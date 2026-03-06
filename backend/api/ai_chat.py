from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta, timezone

from core.database import (
    get_db, AIChatSession, AIChatMessage, ThreatEvent, ScanTask, ScanFinding, User,
)
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

def _build_context_summary(db: Session, req: ChatRequest, session: "AIChatSession") -> str:
    """根据 context_type 从数据库构建上下文摘要"""
    parts: list[str] = []
    ctx_type = req.context_type or session.context_type
    ctx_id = req.context_id or (str(session.context_id) if session.context_id else None)

    if ctx_type == "event" and ctx_id:
        ev = db.query(ThreatEvent).filter(ThreatEvent.id == int(ctx_id)).first()
        if ev:
            parts.append(
                f"[关联事件#{ev.id}] IP={ev.ip} 来源={ev.source} 标签={ev.threat_label} "
                f"AI评分={ev.ai_score} 状态={ev.status}"
            )
    elif ctx_type == "scan_task" and ctx_id:
        task = db.query(ScanTask).filter(ScanTask.id == int(ctx_id)).first()
        if task:
            parts.append(
                f"[关联扫描#{task.id}] 目标={task.target} 工具={task.tool_name} "
                f"状态={task.state} Profile={task.profile}"
            )
            findings_count = db.query(func.count(ScanFinding.id)).filter(
                ScanFinding.scan_task_id == task.id
            ).scalar() or 0
            high_count = db.query(func.count(ScanFinding.id)).filter(
                ScanFinding.scan_task_id == task.id, ScanFinding.severity == "HIGH"
            ).scalar() or 0
            parts.append(f"发现{findings_count}个漏洞（{high_count}个高危）")

    # 统计概览
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_alerts = db.query(func.count(ThreatEvent.id)).filter(
        ThreatEvent.created_at >= today
    ).scalar() or 0
    pending_events = db.query(func.count(ThreatEvent.id)).filter(
        ThreatEvent.status == "PENDING"
    ).scalar() or 0
    parts.append(f"系统概况: 今日告警{today_alerts}条, 待处理{pending_events}条")

    return " | ".join(parts)


def _generate_ai_reply(user_message: str, context: str) -> str:
    """
    基于用户消息和上下文生成 AI 回复。
    当前为模板回复，后续替换为真实 AI 模型调用。
    """
    msg_lower = user_message.lower()

    if any(kw in msg_lower for kw in ["分析", "解读", "判断"]):
        return f"基于当前数据分析：{context}。建议优先处理高危事件，并关注重复攻击 IP 的行为模式。"
    elif any(kw in msg_lower for kw in ["封禁", "阻断", "block"]):
        return f"当前系统状态：{context}。封禁建议：对 AI 评分 ≥ 80 的 IP 建议立即封禁，60-79 分建议观察后处理。"
    elif any(kw in msg_lower for kw in ["漏洞", "扫描", "scan"]):
        return f"扫描情况：{context}。建议优先修复高危漏洞，并对开放敏感端口（22/3389/445）的主机加强防护。"
    elif any(kw in msg_lower for kw in ["报告", "汇总", "总结"]):
        return f"系统摘要：{context}。如需详细报告，可在右侧面板生成日报或周报。"
    else:
        return f"收到您的消息。{context}。请问需要我进一步分析哪方面的安全态势？"


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
    
    # 构建上下文摘要
    context_summary = _build_context_summary(db, req, session)
    response_content = _generate_ai_reply(req.message, context_summary)
    
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