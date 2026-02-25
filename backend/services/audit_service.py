from sqlalchemy.orm import Session
from core.database import AuditLog
from datetime import datetime, timezone
from typing import Optional
import uuid


class AuditService:
    @staticmethod
    def log(
        db: Session,
        actor: str,
        action: str,
        target: str,
        result: str = "success",
        target_type: Optional[str] = None,
        target_ip: Optional[str] = None,
        reason: Optional[str] = None,
        error_message: Optional[str] = None,
        trace_id: Optional[str] = None,
        auto_commit: bool = True,
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
            created_at=datetime.now(timezone.utc),
        )
        db.add(audit)
        if auto_commit:
            db.commit()
        return audit
