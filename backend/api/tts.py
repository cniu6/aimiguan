from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from core.database import get_db, AITTSTask, User
from core.response import APIResponse
from api.auth import require_permissions
from services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/tts", tags=["tts"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TTSRequest(BaseModel):
    text: str
    voice_model: Optional[str] = "local-tts-v1"
    source_type: Optional[str] = None
    source_id: Optional[int] = None


class TTSStatusUpdate(BaseModel):
    state: str  # PROCESSING, SUCCESS, FAILED
    audio_path: Optional[str] = None
    error_message: Optional[str] = None


@router.post("/tasks")
async def create_tts_task(
    req: TTSRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("create_tts_task")),
):
    """创建 TTS 语音合成任务"""
    trace_id = getattr(request.state, "trace_id", None) or str(uuid.uuid4())

    task = AITTSTask(
        source_type=req.source_type or "manual",
        source_id=req.source_id,
        text_content=req.text,
        voice_model=req.voice_model or "local-tts-v1",
        state="PENDING",
        trace_id=trace_id,
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    AuditService.log(
        db=db,
        actor=str(current_user.username),
        action="create_tts_task",
        target=str(task.id),
        target_type="tts_task",
        trace_id=trace_id,
    )

    return APIResponse.success(
        {
            "task_id": task.id,
            "state": task.state,
            "text_length": len(req.text),
        },
        message="TTS 任务已创建",
        trace_id=trace_id,
    )


@router.get("/tasks")
async def list_tts_tasks(
    state: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("view_tts_tasks")),
):
    """TTS 任务列表（支持状态筛选 + 分页）"""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20

    query = db.query(AITTSTask)
    if state:
        query = query.filter(AITTSTask.state == state)

    total = query.count()
    tasks = (
        query.order_by(AITTSTask.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return APIResponse.success({
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": t.id,
                "source_type": t.source_type,
                "source_id": t.source_id,
                "text_preview": (t.text_content or "")[:80],
                "voice_model": t.voice_model,
                "audio_path": t.audio_path,
                "state": t.state,
                "error_message": t.error_message,
                "trace_id": t.trace_id,
                "created_at": t.created_at.isoformat().replace("+00:00", "Z") if t.created_at else None,
                "updated_at": t.updated_at.isoformat().replace("+00:00", "Z") if t.updated_at else None,
            }
            for t in tasks
        ],
    })


@router.get("/tasks/{task_id}")
async def get_tts_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("view_tts_tasks")),
):
    """获取 TTS 任务详情"""
    task = db.query(AITTSTask).filter(AITTSTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="TTS 任务不存在")

    return APIResponse.success({
        "id": task.id,
        "source_type": task.source_type,
        "source_id": task.source_id,
        "text_content": task.text_content,
        "voice_model": task.voice_model,
        "audio_path": task.audio_path,
        "state": task.state,
        "error_message": task.error_message,
        "trace_id": task.trace_id,
        "created_at": task.created_at.isoformat().replace("+00:00", "Z") if task.created_at else None,
        "updated_at": task.updated_at.isoformat().replace("+00:00", "Z") if task.updated_at else None,
    })


@router.post("/tasks/{task_id}/process")
async def process_tts_task(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("create_tts_task")),
):
    """
    模拟执行 TTS 任务（将状态推进到 SUCCESS）。
    实际部署时替换为真实 TTS 引擎调用。
    """
    task = db.query(AITTSTask).filter(AITTSTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="TTS 任务不存在")

    if task.state not in ("PENDING", "FAILED"):
        raise HTTPException(status_code=400, detail=f"当前状态 {task.state} 不允许重新处理")

    trace_id = getattr(request.state, "trace_id", None) or task.trace_id
    now = _utc_now()

    task.state = "SUCCESS"
    task.audio_path = f"/audio/tts_{task.id}_{now.strftime('%Y%m%d%H%M%S')}.mp3"
    task.updated_at = now
    db.commit()

    AuditService.log(
        db=db,
        actor=str(current_user.username),
        action="process_tts_task",
        target=str(task.id),
        target_type="tts_task",
        trace_id=trace_id,
    )

    return APIResponse.success(
        {
            "task_id": task.id,
            "state": task.state,
            "audio_path": task.audio_path,
        },
        message="TTS 任务处理完成",
        trace_id=trace_id,
    )
