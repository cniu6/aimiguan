from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from core.database import get_db, AIChatSession, AIChatMessage, User
from api.auth import require_permissions

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

class ChatRequest(BaseModel):
    message: str
    context_type: Optional[str] = None
    context_id: Optional[str] = None

class ChatMessage(BaseModel):
    role: str
    content: str
    created_at: datetime

@router.post("/chat")
async def chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("ai_chat"))
):
    """AI 多轮对话"""
    # TODO: Implement AI chat logic with context awareness
    # For now, return a placeholder response
    
    response_content = f"AI response to: {req.message}"
    
    return {
        "code": 0,
        "data": {
            "message": response_content,
            "context": {
                "type": req.context_type,
                "id": req.context_id
            }
        }
    }

@router.get("/sessions")
async def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("view_ai_sessions"))
):
    """获取对话会话列表"""
    sessions = db.query(AIChatSession).order_by(AIChatSession.started_at.desc()).limit(50).all()
    return {"code": 0, "data": sessions}

@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessage])
async def get_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("view_ai_sessions"))
):
    """获取会话消息历史"""
    messages = db.query(AIChatMessage).filter(
        AIChatMessage.session_id == session_id
    ).order_by(AIChatMessage.created_at.asc()).all()
    return messages