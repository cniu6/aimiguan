from sqlalchemy.orm import Session
from core.database import AuditLog
from datetime import datetime, timezone
from typing import Optional
import hashlib
import uuid


def _compute_hash(
    actor: str, action: str, target: str, result: str,
    trace_id: str, created_at: str, prev_hash: str,
) -> str:
    """SHA-256 哈希链：当前记录内容 + 前一条哈希 -> 不可篡改"""
    payload = f"{actor}|{action}|{target}|{result}|{trace_id}|{created_at}|{prev_hash}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
        """统一审计日志写入（含哈希链不可篡改校验）"""
        trace_id = trace_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        # 获取前一条日志的 integrity_hash
        prev = db.query(AuditLog.integrity_hash).order_by(
            AuditLog.id.desc()
        ).first()
        prev_hash = prev[0] if prev and prev[0] else "GENESIS"

        integrity_hash = _compute_hash(
            actor, action, target, result, trace_id, now_iso, prev_hash,
        )

        audit = AuditLog(
            actor=actor,
            action=action,
            target=target,
            target_type=target_type,
            target_ip=target_ip,
            reason=reason,
            result=result,
            error_message=error_message,
            trace_id=trace_id,
            integrity_hash=integrity_hash,
            prev_hash=prev_hash,
            created_at=now,
        )
        db.add(audit)
        if auto_commit:
            db.commit()
        return audit

    @staticmethod
    def verify_chain(db: Session, limit: int = 100) -> dict:
        """
        校验审计日志哈希链完整性。
        返回 {"valid": bool, "checked": int, "broken_at": int|None}
        """
        logs = (
            db.query(AuditLog)
            .order_by(AuditLog.id.asc())
            .limit(limit)
            .all()
        )

        if not logs:
            return {"valid": True, "checked": 0, "broken_at": None}

        for i, log in enumerate(logs):
            if not log.integrity_hash:
                continue

            expected_prev = "GENESIS"
            if i > 0 and logs[i - 1].integrity_hash:
                expected_prev = logs[i - 1].integrity_hash

            if log.prev_hash and log.prev_hash != expected_prev:
                return {"valid": False, "checked": i + 1, "broken_at": log.id}

            expected_hash = _compute_hash(
                log.actor, log.action, log.target, log.result,
                log.trace_id, log.created_at.isoformat() if log.created_at else "",
                log.prev_hash or "GENESIS",
            )
            if log.integrity_hash != expected_hash:
                return {"valid": False, "checked": i + 1, "broken_at": log.id}

        return {"valid": True, "checked": len(logs), "broken_at": None}
