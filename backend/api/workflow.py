"""Workflow management APIs (M1-03)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.auth import require_permissions
from core.database import (
    User,
    WorkflowDefinition,
    WorkflowVersion,
    get_db,
)
from services.audit_service import AuditService
from services.workflow_release import apply_release_metadata, get_publish_lock
from services.workflow_dsl import validate_workflow_dsl
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
    trace_id: Optional[str] = Field(default=None, max_length=128)


class WorkflowRollbackRequest(BaseModel):
    target_version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=500)
    trace_id: Optional[str] = Field(default=None, max_length=128)


@router.get("")
async def list_workflows(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    definition_state: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("system:config")),
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
    current_user: User = Depends(require_permissions("system:config")),
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


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("system:config")),
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
    current_user: User = Depends(require_permissions("system:config")),
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
    current_user: User = Depends(require_permissions("system:config")),
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
    current_user: User = Depends(require_permissions("system:config")),
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
    current_user: User = Depends(require_permissions("system:config")),
):
    definition = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == workflow_id).first()
    if definition is None:
        raise HTTPException(status_code=404, detail="workflow not found")

    trace_id = payload.trace_id or getattr(req.state, "trace_id", None)
    actor = str(current_user.username)
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
