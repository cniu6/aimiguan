"""Workflow management APIs (M1-03)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from api.auth import require_permissions
from core.database import (
    User,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowStepRun,
    WorkflowVersion,
    get_db,
)
from services.audit_service import AuditService
from services.workflow_release import apply_release_metadata, get_publish_lock
from services.workflow_dsl import validate_workflow_dsl
from services.workflow_runtime import WorkflowRuntimeError, build_workflow_debug_report, replay_workflow_run
from services.workflow_validator import validate_workflow_publish

router = APIRouter(prefix="/api/v1/workflows", tags=["workflow"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _state_value(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw)


def _duration_ms(started_at: Optional[datetime], ended_at: Optional[datetime]) -> Optional[int]:
    if started_at is None:
        return None
    start = started_at if started_at.tzinfo else started_at.replace(tzinfo=timezone.utc)
    end_value = ended_at or _utc_now()
    end = end_value if end_value.tzinfo else end_value.replace(tzinfo=timezone.utc)
    return max(0, int((end - start).total_seconds() * 1000))


def _safe_json_value(raw: Optional[str]) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return raw


def _payload_summary(raw: Optional[str], limit: int = 180) -> Optional[str]:
    value = _safe_json_value(raw)
    if value is None:
        return None
    text = json.dumps(value, ensure_ascii=False, default=str) if isinstance(value, (dict, list)) else str(value)
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


def _audit_trace_path(trace_id: Optional[str]) -> Optional[str]:
    trace = str(trace_id or "").strip()
    if not trace:
        return None
    return f"/audit?trace_id={trace}"


def _runtime_error_to_http(exc: WorkflowRuntimeError) -> HTTPException:
    message = str(exc)
    status_code = 404 if "not found" in message.lower() else 400
    return HTTPException(status_code=status_code, detail=message)


def _apply_run_filters(
    query,
    *,
    workflow_id: Optional[int] = None,
    workflow_key: Optional[str] = None,
    run_state: Optional[str] = None,
    trace_id: Optional[str] = None,
    trigger_source: Optional[str] = None,
    keyword: Optional[str] = None,
):
    if workflow_id is not None:
        query = query.filter(WorkflowRun.workflow_id == workflow_id)
    if workflow_key:
        query = query.filter(WorkflowDefinition.workflow_key == workflow_key.strip())
    if run_state:
        query = query.filter(WorkflowRun.run_state == run_state.strip().upper())
    if trace_id:
        query = query.filter(WorkflowRun.trace_id == trace_id.strip())
    if trigger_source:
        query = query.filter(WorkflowRun.trigger_source == trigger_source.strip())
    if keyword:
        term = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                WorkflowDefinition.workflow_key.like(term),
                WorkflowDefinition.name.like(term),
                WorkflowRun.trigger_ref.like(term),
                WorkflowRun.trace_id.like(term),
            )
        )
    return query


def _run_state_summary(counts: Dict[str, int]) -> Dict[str, Any]:
    total_runs = sum(counts.values())
    failed_total = counts.get("FAILED", 0) + counts.get("MANUAL_REQUIRED", 0) + counts.get("CANCELLED", 0)
    return {
        "total_runs": total_runs,
        "queued_runs": counts.get("QUEUED", 0),
        "running_runs": counts.get("RUNNING", 0) + counts.get("RETRYING", 0),
        "success_runs": counts.get("SUCCESS", 0),
        "failed_runs": counts.get("FAILED", 0),
        "manual_required_runs": counts.get("MANUAL_REQUIRED", 0),
        "cancelled_runs": counts.get("CANCELLED", 0),
        "failure_rate": round((failed_total / total_runs) * 100, 2) if total_runs > 0 else 0.0,
    }


def _to_run_item(
    run: WorkflowRun,
    definition: WorkflowDefinition,
    version: WorkflowVersion,
    *,
    step_count: int,
    failed_step_count: int,
    latest_error_message: Optional[str],
) -> Dict[str, Any]:
    duration_ms = _duration_ms(run.started_at, run.ended_at)
    return {
        "run_id": run.id,
        "workflow_id": definition.id,
        "workflow_key": definition.workflow_key,
        "workflow_name": definition.name,
        "workflow_version": version.version,
        "run_state": run.run_state,
        "trigger_source": run.trigger_source,
        "trigger_ref": run.trigger_ref,
        "trace_id": run.trace_id,
        "audit_path": _audit_trace_path(run.trace_id),
        "started_at": _iso(run.started_at),
        "ended_at": _iso(run.ended_at),
        "created_at": _iso(run.created_at),
        "updated_at": _iso(run.updated_at),
        "duration_ms": duration_ms,
        "step_count": step_count,
        "failed_step_count": failed_step_count,
        "latest_error_message": latest_error_message,
    }


def _to_step_item(step: WorkflowStepRun) -> Dict[str, Any]:
    return {
        "id": step.id,
        "node_id": step.node_id,
        "node_type": step.node_type,
        "step_state": step.step_state,
        "attempt": step.attempt,
        "trace_id": step.trace_id,
        "audit_path": _audit_trace_path(step.trace_id),
        "started_at": _iso(step.started_at),
        "ended_at": _iso(step.ended_at),
        "created_at": _iso(step.created_at),
        "updated_at": _iso(step.updated_at),
        "duration_ms": _duration_ms(step.started_at, step.ended_at),
        "error_message": step.error_message,
        "input_summary": _payload_summary(step.input_payload),
        "output_summary": _payload_summary(step.output_payload),
        "input_payload": _safe_json_value(step.input_payload),
        "output_payload": _safe_json_value(step.output_payload),
    }


def _to_definition_item(model: WorkflowDefinition) -> Dict[str, Any]:
    return {
        "id": model.id,
        "workflow_key": model.workflow_key,
        "name": model.name,
        "description": model.description,
        "definition_state": _state_value(model.definition_state),
        "latest_version": model.latest_version,
        "published_version": model.published_version,
        "version_tag": model.latest_version,
        "created_by": model.created_by,
        "updated_by": model.updated_by,
        "created_at": _iso(model.created_at),
        "updated_at": _iso(model.updated_at),
    }


def _load_latest_version(db: Session, workflow_id: int, latest_version: int) -> WorkflowVersion:
    row = (
        db.query(WorkflowVersion)
        .filter(
            WorkflowVersion.workflow_id == workflow_id,
            WorkflowVersion.version == latest_version,
        )
        .first()
    )
    if row:
        return row
    fallback = (
        db.query(WorkflowVersion)
        .filter(WorkflowVersion.workflow_id == workflow_id)
        .order_by(WorkflowVersion.version.desc())
        .first()
    )
    if fallback is None:
        raise HTTPException(status_code=404, detail="workflow version not found")
    return fallback


def _load_target_version(db: Session, workflow_id: int, version: int) -> WorkflowVersion:
    row = (
        db.query(WorkflowVersion)
        .filter(
            WorkflowVersion.workflow_id == workflow_id,
            WorkflowVersion.version == version,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail={
            "code": 40441,
            "message": f"workflow version {version} not found",
            "data": {"workflow_id": workflow_id, "version": version},
        })
    return row


def _load_version_dsl(version: WorkflowVersion) -> Dict[str, Any]:
    try:
        payload = json.loads(version.dsl_json or "{}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"invalid workflow dsl snapshot: {exc}")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="invalid workflow dsl snapshot: payload must be object")
    return payload


def _set_published_version(
    db: Session,
    definition: WorkflowDefinition,
    target_version: WorkflowVersion,
    *,
    actor: str,
    now: datetime,
) -> Optional[int]:
    previous_published_version = definition.published_version
    if previous_published_version is not None and previous_published_version != target_version.version:
        previous_row = _load_target_version(db, definition.id, previous_published_version)
        previous_row.definition_state = "VALIDATED"
        previous_row.updated_at = now
    target_version.definition_state = "PUBLISHED"
    target_version.updated_at = now
    definition.definition_state = "PUBLISHED"
    definition.published_version = target_version.version
    definition.updated_by = actor
    definition.updated_at = now
    return previous_published_version


def _ensure_confirmation(required_text: str, confirmation_text: str, *, error_code: int, action: str) -> None:
    if confirmation_text.strip() == required_text:
        return
    raise HTTPException(status_code=400, detail={
        "code": error_code,
        "message": f"{action} confirmation mismatch",
        "data": {"required_confirmation": required_text},
    })


def _normalize_and_validate_dsl(workflow_key: str, dsl: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(dsl)
    if not payload.get("workflow_id"):
        payload["workflow_id"] = workflow_key
    if str(payload.get("workflow_id")) != workflow_key:
        raise HTTPException(status_code=400, detail="dsl.workflow_id must match workflow_key")
    validated = validate_workflow_dsl(payload)
    return validated.model_dump(by_alias=True, mode="json")


class WorkflowCreateRequest(BaseModel):
    workflow_key: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    dsl: Dict[str, Any]
    change_note: Optional[str] = Field(default=None, max_length=500)


class WorkflowUpdateRequest(BaseModel):
    version_tag: int = Field(ge=1)
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    dsl: Dict[str, Any]
    change_note: Optional[str] = Field(default=None, max_length=500)


class WorkflowPublishRequest(BaseModel):
    version_tag: Optional[int] = Field(default=None, ge=1)
    canary_percent: int = Field(default=100, ge=1, le=100)
    effective_at: Optional[datetime] = None
    approval_reason: str = Field(min_length=1, max_length=500)
    approval_passed: bool = False
    confirmation_text: str = Field(min_length=1, max_length=120)
    trace_id: Optional[str] = Field(default=None, max_length=128)


class WorkflowRollbackRequest(BaseModel):
    target_version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=500)
    confirmation_text: str = Field(min_length=1, max_length=120)
    trace_id: Optional[str] = Field(default=None, max_length=128)


class WorkflowReplayRequest(BaseModel):
    mode: str = Field(default="full", pattern="^(full|resume_from_failure)$")
    overrides: Dict[str, Any] = Field(default_factory=dict)
    trace_id: Optional[str] = Field(default=None, max_length=128)


@router.get("")
async def list_workflows(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    definition_state: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("workflow_view")),
):
    query = db.query(WorkflowDefinition)
    if keyword:
        key = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                WorkflowDefinition.workflow_key.like(key),
                WorkflowDefinition.name.like(key),
                WorkflowDefinition.description.like(key),
            )
        )
    if definition_state:
        query = query.filter(WorkflowDefinition.definition_state == definition_state.strip().upper())

    total = query.count()
    items = (
        query.order_by(WorkflowDefinition.updated_at.desc(), WorkflowDefinition.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "code": 0,
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [_to_definition_item(item) for item in items],
        },
    }


@router.post("")
async def create_workflow(
    payload: WorkflowCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("workflow_edit")),
):
    existing = (
        db.query(WorkflowDefinition)
        .filter(WorkflowDefinition.workflow_key == payload.workflow_key)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="workflow_key already exists")

    dsl_payload = _normalize_and_validate_dsl(payload.workflow_key, payload.dsl)
    now = _utc_now()

    definition = WorkflowDefinition(
        workflow_key=payload.workflow_key,
        name=payload.name,
        description=payload.description,
        definition_state=str(dsl_payload.get("status", "DRAFT")).upper(),
        latest_version=int(dsl_payload.get("version", 1)),
        published_version=None,
        created_by=str(current_user.username),
        updated_by=str(current_user.username),
        created_at=now,
        updated_at=now,
    )
    db.add(definition)
    db.flush()

    version = WorkflowVersion(
        workflow_id=definition.id,
        version=definition.latest_version,
        definition_state=definition.definition_state,
        dsl_json=json.dumps(dsl_payload, ensure_ascii=False),
        change_note=payload.change_note,
        created_by=str(current_user.username),
        created_at=now,
        updated_at=now,
    )
    db.add(version)
    db.commit()
    db.refresh(definition)

    return {
        "code": 0,
        "data": _to_definition_item(definition),
        "message": "workflow created",
    }


@router.get("/runs")
async def list_workflow_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    workflow_id: Optional[int] = Query(default=None),
    workflow_key: Optional[str] = Query(default=None),
    run_state: Optional[str] = Query(default=None),
    trace_id: Optional[str] = Query(default=None),
    trigger_source: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("workflow_view")),
):
    base_query = (
        db.query(WorkflowRun, WorkflowDefinition, WorkflowVersion)
        .join(WorkflowDefinition, WorkflowDefinition.id == WorkflowRun.workflow_id)
        .join(WorkflowVersion, WorkflowVersion.id == WorkflowRun.workflow_version_id)
    )
    base_query = _apply_run_filters(
        base_query,
        workflow_id=workflow_id,
        workflow_key=workflow_key,
        run_state=run_state,
        trace_id=trace_id,
        trigger_source=trigger_source,
        keyword=keyword,
    )

    total = base_query.count()
    rows = (
        base_query.order_by(WorkflowRun.created_at.desc(), WorkflowRun.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    run_ids = [row[0].id for row in rows]
    step_meta: Dict[int, Dict[str, Any]] = {}
    if run_ids:
        step_rows = (
            db.query(WorkflowStepRun)
            .filter(WorkflowStepRun.workflow_run_id.in_(run_ids))
            .order_by(WorkflowStepRun.workflow_run_id.asc(), WorkflowStepRun.id.desc())
            .all()
        )
        for step in step_rows:
            meta = step_meta.setdefault(
                step.workflow_run_id,
                {"step_count": 0, "failed_step_count": 0, "latest_error_message": None},
            )
            meta["step_count"] += 1
            if str(step.step_state or "").upper() in {"FAILED", "MANUAL_REQUIRED"}:
                meta["failed_step_count"] += 1
            if meta["latest_error_message"] is None and step.error_message:
                meta["latest_error_message"] = str(step.error_message)[:500]

    count_query = (
        db.query(WorkflowRun.run_state, func.count(WorkflowRun.id))
        .join(WorkflowDefinition, WorkflowDefinition.id == WorkflowRun.workflow_id)
    )
    count_query = _apply_run_filters(
        count_query,
        workflow_id=workflow_id,
        workflow_key=workflow_key,
        run_state=run_state,
        trace_id=trace_id,
        trigger_source=trigger_source,
        keyword=keyword,
    )
    state_counts = {str(state): int(count) for state, count in count_query.group_by(WorkflowRun.run_state).all()}

    duration_query = (
        db.query(WorkflowRun.started_at, WorkflowRun.ended_at)
        .join(WorkflowDefinition, WorkflowDefinition.id == WorkflowRun.workflow_id)
    )
    duration_query = _apply_run_filters(
        duration_query,
        workflow_id=workflow_id,
        workflow_key=workflow_key,
        run_state=run_state,
        trace_id=trace_id,
        trigger_source=trigger_source,
        keyword=keyword,
    )
    duration_values = [
        value
        for value in (_duration_ms(started_at, ended_at) for started_at, ended_at in duration_query.all())
        if value is not None
    ]

    items = []
    for run, definition, version in rows:
        meta = step_meta.get(run.id, {})
        items.append(
            _to_run_item(
                run,
                definition,
                version,
                step_count=int(meta.get("step_count", 0)),
                failed_step_count=int(meta.get("failed_step_count", 0)),
                latest_error_message=meta.get("latest_error_message"),
            )
        )

    summary = _run_state_summary(state_counts)
    summary["avg_duration_ms"] = round(sum(duration_values) / len(duration_values), 2) if duration_values else 0.0

    return {
        "code": 0,
        "data": {
            "summary": summary,
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
        },
    }


@router.get("/runs/{run_id}")
async def get_workflow_run_detail(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("workflow_view")),
):
    row = (
        db.query(WorkflowRun, WorkflowDefinition, WorkflowVersion)
        .join(WorkflowDefinition, WorkflowDefinition.id == WorkflowRun.workflow_id)
        .join(WorkflowVersion, WorkflowVersion.id == WorkflowRun.workflow_version_id)
        .filter(WorkflowRun.id == run_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="workflow run not found")

    run, definition, version = row
    steps = db.query(WorkflowStepRun).filter(WorkflowStepRun.workflow_run_id == run_id).all()
    steps.sort(
        key=lambda item: (
            item.started_at or item.created_at or _utc_now(),
            item.attempt,
            item.id,
        )
    )
    failed_step_count = sum(1 for step in steps if str(step.step_state or "").upper() in {"FAILED", "MANUAL_REQUIRED"})
    latest_error_message = next((str(step.error_message)[:500] for step in reversed(steps) if step.error_message), None)

    return {
        "code": 0,
        "data": {
            "run": {
                **_to_run_item(
                    run,
                    definition,
                    version,
                    step_count=len(steps),
                    failed_step_count=failed_step_count,
                    latest_error_message=latest_error_message,
                ),
                "input_payload": _safe_json_value(run.input_payload),
                "output_payload": _safe_json_value(run.output_payload),
                "context": _safe_json_value(run.context_json),
                "input_summary": _payload_summary(run.input_payload),
                "output_summary": _payload_summary(run.output_payload),
                "context_summary": _payload_summary(run.context_json),
            },
            "steps": [_to_step_item(step) for step in steps],
        },
    }


@router.get("/runs/{run_id}/debug-report")
async def get_workflow_run_debug_report(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("workflow_view")),
):
    try:
        report = build_workflow_debug_report(db, run_id=run_id)
    except WorkflowRuntimeError as exc:
        raise _runtime_error_to_http(exc) from exc
    return {
        "code": 0,
        "data": report,
    }


@router.post("/runs/{run_id}/replay")
async def replay_workflow_run_api(
    run_id: int,
    payload: WorkflowReplayRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("workflow_edit")),
):
    try:
        replay = await replay_workflow_run(
            db,
            run_id=run_id,
            mode=payload.mode,
            overrides=payload.overrides,
            actor=str(current_user.username),
            trace_id=payload.trace_id,
        )
    except WorkflowRuntimeError as exc:
        raise _runtime_error_to_http(exc) from exc

    return {
        "code": 0,
        "data": {
            "source_run_id": replay.source_run_id,
            "source_run_state": replay.source_run_state,
            "workflow_key": replay.workflow_key,
            "workflow_version": replay.workflow_version,
            "mode": replay.mode,
            "resumed_from_node_id": replay.resumed_from_node_id,
            "replay_run_id": replay.replay_run.run_id,
            "replay_run_state": replay.replay_run.run_state,
            "replay_trace_id": replay.replay_run.trace_id,
            "replay_audit_path": _audit_trace_path(replay.replay_run.trace_id),
            "reused_existing": replay.replay_run.reused_existing,
            "debug_report": replay.debug_report,
        },
    }


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("workflow_view")),
):
    definition = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == workflow_id).first()
    if definition is None:
        raise HTTPException(status_code=404, detail="workflow not found")

    latest = _load_latest_version(db, workflow_id, definition.latest_version)
    try:
        dsl = json.loads(latest.dsl_json or "{}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"invalid workflow dsl snapshot: {exc}")

    return {
        "code": 0,
        "data": {
            "workflow": _to_definition_item(definition),
            "version": {
                "id": latest.id,
                "version": latest.version,
                "definition_state": latest.definition_state,
                "change_note": latest.change_note,
                "created_by": latest.created_by,
                "created_at": _iso(latest.created_at),
                "updated_at": _iso(latest.updated_at),
            },
            "dsl": dsl,
        },
    }


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: int,
    payload: WorkflowUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("workflow_edit")),
):
    definition = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == workflow_id).first()
    if definition is None:
        raise HTTPException(status_code=404, detail="workflow not found")

    if payload.version_tag != definition.latest_version:
        raise HTTPException(
            status_code=409,
            detail=f"version_tag mismatch: expected {definition.latest_version}, got {payload.version_tag}",
        )

    dsl_payload = _normalize_and_validate_dsl(definition.workflow_key, payload.dsl)
    now = _utc_now()
    next_version = definition.latest_version + 1

    snapshot = WorkflowVersion(
        workflow_id=definition.id,
        version=next_version,
        definition_state=str(dsl_payload.get("status", "DRAFT")).upper(),
        dsl_json=json.dumps(dsl_payload, ensure_ascii=False),
        change_note=payload.change_note,
        created_by=str(current_user.username),
        created_at=now,
        updated_at=now,
    )
    db.add(snapshot)

    definition.name = payload.name or str(dsl_payload.get("name") or definition.name)
    if payload.description is not None:
        definition.description = payload.description
    elif dsl_payload.get("description") is not None:
        definition.description = str(dsl_payload.get("description"))
    definition.definition_state = snapshot.definition_state
    definition.latest_version = next_version
    definition.updated_by = str(current_user.username)
    definition.updated_at = now

    db.commit()
    db.refresh(definition)

    return {
        "code": 0,
        "data": _to_definition_item(definition),
        "message": "workflow updated",
    }


@router.post("/{workflow_id}/validate")
async def validate_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("workflow_edit")),
):
    definition = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == workflow_id).first()
    if definition is None:
        raise HTTPException(status_code=404, detail="workflow not found")

    latest = _load_latest_version(db, workflow_id, definition.latest_version)
    try:
        dsl_payload = json.loads(latest.dsl_json or "{}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"invalid workflow dsl snapshot: {exc}")

    result = validate_workflow_publish(dsl_payload)
    if not result["valid"]:
        return {
            "code": 0,
            "data": {
                "workflow_id": definition.id,
                "workflow_key": definition.workflow_key,
                "version": latest.version,
                "valid": False,
                "errors": result["errors"],
                "warnings": result["warnings"],
                "summary": result["summary"],
            },
            "message": "workflow validation failed",
        }

    now = _utc_now()
    latest.definition_state = "VALIDATED"
    latest.updated_at = now
    definition.definition_state = "VALIDATED"
    definition.updated_by = str(current_user.username)
    definition.updated_at = now
    db.commit()

    return {
        "code": 0,
        "data": {
            "workflow_id": definition.id,
            "workflow_key": definition.workflow_key,
            "version": latest.version,
            "valid": True,
            "errors": [],
            "warnings": result["warnings"],
            "summary": result["summary"],
        },
        "message": "workflow validated",
    }


@router.post("/{workflow_id}/publish")
async def publish_workflow(
    workflow_id: int,
    payload: WorkflowPublishRequest,
    req: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("workflow_publish")),
):
    definition = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == workflow_id).first()
    if definition is None:
        raise HTTPException(status_code=404, detail="workflow not found")

    if payload.version_tag is not None and payload.version_tag != definition.latest_version:
        raise HTTPException(status_code=409, detail={
            "code": 40942,
            "message": f"version_tag mismatch: expected {definition.latest_version}, got {payload.version_tag}",
            "data": {"workflow_id": definition.id, "version_tag": payload.version_tag},
        })

    trace_id = payload.trace_id or getattr(req.state, "trace_id", None)
    actor = str(current_user.username)
    if not payload.approval_passed:
        raise HTTPException(status_code=400, detail={
            "code": 40042,
            "message": "workflow publish requires approval",
            "data": {"workflow_id": definition.id},
        })
    _ensure_confirmation(
        definition.workflow_key,
        payload.confirmation_text,
        error_code=40043,
        action="workflow publish",
    )
    publish_lock = get_publish_lock(definition.id)
    if not publish_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail={
            "code": 40941,
            "message": "workflow publish already in progress",
            "data": {"workflow_id": definition.id},
        })

    try:
        latest = _load_latest_version(db, workflow_id, definition.latest_version)
        validation_result = validate_workflow_publish(_load_version_dsl(latest))
        if not validation_result["valid"]:
            raise HTTPException(status_code=400, detail={
                "code": 40041,
                "message": "workflow publish validation failed",
                "data": {
                    "workflow_id": definition.id,
                    "workflow_key": definition.workflow_key,
                    "version": latest.version,
                    "validation": validation_result,
                },
            })

        released_dsl = apply_release_metadata(
            validation_result["normalized_dsl"],
            canary_percent=payload.canary_percent,
            effective_at=payload.effective_at,
            approval_reason=payload.approval_reason,
            actor=actor,
            trace_id=trace_id,
        )
        latest.dsl_json = json.dumps(released_dsl, ensure_ascii=False)
        now = _utc_now()
        previous_published_version = _set_published_version(
            db,
            definition,
            latest,
            actor=actor,
            now=now,
        )
        AuditService.log(
            db=db,
            actor=actor,
            action="workflow_publish",
            target=f"{definition.workflow_key}:v{latest.version}",
            target_type="workflow",
            reason=payload.approval_reason,
            result="success",
            trace_id=trace_id,
            auto_commit=False,
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail={
            "code": 50041,
            "message": "workflow publish failed",
            "data": {"workflow_id": definition.id, "detail": str(exc)},
        })
    finally:
        publish_lock.release()

    return {
        "code": 0,
        "data": {
            "workflow_id": definition.id,
            "workflow_key": definition.workflow_key,
            "version": latest.version,
            "published_version": definition.published_version,
            "previous_published_version": previous_published_version,
            "definition_state": definition.definition_state,
            "canary_percent": payload.canary_percent,
            "effective_at": _iso(payload.effective_at),
            "approval_reason": payload.approval_reason,
            "trace_id": trace_id,
        },
        "message": "workflow published",
    }


@router.post("/{workflow_id}/rollback")
async def rollback_workflow(
    workflow_id: int,
    payload: WorkflowRollbackRequest,
    req: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("workflow_rollback")),
):
    definition = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == workflow_id).first()
    if definition is None:
        raise HTTPException(status_code=404, detail="workflow not found")

    trace_id = payload.trace_id or getattr(req.state, "trace_id", None)
    actor = str(current_user.username)
    _ensure_confirmation(
        definition.workflow_key,
        payload.confirmation_text,
        error_code=40044,
        action="workflow rollback",
    )
    publish_lock = get_publish_lock(definition.id)
    if not publish_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail={
            "code": 40941,
            "message": "workflow publish already in progress",
            "data": {"workflow_id": definition.id},
        })

    try:
        target_version = _load_target_version(db, definition.id, payload.target_version)
        now = _utc_now()
        previous_published_version = _set_published_version(
            db,
            definition,
            target_version,
            actor=actor,
            now=now,
        )
        AuditService.log(
            db=db,
            actor=actor,
            action="workflow_rollback",
            target=f"{definition.workflow_key}:v{payload.target_version}",
            target_type="workflow",
            reason=payload.reason,
            result="success",
            trace_id=trace_id,
            auto_commit=False,
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail={
            "code": 50042,
            "message": "workflow rollback failed",
            "data": {"workflow_id": definition.id, "detail": str(exc)},
        })
    finally:
        publish_lock.release()

    return {
        "code": 0,
        "data": {
            "workflow_id": definition.id,
            "workflow_key": definition.workflow_key,
            "rolled_back_to_version": target_version.version,
            "previous_published_version": previous_published_version,
            "published_version": definition.published_version,
            "definition_state": definition.definition_state,
            "reason": payload.reason,
            "trace_id": trace_id,
        },
        "message": "workflow rolled back",
    }
