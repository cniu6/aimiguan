from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.database import SystemConfigSnapshot
from services.audit_service import AuditService

DEFENSE_WORKFLOW_ROLLOUT_KEY = "defense_workflow_rollout"
VALID_DEFENSE_WORKFLOW_ROLLOUT_MODES = {"legacy_only", "workflow_gray", "workflow_full"}
DEFAULT_DEFENSE_WORKFLOW_ROLLOUT = {
    "mode": "legacy_only",
    "gray_percent": 0,
    "double_write_metrics": False,
    "reason": "系统初始化",
    "operator": "system",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso(value: Optional[datetime] = None) -> str:
    current = value or _utc_now()
    return current.isoformat().replace("+00:00", "Z")


def _normalize_mode(value: Any) -> str:
    mode = str(value or "").strip().lower()
    return mode if mode in VALID_DEFENSE_WORKFLOW_ROLLOUT_MODES else "legacy_only"


def _normalize_gray_percent(value: Any) -> int:
    try:
        percent = int(value)
    except (TypeError, ValueError):
        percent = 0
    return max(0, min(100, percent))


def _snapshot_payload(row: Any) -> dict[str, Any]:
    if not row:
        return {**DEFAULT_DEFENSE_WORKFLOW_ROLLOUT, "updated_at": _utc_iso()}
    try:
        payload = json.loads(row[0]) if row[0] else {}
    except (TypeError, json.JSONDecodeError):
        payload = {}
    data = payload if isinstance(payload, dict) else {}
    return {
        "mode": _normalize_mode(data.get("mode")),
        "gray_percent": _normalize_gray_percent(data.get("gray_percent")),
        "double_write_metrics": bool(data.get("double_write_metrics", False)),
        "reason": data.get("reason") or DEFAULT_DEFENSE_WORKFLOW_ROLLOUT["reason"],
        "operator": data.get("operator") or DEFAULT_DEFENSE_WORKFLOW_ROLLOUT["operator"],
        "updated_at": data.get("updated_at") or _utc_iso(getattr(row, "loaded_at", None) if hasattr(row, "loaded_at") else None),
    }


def get_defense_workflow_rollout(db: Session, env: str) -> dict[str, Any]:
    row = db.execute(
        text(
            """
            SELECT config_value, loaded_at
            FROM system_config_snapshot
            WHERE config_key = :config_key AND env = :env
            ORDER BY loaded_at DESC, id DESC
            LIMIT 1
            """
        ),
        {"config_key": DEFENSE_WORKFLOW_ROLLOUT_KEY, "env": env},
    ).fetchone()
    return _snapshot_payload(row)


def set_defense_workflow_rollout(
    db: Session,
    *,
    mode: str,
    gray_percent: int,
    double_write_metrics: bool,
    reason: Optional[str],
    operator: str,
    env: str,
    trace_id: Optional[str],
) -> dict[str, Any]:
    normalized_mode = _normalize_mode(mode)
    normalized_gray_percent = _normalize_gray_percent(gray_percent)
    now = _utc_now()
    payload = {
        "mode": normalized_mode,
        "gray_percent": normalized_gray_percent,
        "double_write_metrics": bool(double_write_metrics),
        "reason": reason,
        "operator": operator,
        "updated_at": _utc_iso(now),
    }
    snapshot = SystemConfigSnapshot(
        config_key=DEFENSE_WORKFLOW_ROLLOUT_KEY,
        config_value=json.dumps(payload, ensure_ascii=False),
        source="api",
        is_sensitive=0,
        env=env,
        loaded_at=now,
        created_at=now,
    )
    db.add(snapshot)
    AuditService.log(
        db=db,
        actor=operator,
        action=f"set_defense_workflow_rollout:{normalized_mode}",
        target=DEFENSE_WORKFLOW_ROLLOUT_KEY,
        target_type="system",
        reason=reason,
        result="success",
        trace_id=trace_id,
        auto_commit=False,
    )
    db.commit()
    return payload


def should_route_to_workflow_runtime(
    *,
    rollout: Mapping[str, Any],
    routing_key: str,
    trace_id: Optional[str] = None,
) -> bool:
    mode = _normalize_mode(rollout.get("mode"))
    if mode == "legacy_only":
        return False
    if mode == "workflow_full":
        return True
    gray_percent = _normalize_gray_percent(rollout.get("gray_percent"))
    if gray_percent <= 0:
        return False
    if gray_percent >= 100:
        return True
    basis = routing_key or trace_id or "workflow_gray"
    slot = int(hashlib.sha256(basis.encode("utf-8")).hexdigest()[:8], 16) % 100
    return slot < gray_percent
