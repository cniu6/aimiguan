from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import hashlib
import uuid

from core.database import get_db, FirewallSyncTask, User
from api.auth import require_permissions

router = APIRouter(prefix="/api/v1/firewall", tags=["firewall"])

class FirewallSyncRequest(BaseModel):
    ip: str
    action: str  # block, unblock
    firewall_vendor: Optional[str] = "generic"

@router.post("/sync")
async def sync_to_firewall(
    req: FirewallSyncRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("firewall_sync"))
):
    """同步封堵到外部防火墙"""
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
    
    # Generate request hash for idempotency
    request_hash = hashlib.sha256(
        f"{req.ip}:{req.action}:{req.firewall_vendor}".encode()
    ).hexdigest()
    
    # Check if already exists
    existing = db.query(FirewallSyncTask).filter(
        FirewallSyncTask.request_hash == request_hash
    ).first()
    
    if existing:
        return {
            "code": 0,
            "message": "Task already exists",
            "data": {"task_id": existing.id, "state": existing.state}
        }
    
    task = FirewallSyncTask(
        ip=req.ip,
        firewall_vendor=req.firewall_vendor,
        request_hash=request_hash,
        state="PENDING"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # TODO: Trigger firewall sync service
    
    return {
        "code": 0,
        "message": "Firewall sync task created",
        "data": {"task_id": task.id, "trace_id": trace_id}
    }

@router.get("/tasks/{task_id}")
async def get_firewall_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("view_firewall_tasks"))
):
    """获取防火墙同步任务状态"""
    task = db.query(FirewallSyncTask).filter(FirewallSyncTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"code": 0, "data": task}