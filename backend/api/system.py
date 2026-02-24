from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import sqlite3

from core.database import get_db, User
from api.auth import get_current_user
from services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/system", tags=["system"])

# In-memory system mode (persisted via system_config_snapshot)
_system_mode = {"mode": "PASSIVE", "reason": "系统初始化", "operator": "system", "updated_at": datetime.utcnow().isoformat()}

class SystemModeRequest(BaseModel):
    mode: str
    reason: Optional[str] = None

class SystemModeResponse(BaseModel):
    mode: str
    reason: Optional[str]
    operator: Optional[str]
    updated_at: str

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
