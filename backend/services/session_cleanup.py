"""会话清理服务 - S1-03 上下文隔离要求"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from core.database import AIChatSession, AIChatMessage
import logging

logger = logging.getLogger(__name__)

class SessionCleanupService:
    """会话过期清理服务"""
    
    @staticmethod
    def cleanup_expired_sessions(db: Session) -> int:
        """清理过期会话及其上下文缓存"""
        now = datetime.now(timezone.utc)
        
        # 查找所有过期会话
        expired_sessions = db.query(AIChatSession).filter(
            AIChatSession.expires_at.isnot(None),
            AIChatSession.expires_at < now,
            AIChatSession.ended_at.is_(None)
        ).all()
        
        cleaned_count = 0
        for session in expired_sessions:
            # 标记会话为已结束
            session.ended_at = now
            
            # 删除会话消息（清除上下文缓存）
            deleted = db.query(AIChatMessage).filter(
                AIChatMessage.session_id == session.id
            ).delete()
            
            logger.info(f"Cleaned expired session {session.id}: deleted {deleted} messages")
            cleaned_count += 1
        
        db.commit()
        return cleaned_count
    
    @staticmethod
    def force_end_session(db: Session, session_id: int) -> bool:
        """强制结束会话并清除上下文"""
        session = db.query(AIChatSession).filter(AIChatSession.id == session_id).first()
        if not session:
            return False
        
        session.ended_at = datetime.now(timezone.utc)
        
        # 清除消息
        db.query(AIChatMessage).filter(
            AIChatMessage.session_id == session_id
        ).delete()
        
        db.commit()
        logger.info(f"Force ended session {session_id}")
        return True
