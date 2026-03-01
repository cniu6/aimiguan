from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from core.database import get_db, AITTSTask, User
from api.auth import require_permissions

router = APIRouter(prefix="/api/v1/tts", tags=["tts"])

class TTSRequest(BaseModel):
    text: str
    voice_model: Optional[str] = "default"
    source_type: Optional[str] = None
    source_id: Optional[str] = None

@router.post("/tasks")
async def create_tts_task(
    req: TTSRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("create_tts_task"))
):
    """创建 TTS 任务"""
    task = AITTSTask(
        source_type=req.source_type,
        source_id=req.source_id,
        voice_model=req.voice_model,
        state="PENDING"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # TODO: Trigger TTS processing
    
    return {"code": 0, "message": "TTS task created", "data": {"task_id": task.id}}

@router.get("/tasks/{task_id}")
async def get_tts_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("view_tts_tasks"))
):
    """获取 TTS 任务状态"""
    task = db.query(AITTSTask).filter(AITTSTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"code": 0, "data": task}