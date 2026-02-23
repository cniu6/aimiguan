from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

from core.database import get_db, ThreatEvent, ExecutionTask

router = APIRouter(prefix="/api/v1/defense", tags=["defense"])

class HFishAlert(BaseModel):
    ip: str
    source: str
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

@router.post("/alerts")
async def receive_alert(alert: HFishAlert, request: Request, db: Session = Depends(get_db)):
    """接收 HFish 告警"""
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
    
    # TODO: Call AI engine for risk assessment
    ai_score = 75  # Placeholder
    ai_reason = "High frequency attack detected"
    
    event = ThreatEvent(
        ip=alert.ip,
        source=alert.source,
        ai_score=ai_score,
        ai_reason=ai_reason,
        status="PENDING",
        trace_id=trace_id
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    
    return {
        "code": 0,
        "message": "Alert received",
        "data": {"event_id": event.id, "trace_id": trace_id}
    }

@router.get("/events", response_model=List[EventResponse])
async def get_events(status: Optional[str] = None, db: Session = Depends(get_db)):
    """获取威胁事件列表"""
    query = db.query(ThreatEvent)
    if status:
        query = query.filter(ThreatEvent.status == status)
    events = query.order_by(ThreatEvent.created_at.desc()).limit(100).all()
    return events

@router.post("/events/{event_id}/approve")
async def approve_event(event_id: int, req: ApproveRequest, request: Request, db: Session = Depends(get_db)):
    """批准处置事件"""
    event = db.query(ThreatEvent).filter(ThreatEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event.status = "APPROVED"
    event.updated_at = datetime.utcnow()
    
    # TODO: Trigger MCP client to block IP
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
    task = ExecutionTask(
        event_id=event_id,
        action="BLOCK",
        state="PENDING",
        trace_id=trace_id
    )
    db.add(task)
    db.commit()
    
    return {"code": 0, "message": "Event approved", "data": {"task_id": task.id}}

@router.post("/events/{event_id}/reject")
async def reject_event(event_id: int, req: ApproveRequest, db: Session = Depends(get_db)):
    """驳回处置事件"""
    event = db.query(ThreatEvent).filter(ThreatEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event.status = "REJECTED"
    event.updated_at = datetime.utcnow()
    db.commit()
    
    return {"code": 0, "message": "Event rejected"}