"""Workflow management APIs (M1-03)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
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
from services.workflow_dsl import validate_workflow_dsl

router = APIRouter(prefix="/api/v1/workflows", tags=["workflow"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _to_definition_item(model: WorkflowDefinition) -> Dict[str, Any]:
    return {
        "id": model.id,
        "workflow_key": model.workflow_key,
        "name": model.name,
        "description": model.description,
        "definition_state": model.definition_state,
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


def _normalize_and_validate_dsl(workflow_key: str, dsl: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(dsl)
    if not payload.get("workflow_id"):
        payload["workflow_id"] = workflow_key
    if str(payload.get("workflow_id")) != workflow_key:
        raise HTTPException(status_code=400, detail="dsl.workflow_id must match workflow_key")
    validated = validate_workflow_dsl(payload)
    return validated.model_dump(by_alias=True)


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

    try:
        validate_workflow_dsl(dsl_payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"dsl validation failed: {exc}")

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
        },
        "message": "workflow validated",
    }
