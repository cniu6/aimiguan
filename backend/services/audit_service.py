from sqlalchemy.orm import Session
from core.database import AuditLog
from datetime import datetime
import uuid

class AuditService:
    @staticmethod
    def log(
        db: Session,
        actor: str,
        action: str,
        target: str,
        result: str = "success",
        target_type: str = None,
        target_ip: str = None,
        reason: str = None,
        error_message: str = None,
        trace_id: str = None
    ):
        """统一审计日志写入"""
        audit = AuditLog(
            actor=actor,
            action=action,
            target=target,
            target_type=target_type,
            target_ip=target_ip,
            reason=reason,
            result=result,
            error_message=error_message,
            trace_id=trace_id or str(uuid.uuid4()),
            created_at=datetime.utcnow()
        )
        db.add(audit)
        db.commit()
        return audit
