from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from core.database import get_db, ScanTask, ScanFinding

router = APIRouter(prefix="/api/v1/scan", tags=["scan"])

class CreateScanRequest(BaseModel):
    target: str
    target_type: Optional[str] = "host"
    tool_name: Optional[str] = "nmap"

class ScanTaskResponse(BaseModel):
    id: int
    target: str
    tool_name: Optional[str]
    state: str
    created_at: datetime

@router.post("/tasks")
async def create_scan_task(req: CreateScanRequest, db: Session = Depends(get_db)):
    """创建扫描任务"""
    task = ScanTask(
        target=req.target,
        target_type=req.target_type,
        tool_name=req.tool_name,
        state="PENDING"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # TODO: Trigger scanner service
    
    return {"code": 0, "message": "Scan task created", "data": {"task_id": task.id}}

@router.get("/tasks", response_model=List[ScanTaskResponse])
async def get_scan_tasks(state: Optional[str] = None, db: Session = Depends(get_db)):
    """获取扫描任务列表"""
    query = db.query(ScanTask)
    if state:
        query = query.filter(ScanTask.state == state)
    tasks = query.order_by(ScanTask.created_at.desc()).limit(100).all()
    return tasks

@router.get("/tasks/{task_id}")
async def get_scan_task(task_id: int, db: Session = Depends(get_db)):
    """获取扫描任务详情"""
    task = db.query(ScanTask).filter(ScanTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    findings = db.query(ScanFinding).filter(ScanFinding.scan_task_id == task_id).all()
    
    return {
        "code": 0,
        "data": {
            "task": task,
            "findings": findings
        }
    }