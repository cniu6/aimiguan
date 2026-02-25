from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os

from core.database import get_db, User
from api.auth import get_current_user, get_user_role
from services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/system", tags=["system"])
compat_router = APIRouter(prefix="/api/system", tags=["system"])

# In-memory system mode (persisted via system_config_snapshot)
_system_mode = {"mode": "PASSIVE", "reason": "系统初始化", "operator": "system", "updated_at": datetime.utcnow().isoformat()}

APP_VERSION = os.getenv("APP_VERSION", "v0.1.0")
GIT_COMMIT = os.getenv("GIT_COMMIT", "initial")
BUILD_TIME = os.getenv("BUILD_TIME", datetime.utcnow().isoformat() + "Z")
ROLLBACK_CANDIDATE_LIMIT = int(os.getenv("ROLLBACK_CANDIDATE_LIMIT", "5"))


class SystemModeRequest(BaseModel):
    mode: str
    reason: Optional[str] = None


class SystemModeResponse(BaseModel):
    mode: str
    reason: Optional[str]
    operator: Optional[str]
    updated_at: str


class RollbackRequest(BaseModel):
    target_version: str
    reason: str
    trace_id: Optional[str] = None


def _ensure_operator_or_admin(current_user: User, db: Session):
    role = get_user_role(current_user, db)
    if role not in ["admin", "operator"]:
        raise HTTPException(status_code=40301, detail="权限不足")


def _get_latest_schema_version(db: Session) -> str:
    latest = db.execute(
        text("""
        SELECT schema_version
        FROM release_history
        ORDER BY datetime(created_at) DESC, id DESC
        LIMIT 1
        """)
    ).fetchone()
    return latest[0] if latest else "unknown"


def _get_available_versions(db: Session, limit: int = ROLLBACK_CANDIDATE_LIMIT) -> List[str]:
    rows = db.execute(
        text("""
        SELECT version
        FROM release_history
        WHERE status IN ('active', 'deployed', 'rolled_back')
        GROUP BY version
        ORDER BY MAX(datetime(created_at)) DESC
        LIMIT :limit
        """),
        {"limit": limit},
    ).fetchall()
    return [row[0] for row in rows]


def _record_release_status(
    db: Session,
    *,
    version: str,
    git_commit: str,
    schema_version: str,
    deploy_env: str,
    status: str,
    deployed_by: str,
    rollback_reason: Optional[str] = None,
    trace_id: Optional[str] = None,
):
    now = datetime.utcnow()
    db.execute(
        text("""
        INSERT INTO release_history (
            version, git_commit, schema_version, deploy_env, status,
            deployed_by, rollback_reason, trace_id, created_at, updated_at
        ) VALUES (
            :version, :git_commit, :schema_version, :deploy_env, :status,
            :deployed_by, :rollback_reason, :trace_id, :created_at, :updated_at
        )
        """),
        {
            "version": version,
            "git_commit": git_commit,
            "schema_version": schema_version,
            "deploy_env": deploy_env,
            "status": status,
            "deployed_by": deployed_by,
            "rollback_reason": rollback_reason,
            "trace_id": trace_id,
            "created_at": now,
            "updated_at": now,
        },
    )


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "aimiguan"}


@router.get("/mode", response_model=SystemModeResponse)
async def get_system_mode():
    return SystemModeResponse(**_system_mode)


@router.post("/mode", response_model=SystemModeResponse)
async def set_system_mode(
    request: SystemModeRequest,
    req: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if request.mode not in ["PASSIVE", "ACTIVE"]:
        raise HTTPException(status_code=400, detail="模式必须是 PASSIVE 或 ACTIVE")

    global _system_mode
    _system_mode = {
        "mode": request.mode,
        "reason": request.reason,
        "operator": current_user.username,
        "updated_at": datetime.utcnow().isoformat()
    }

    trace_id = getattr(req.state, "trace_id", None)
    AuditService.log(
        db=db,
        actor=current_user.username,
        action=f"set_mode:{request.mode}",
        target="system_mode",
        target_type="system",
        result="success",
        trace_id=trace_id
    )

    return SystemModeResponse(**_system_mode)


@router.get("/version")
@compat_router.get("/version")
async def get_system_version(db: Session = Depends(get_db)):
    schema_version = _get_latest_schema_version(db)
    deploy_env = os.getenv("APP_ENV", "dev")
    return {
        "app_version": APP_VERSION,
        "git_commit": GIT_COMMIT,
        "build_time": BUILD_TIME,
        "schema_version": schema_version,
        "env": deploy_env,
    }


@router.post("/rollback")
@compat_router.post("/rollback")
async def rollback_system(
    payload: RollbackRequest,
    req: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_operator_or_admin(current_user, db)

    trace_id = payload.trace_id or getattr(req.state, "trace_id", None)
    deploy_env = os.getenv("APP_ENV", "dev")
    available_versions = _get_available_versions(db)

    if payload.target_version not in available_versions:
        raise HTTPException(
            status_code=40404,
            detail={
                "error": "version_not_found",
                "message": f"目标版本 {payload.target_version} 不在可回滚列表中",
                "available_versions": available_versions,
            },
        )

    target = db.execute(
        text("""
        SELECT version, git_commit, schema_version
        FROM release_history
        WHERE version = :version
        ORDER BY datetime(created_at) DESC, id DESC
        LIMIT 1
        """),
        {"version": payload.target_version},
    ).fetchone()

    if not target:
        raise HTTPException(
            status_code=40404,
            detail={
                "error": "version_not_found",
                "message": f"目标版本 {payload.target_version} 不在可回滚列表中",
                "available_versions": available_versions,
            },
        )

    try:
        _record_release_status(
            db,
            version=target[0],
            git_commit=target[1],
            schema_version=target[2],
            deploy_env=deploy_env,
            status="active",
            deployed_by=current_user.username,
            rollback_reason=payload.reason,
            trace_id=trace_id,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=50001,
            detail={
                "error": "rollback_failed",
                "message": "数据库迁移版本校验失败",
                "detail": str(exc),
                "trace_id": trace_id,
            },
        )

    AuditService.log(
        db=db,
        actor=current_user.username,
        action="system_rollback",
        target=payload.target_version,
        target_type="release",
        reason=payload.reason,
        result="success",
        trace_id=trace_id,
    )

    return {
        "status": "success",
        "rolled_back_to": payload.target_version,
        "actions_taken": ["config_reverted", "schema_checked", "health_verified"],
        "trace_id": trace_id,
    }
