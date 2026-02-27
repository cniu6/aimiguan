from datetime import datetime, timezone
import asyncio
import hashlib
import json
import uuid
from typing import Any, Callable, Dict, List, Optional, cast

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from core.database import ExecutionTask, SessionLocal, ThreatEvent, User, get_db
from api.auth import require_permissions
from services.ai_engine import ai_engine
from services.audit_service import AuditService
from services.mcp_client import mcp_client

router = APIRouter(prefix="/api/v1/defense", tags=["defense"])
compat_router = APIRouter(tags=["defense"])

MAX_BLOCK_RETRIES = 3
BASE_RETRY_DELAY_SECONDS = 1.0


class HFishHTTPInfo(BaseModel):
    url: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    user_agent: Optional[str] = None


class HFishListInfo(BaseModel):
    client_id: Optional[str] = None
    client_ip: Optional[str] = None
    service_name: Optional[str] = None
    service_type: Optional[str] = None
    attack_ip: Optional[str] = None
    attack_count: Optional[int] = 1
    last_attack_time: Optional[str] = None
    labels: Optional[Any] = None
    labels_cn: Optional[Any] = None
    is_white: Optional[Any] = 0
    intranet: Optional[Any] = 0


class HFishAttackInfo(BaseModel):
    info_id: Optional[str] = None
    attack_ip: Optional[str] = None
    attack_port: Optional[int] = None
    attack_time: Optional[str] = None
    victim_ip: Optional[str] = None
    attack_rule: Optional[Any] = None
    info: Optional[HFishHTTPInfo] = None
    session: Optional[str] = None
    client_id: Optional[str] = None


class HFishAttackTrend(BaseModel):
    attack_time: Optional[str] = None
    attack_count: Optional[int] = 0


class HFishAlert(BaseModel):
    response_code: int = 0
    response_message: Optional[str] = None
    list_infos: List[HFishListInfo] = Field(default_factory=list)
    attack_infos: List[HFishAttackInfo] = Field(default_factory=list)
    attack_trend: List[HFishAttackTrend] = Field(default_factory=list)

    # legacy compatible payload
    ip: Optional[str] = None
    source: Optional[str] = None
    attack_type: Optional[str] = None
    attack_count: Optional[int] = 1


class EventResponse(BaseModel):
    id: int
    ip: str
    source: str
    ai_score: Optional[int]
    ai_reason: Optional[str]
    status: str
    created_at: datetime


class ApproveRequest(BaseModel):
    reason: Optional[str] = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_flag(value: Any) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return 1 if int(value) != 0 else 0
    if isinstance(value, str):
        return 1 if value.strip().lower() in {"1", "true", "yes", "y", "on"} else 0
    return 0


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _normalize_label(labels: Any, labels_cn: Any) -> str:
    for candidate in (labels, labels_cn):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
        if isinstance(candidate, list):
            parts = [str(item).strip() for item in candidate if str(item).strip()]
            if parts:
                return ",".join(parts)
    return "unknown"


def _parse_hfish_time(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        try:
            dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OSError, ValueError):
            return None
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            dt = None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    dt = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
            if dt is None:
                return None
    else:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def _iso_z(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_fallback_event_id(
    source_type: str,
    attack_ip: str,
    attack_time: Optional[datetime],
    raw: Dict[str, Any],
) -> str:
    seed = (
        f"{source_type}|{attack_ip}|{_iso_z(attack_time) or 'none'}|{_json_dumps(raw)}"
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"fallback-{source_type}-{digest}"


def _rule_assess(attack_count: int, attack_ip: str) -> Dict[str, Any]:
    score = max(0, min(100, 50 + attack_count * 10))
    action = "BLOCK" if score >= 80 else "MONITOR"
    return {
        "score": score,
        "reason": f"规则评估：检测到 {attack_count} 次攻击，来源 {attack_ip}",
        "action_suggest": action,
    }


def _safe_json_loads(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    except (TypeError, ValueError):
        pass
    return {}


def _normalize_action(value: Any) -> str:
    action = str(value or "").strip().upper()
    return action if action in {"BLOCK", "MONITOR"} else "MONITOR"


def _clamp_score(value: Any, default: int) -> int:
    score = _safe_int(value, default)
    return max(0, min(100, score))


async def _enrich_with_ai_assessment(event_payload: Dict[str, Any]) -> Dict[str, Any]:
    attack_ip = event_payload.get("ip") or "unknown"
    attack_count = max(1, _safe_int(event_payload.get("attack_count"), 1))
    threat_label = event_payload.get("threat_label") or "unknown"

    fallback = _rule_assess(attack_count, attack_ip)
    degraded = False
    ai_model = "llm"
    reason_detail = ""

    try:
        ai_result = await ai_engine.assess_threat(
            ip=attack_ip,
            attack_type=threat_label,
            attack_count=attack_count,
            history=None,
        )
    except Exception as exc:
        ai_result = fallback
        degraded = True
        ai_model = "rule_fallback"
        reason_detail = str(exc)

    if not isinstance(ai_result, dict):
        ai_result = fallback
        degraded = True
        ai_model = "rule_fallback"
        if not reason_detail:
            reason_detail = "ai_result_not_dict"

    if ai_result.get("degraded") is True:
        degraded = True
    if ai_result.get("model"):
        ai_model = str(ai_result["model"])

    ai_reason = str(ai_result.get("reason") or "").strip()
    if "规则降级" in ai_reason or "AI服务" in ai_reason:
        degraded = True
    if degraded and ai_model == "llm":
        ai_model = "rule_fallback"

    event_payload["ai_score"] = _clamp_score(ai_result.get("score"), fallback["score"])
    event_payload["ai_reason"] = ai_reason or fallback["reason"]
    event_payload["action_suggest"] = _normalize_action(
        ai_result.get("action_suggest") or fallback["action_suggest"]
    )

    extra_json = _safe_json_loads(event_payload.get("extra_json"))
    extra_json["ai_assessment"] = {
        "provider": "ai_engine",
        "model": ai_model,
        "degraded": degraded,
        "assessed_at": _iso_z(_utc_now()),
    }
    if degraded:
        extra_json["ai_assessment"]["fallback"] = "rule_engine"
        if reason_detail:
            extra_json["ai_assessment"]["degrade_reason"] = reason_detail

    event_payload["extra_json"] = _json_dumps(extra_json)
    return event_payload


async def _sleep_for_retry(seconds: float) -> None:
    await asyncio.sleep(seconds)


def _extract_mcp_error(result: Dict[str, Any]) -> str:
    for key in ("error", "message", "result"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "mcp_call_failed"


async def _execute_block_task(
    db: Session,
    event: ThreatEvent,
    task: ExecutionTask,
    trace_id: str,
) -> None:
    task_id = _safe_int(getattr(task, "id", 0), 0)
    event_id = _safe_int(getattr(event, "id", 0), 0)
    event_ip = str(getattr(event, "ip", "") or "")
    device_id_raw = getattr(task, "device_id", None)
    device_id: Optional[int]
    if isinstance(device_id_raw, int):
        device_id = device_id_raw
    elif isinstance(device_id_raw, str) and device_id_raw.strip().isdigit():
        device_id = int(device_id_raw)
    else:
        device_id = None

    if task_id <= 0 or event_id <= 0 or not event_ip:
        return

    now = _utc_now()
    db.query(ExecutionTask).filter(ExecutionTask.id == task_id).update(
        {"state": "RUNNING", "started_at": now, "updated_at": now}
    )
    db.query(ThreatEvent).filter(ThreatEvent.id == event_id).update(
        {"status": "EXECUTING", "updated_at": now}
    )
    db.commit()

    attempt = 0
    while True:
        result = await mcp_client.block_ip(event_ip, device_id)
        if result.get("success") is True:
            done_time = _utc_now()
            db.query(ExecutionTask).filter(ExecutionTask.id == task_id).update(
                {
                    "state": "SUCCESS",
                    "error_message": None,
                    "ended_at": done_time,
                    "updated_at": done_time,
                }
            )
            db.query(ThreatEvent).filter(ThreatEvent.id == event_id).update(
                {"status": "DONE", "updated_at": done_time}
            )
            db.commit()
            AuditService.log(
                db=db,
                actor="defense_executor",
                action="block_ip_execute",
                target=f"execution_task:{task_id}",
                target_type="execution_task",
                target_ip=event_ip,
                reason=_json_dumps({"attempt": attempt + 1, "result": result}),
                result="success",
                trace_id=trace_id,
            )
            return

        attempt += 1
        error_message = _extract_mcp_error(result)
        db.query(ExecutionTask).filter(ExecutionTask.id == task_id).update(
            {
                "retry_count": attempt,
                "error_message": error_message,
                "updated_at": _utc_now(),
            }
        )

        if attempt >= MAX_BLOCK_RETRIES:
            end_time = _utc_now()
            db.query(ExecutionTask).filter(ExecutionTask.id == task_id).update(
                {
                    "state": "MANUAL_REQUIRED",
                    "ended_at": end_time,
                    "updated_at": end_time,
                }
            )
            db.query(ThreatEvent).filter(ThreatEvent.id == event_id).update(
                {"status": "FAILED", "updated_at": end_time}
            )
            db.commit()
            AuditService.log(
                db=db,
                actor="defense_executor",
                action="block_ip_execute",
                target=f"execution_task:{task_id}",
                target_type="execution_task",
                target_ip=event_ip,
                reason=_json_dumps(
                    {
                        "attempt": attempt,
                        "state": "MANUAL_REQUIRED",
                        "error": error_message,
                    }
                ),
                result="failed",
                trace_id=trace_id,
            )
            return

        db.query(ExecutionTask).filter(ExecutionTask.id == task_id).update(
            {"state": "FAILED"}
        )
        db.commit()

        db.query(ExecutionTask).filter(ExecutionTask.id == task_id).update(
            {"state": "RETRYING", "updated_at": _utc_now()}
        )
        db.commit()

        delay_seconds = BASE_RETRY_DELAY_SECONDS * (2 ** (attempt - 1))
        await _sleep_for_retry(delay_seconds)

        db.query(ExecutionTask).filter(ExecutionTask.id == task_id).update(
            {"state": "RUNNING", "updated_at": _utc_now()}
        )
        db.commit()


async def _run_execution_task_background(
    task_id: int,
    trace_id: str,
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:
    db = session_factory()
    try:
        task = db.query(ExecutionTask).filter(ExecutionTask.id == task_id).first()
        if task is None:
            return

        event = db.query(ThreatEvent).filter(ThreatEvent.id == task.event_id).first()
        if event is None:
            now = _utc_now()
            db.query(ExecutionTask).filter(ExecutionTask.id == task_id).update(
                {
                    "state": "MANUAL_REQUIRED",
                    "error_message": "threat_event_not_found",
                    "ended_at": now,
                    "updated_at": now,
                }
            )
            db.commit()
            return

        await _execute_block_task(db=db, event=event, task=task, trace_id=trace_id)
    except Exception as exc:
        db.rollback()
        now = _utc_now()
        db.query(ExecutionTask).filter(ExecutionTask.id == task_id).update(
            {
                "state": "MANUAL_REQUIRED",
                "error_message": str(exc),
                "ended_at": now,
                "updated_at": now,
            }
        )
        db.commit()
    finally:
        db.close()


def _normalize_list_info(item: HFishListInfo, trace_id: str) -> Dict[str, Any]:
    raw = item.model_dump()
    attack_ip = (item.attack_ip or "").strip()
    if not attack_ip:
        raise ValueError("list_infos item missing attack_ip")

    attack_dt = _parse_hfish_time(item.last_attack_time)
    source_event_id = (item.client_id or "").strip()
    if not source_event_id:
        source_event_id = _build_fallback_event_id(
            "attack_source", attack_ip, attack_dt, raw
        )

    attack_count = max(1, _safe_int(item.attack_count, 1))
    assessment = _rule_assess(attack_count, attack_ip)

    extra_json = {
        "source_client_id": item.client_id,
        "intranet": _to_flag(item.intranet),
        "last_attack_time_raw": item.last_attack_time,
        "normalized_attack_time": _iso_z(attack_dt),
    }

    event_time = attack_dt or _utc_now()
    return {
        "ip": attack_ip,
        "source": item.service_name or "hfish",
        "source_vendor": "hfish",
        "source_type": "attack_source",
        "source_event_id": source_event_id,
        "attack_count": attack_count,
        "asset_ip": item.client_ip,
        "service_name": item.service_name,
        "service_type": item.service_type,
        "threat_label": _normalize_label(item.labels, item.labels_cn),
        "is_white": _to_flag(item.is_white),
        "ai_score": assessment["score"],
        "ai_reason": assessment["reason"],
        "action_suggest": assessment["action_suggest"],
        "status": "PENDING",
        "trace_id": trace_id,
        "raw_payload": _json_dumps(raw),
        "extra_json": _json_dumps(extra_json),
        "created_at": event_time,
        "updated_at": event_time,
    }


def _normalize_attack_info(item: HFishAttackInfo, trace_id: str) -> Dict[str, Any]:
    raw = item.model_dump()
    attack_ip = (item.attack_ip or "").strip()
    if not attack_ip:
        raise ValueError("attack_infos item missing attack_ip")

    attack_dt = _parse_hfish_time(item.attack_time)
    source_event_id = (item.info_id or "").strip()
    if not source_event_id:
        source_event_id = _build_fallback_event_id(
            "attack_detail", attack_ip, attack_dt, raw
        )

    assessment = _rule_assess(1, attack_ip)
    http_meta = item.info.model_dump() if item.info else {}

    extra_json = {
        "attack_port": item.attack_port,
        "session": item.session,
        "http_meta": http_meta,
        "rule_hits": item.attack_rule,
        "normalized_attack_time": _iso_z(attack_dt),
    }

    event_time = attack_dt or _utc_now()
    return {
        "ip": attack_ip,
        "source": "hfish_attack_detail",
        "source_vendor": "hfish",
        "source_type": "attack_detail",
        "source_event_id": source_event_id,
        "attack_count": 1,
        "asset_ip": item.victim_ip,
        "service_name": "attack_detail",
        "service_type": "hfish",
        "threat_label": _normalize_label(item.attack_rule, None),
        "is_white": 0,
        "ai_score": assessment["score"],
        "ai_reason": assessment["reason"],
        "action_suggest": assessment["action_suggest"],
        "status": "PENDING",
        "trace_id": trace_id,
        "raw_payload": _json_dumps(raw),
        "extra_json": _json_dumps(extra_json),
        "created_at": event_time,
        "updated_at": event_time,
    }


def _normalize_legacy_alert(
    alert: HFishAlert, trace_id: str
) -> Optional[Dict[str, Any]]:
    ip = (alert.ip or "").strip()
    if not ip:
        return None

    attack_count = max(1, _safe_int(alert.attack_count, 1))
    assessment = _rule_assess(attack_count, ip)
    raw = alert.model_dump()
    source_event_id = _build_fallback_event_id("legacy_alert", ip, None, raw)
    now = _utc_now()

    return {
        "ip": ip,
        "source": alert.source or "legacy_hfish",
        "source_vendor": "hfish",
        "source_type": "legacy_alert",
        "source_event_id": source_event_id,
        "attack_count": attack_count,
        "asset_ip": None,
        "service_name": alert.source,
        "service_type": "legacy",
        "threat_label": _normalize_label(alert.attack_type, None),
        "is_white": 0,
        "ai_score": assessment["score"],
        "ai_reason": assessment["reason"],
        "action_suggest": assessment["action_suggest"],
        "status": "PENDING",
        "trace_id": trace_id,
        "raw_payload": _json_dumps(raw),
        "extra_json": _json_dumps({"legacy_payload": True}),
        "created_at": now,
        "updated_at": now,
    }


def _normalize_trend_points(points: List[HFishAttackTrend]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in points:
        dt = _parse_hfish_time(item.attack_time)
        if dt is None:
            continue
        normalized.append(
            {
                "trend_time_utc": _iso_z(dt),
                "trend_count": max(0, _safe_int(item.attack_count, 0)),
            }
        )
    return normalized


@router.post("/alerts")
@compat_router.post("/alerts", include_in_schema=False)
async def receive_alert(
    alert: HFishAlert,
    request: Request,
    db: Session = Depends(get_db),
):
    """接收 HFish 告警"""
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))

    if alert.response_code != 0:
        AuditService.log(
            db=db,
            actor="hfish_ingestor",
            action="hfish_ingest",
            target="threat_event",
            target_type="ingest",
            reason=_json_dumps(
                {
                    "error": "upstream_response_invalid",
                    "response_code": alert.response_code,
                    "response_message": alert.response_message,
                }
            ),
            result="failed",
            trace_id=trace_id,
        )
        raise HTTPException(status_code=502, detail={
            "error": "upstream_response_invalid",
            "message": "HFish 源端响应失败，未进入解析流程",
            "response_code": alert.response_code,
            "trace_id": trace_id,
        })

    normalized_events: List[Dict[str, Any]] = []
    invalid_reasons: List[str] = []

    for item in alert.list_infos:
        try:
            normalized_events.append(_normalize_list_info(item, trace_id))
        except ValueError as exc:
            invalid_reasons.append(str(exc))

    for item in alert.attack_infos:
        try:
            normalized_events.append(_normalize_attack_info(item, trace_id))
        except ValueError as exc:
            invalid_reasons.append(str(exc))

    if not normalized_events:
        legacy = _normalize_legacy_alert(alert, trace_id)
        if legacy:
            normalized_events.append(legacy)

    trend_points = _normalize_trend_points(alert.attack_trend)
    ingested_event_ids: List[int] = []
    deduped_event_ids: List[int] = []

    try:
        for event_payload in normalized_events:
            existing = (
                db.query(ThreatEvent)
                .filter(
                    ThreatEvent.source_vendor == event_payload["source_vendor"],
                    ThreatEvent.source_event_id == event_payload["source_event_id"],
                )
                .first()
            )
            if existing:
                if existing.id is not None:
                    existing_id = _safe_int(getattr(existing, "id", None), 0)
                    if existing_id > 0:
                        deduped_event_ids.append(existing_id)
                continue

            event_payload = await _enrich_with_ai_assessment(event_payload)
            event = ThreatEvent(**event_payload)
            db.add(event)
            db.flush()
            if event.id is not None:
                event_id = _safe_int(getattr(event, "id", None), 0)
                if event_id > 0:
                    ingested_event_ids.append(event_id)

        db.commit()
    except Exception as exc:
        db.rollback()
        AuditService.log(
            db=db,
            actor="hfish_ingestor",
            action="hfish_ingest",
            target="threat_event",
            target_type="ingest",
            reason=_json_dumps({"error": "db_persist_failed", "detail": str(exc)}),
            result="failed",
            trace_id=trace_id,
        )
        raise HTTPException(status_code=500, detail={
            "error": "alert_operation_failed",
            "message": "威胁事件写入失败",
            "detail": str(exc),
            "trace_id": trace_id,
        })

    ingest_summary = {
        "source": "hfish",
        "ingested": len(ingested_event_ids),
        "deduped": len(deduped_event_ids),
        "invalid": len(invalid_reasons),
    }
    AuditService.log(
        db=db,
        actor="hfish_ingestor",
        action="hfish_ingest",
        target="threat_event",
        target_type="ingest",
        reason=_json_dumps(ingest_summary),
        result="success",
        trace_id=trace_id,
    )

    if invalid_reasons:
        AuditService.log(
            db=db,
            actor="hfish_ingestor",
            action="hfish_ingest_invalid",
            target="threat_event",
            target_type="ingest",
            reason=_json_dumps({"invalid_reasons": invalid_reasons}),
            result="failed",
            trace_id=trace_id,
        )

    first_id: Optional[int] = None
    if ingested_event_ids:
        first_id = ingested_event_ids[0]
    elif deduped_event_ids:
        first_id = deduped_event_ids[0]

    return {
        "code": 0,
        "message": "Alert received",
        "data": {
            "event_id": first_id,
            "event_ids": ingested_event_ids,
            "deduped_event_ids": deduped_event_ids,
            "invalid_reasons": invalid_reasons,
            "trend_points": trend_points,
            "trace_id": trace_id,
        },
    }


@router.get("/events", response_model=List[EventResponse])
@compat_router.get(
    "/events", response_model=List[EventResponse], include_in_schema=False
)
async def get_events(status: Optional[str] = None, db: Session = Depends(get_db)):
    """获取威胁事件列表"""
    query = db.query(ThreatEvent)
    if status:
        query = query.filter(ThreatEvent.status == status)
    events = query.order_by(ThreatEvent.created_at.desc()).limit(100).all()
    return events


def _parse_filter_time(value: Optional[str], field_name: str) -> Optional[datetime]:
    if value is None:
        return None
    parsed = _parse_hfish_time(value)
    if parsed is None:
        raise HTTPException(status_code=400, detail=f"invalid {field_name}, expected ISO8601 or '%Y-%m-%d %H:%M:%S'")
    return parsed


def _serialize_threat_event(event: ThreatEvent) -> Dict[str, Any]:
    created_at = getattr(event, "created_at", None)
    updated_at = getattr(event, "updated_at", None)
    return {
        "id": _safe_int(getattr(event, "id", 0), 0),
        "ip": str(getattr(event, "ip", "") or ""),
        "source": str(getattr(event, "source", "") or ""),
        "source_vendor": getattr(event, "source_vendor", None),
        "source_type": getattr(event, "source_type", None),
        "ai_score": getattr(event, "ai_score", None),
        "ai_reason": getattr(event, "ai_reason", None),
        "action_suggest": getattr(event, "action_suggest", None),
        "status": str(getattr(event, "status", "") or ""),
        "trace_id": str(getattr(event, "trace_id", "") or ""),
        "created_at": _iso_z(created_at) if isinstance(created_at, datetime) else None,
        "updated_at": _iso_z(updated_at) if isinstance(updated_at, datetime) else None,
    }


@router.get("/pending")
@compat_router.get("/pending", include_in_schema=False)
async def get_pending_events(
    request: Request,
    status: str = "PENDING",
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    risk_level: Optional[str] = None,
    source: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    current_user: User = Depends(require_permissions("view_events")),
    db: Session = Depends(get_db),
):
    """获取待审批事件列表（支持状态、时间、风险筛选与分页排序）"""
    if page < 1:
        raise HTTPException(status_code=400, detail="page must be >= 1")
    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=400, detail="page_size must be between 1 and 100")

    parsed_start_time = _parse_filter_time(start_time, "start_time")
    parsed_end_time = _parse_filter_time(end_time, "end_time")
    if parsed_start_time and parsed_end_time and parsed_start_time > parsed_end_time:
        raise HTTPException(status_code=400, detail="start_time must be <= end_time")

    if min_score is not None and (min_score < 0 or min_score > 100):
        raise HTTPException(status_code=400, detail="min_score must be between 0 and 100")
    if max_score is not None and (max_score < 0 or max_score > 100):
        raise HTTPException(status_code=400, detail="max_score must be between 0 and 100")
    if min_score is not None and max_score is not None and min_score > max_score:
        raise HTTPException(status_code=400, detail="min_score must be <= max_score")

    normalized_risk_level: Optional[str] = None
    if risk_level is not None:
        normalized_risk_level = str(risk_level).strip().upper()
        if normalized_risk_level not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            raise HTTPException(status_code=400, detail="risk_level must be one of LOW, MEDIUM, HIGH, CRITICAL")

    normalized_sort_by = str(sort_by).strip()
    sort_field_map = {
        "created_at": ThreatEvent.created_at,
        "updated_at": ThreatEvent.updated_at,
        "ai_score": ThreatEvent.ai_score,
        "ip": ThreatEvent.ip,
        "status": ThreatEvent.status,
    }
    if normalized_sort_by not in sort_field_map:
        raise HTTPException(status_code=400, detail="sort_by must be one of created_at, updated_at, ai_score, ip, status")

    normalized_sort_order = str(sort_order).strip().lower()
    if normalized_sort_order not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="sort_order must be asc or desc")

    query = db.query(ThreatEvent)
    normalized_status = str(status or "").strip().upper()
    if normalized_status:
        query = query.filter(ThreatEvent.status == normalized_status)

    if parsed_start_time is not None:
        query = query.filter(ThreatEvent.created_at >= parsed_start_time)
    if parsed_end_time is not None:
        query = query.filter(ThreatEvent.created_at <= parsed_end_time)

    if source is not None and str(source).strip():
        query = query.filter(ThreatEvent.source == str(source).strip())

    if normalized_risk_level is not None:
        risk_ranges = {
            "LOW": (0, 39),
            "MEDIUM": (40, 69),
            "HIGH": (70, 89),
            "CRITICAL": (90, 100),
        }
        level_min, level_max = risk_ranges[normalized_risk_level]
        query = query.filter(
            ThreatEvent.ai_score >= level_min, ThreatEvent.ai_score <= level_max
        )

    if min_score is not None:
        query = query.filter(ThreatEvent.ai_score >= min_score)
    if max_score is not None:
        query = query.filter(ThreatEvent.ai_score <= max_score)

    total = query.count()
    sort_column = sort_field_map[normalized_sort_by]
    if normalized_sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    offset = (page - 1) * page_size
    records = query.offset(offset).limit(page_size).all()
    items = [_serialize_threat_event(record) for record in records]
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return {
        "code": 0,
        "message": "Pending events fetched",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
        "trace_id": getattr(request.state, "trace_id", None),
    }


@router.post("/events/{event_id}/approve")
@compat_router.post("/events/{event_id}/approve", include_in_schema=False)
async def approve_event(
    background_tasks: BackgroundTasks,
    event_id: int,
    req: ApproveRequest,
    request: Request,
    current_user: User = Depends(require_permissions("approve_event")),
    db: Session = Depends(get_db),
):
    """批准处置事件"""
    event = db.query(ThreatEvent).filter(ThreatEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    db.query(ThreatEvent).filter(ThreatEvent.id == event_id).update(
        {"status": "APPROVED", "updated_at": _utc_now()}
    )

    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
    task = ExecutionTask(
        event_id=event_id,
        action="BLOCK",
        state="QUEUED",
        trace_id=trace_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    event = db.query(ThreatEvent).filter(ThreatEvent.id == event_id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    task_id = _safe_int(cast(Optional[int], getattr(task, "id", None)), 0)
    if task_id <= 0:
        raise HTTPException(status_code=500, detail="execution_task_create_failed")
    request_session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db.get_bind(),
    )
    background_tasks.add_task(
        _run_execution_task_background,
        task_id,
        trace_id,
        request_session_factory,
    )

    task_row = (
        db.query(ExecutionTask.state, ExecutionTask.retry_count)
        .filter(ExecutionTask.id == task.id)
        .first()
    )
    task_state = "QUEUED"
    retry_count = 0
    if task_row:
        task_state = str(task_row[0] or "QUEUED")
        retry_count = _safe_int(task_row[1], 0)

    return {
        "code": 0,
        "message": "Event approved",
        "data": {
            "task_id": task.id,
            "task_state": task_state,
            "retry_count": retry_count,
        },
    }


@router.post("/events/{event_id}/reject")
@compat_router.post("/events/{event_id}/reject", include_in_schema=False)
async def reject_event(
    event_id: int,
    req: ApproveRequest,
    current_user: User = Depends(require_permissions("reject_event")),
    db: Session = Depends(get_db),
):
    """驳回处置事件"""
    event = db.query(ThreatEvent).filter(ThreatEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    db.query(ThreatEvent).filter(ThreatEvent.id == event_id).update(
        {"status": "REJECTED", "updated_at": _utc_now()}
    )
    db.commit()

    return {"code": 0, "message": "Event rejected"}
