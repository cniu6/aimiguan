from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta, timezone

from core.database import get_db, AIChatSession, AIChatMessage, User
from api.auth import require_permissions

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = None
    context_type: Optional[str] = None
    context_id: Optional[str] = None

class ChatMessage(BaseModel):
    role: str
    content: str
    created_at: datetime

def verify_session_ownership(session: AIChatSession, user: User) -> None:
    """验证会话归属权（S1-03 安全要求）"""
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问此会话")
    
    # 检查会话是否过期
    if session.expires_at:
        # 将数据库中的 naive datetime 转换为 UTC aware datetime
        expires_at_utc = session.expires_at.replace(tzinfo=timezone.utc) if session.expires_at.tzinfo is None else session.expires_at
        if expires_at_utc < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="会话已过期")

@router.post("/chat")
async def chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("ai_chat"))
):
    """AI 多轮对话（带会话隔离）"""
    session = None
    
    # 如果提供了 session_id，验证归属权
    if req.session_id:
        session = db.query(AIChatSession).filter(AIChatSession.id == req.session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        verify_session_ownership(session, current_user)
    else:
        # 创建新会话（默认 24 小时过期）
        session = AIChatSession(
            user_id=current_user.id,
            operator=current_user.username,
            context_type=req.context_type,
            context_id=req.context_id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        db.add(session)
        db.flush()
    
    # 保存用户消息
    user_msg = AIChatMessage(
        session_id=session.id,
        role="user",
        content=req.message,
        created_at=datetime.now(timezone.utc)
    )
    db.add(user_msg)
    
    # AI 响应（占位实现）
    response_content = f"AI response to: {req.message}"
    
    ai_msg = AIChatMessage(
        session_id=session.id,
        role="assistant",
        content=response_content,
        created_at=datetime.now(timezone.utc)
    )
    db.add(ai_msg)
    db.commit()
    
    return {
        "code": 0,
        "data": {
            "session_id": session.id,
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
    """获取对话会话列表（仅返回当前用户的会话）"""
    sessions = db.query(AIChatSession).filter(
        AIChatSession.user_id == current_user.id
    ).order_by(AIChatSession.started_at.desc()).limit(50).all()
    return {"code": 0, "data": sessions}

@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessage])
async def get_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("view_ai_sessions"))
):
    """获取会话消息历史（带归属权验证）"""
    session = db.query(AIChatSession).filter(AIChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    verify_session_ownership(session, current_user)
    
    messages = db.query(AIChatMessage).filter(
        AIChatMessage.session_id == session_id
    ).order_by(AIChatMessage.created_at.asc()).all()
    return messages

@router.get("/chat/{session_id}/context")
async def get_session_context(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("view_ai_sessions"))
):
    """获取会话上下文（S1-03 要求的接口，带 RBAC 校验）"""
    session = db.query(AIChatSession).filter(AIChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    verify_session_ownership(session, current_user)
    
    # 获取会话的所有消息作为上下文
    messages = db.query(AIChatMessage).filter(
        AIChatMessage.session_id == session_id
    ).order_by(AIChatMessage.created_at.asc()).all()
    
    return {
        "code": 0,
        "data": {
            "session_id": session.id,
            "user_id": session.user_id,
            "context_type": session.context_type,
            "context_id": session.context_id,
            "started_at": session.started_at,
            "expires_at": session.expires_at,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at
                }
                for msg in messages
            ]
        }
    }