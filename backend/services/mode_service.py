import json
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.database import SystemConfigSnapshot
from services.audit_service import AuditService

MODE_CONFIG_KEY = "system_mode"
DEFAULT_MODE_PAYLOAD = {
    "mode": "PASSIVE",
    "reason": "系统初始化",
    "operator": "system",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso(ts: Optional[datetime] = None) -> str:
    current = ts or _utc_now()
    return current.isoformat().replace("+00:00", "Z")


def get_current_mode(db: Session, env: str) -> Dict[str, str]:
    row = db.execute(
        text(
            """
            SELECT config_value, loaded_at
            FROM system_config_snapshot
            WHERE config_key = :config_key AND env = :env
            ORDER BY loaded_at DESC, id DESC
            LIMIT 1
            """
        ),
        {"config_key": MODE_CONFIG_KEY, "env": env},
    ).fetchone()

    if not row:
        return {**DEFAULT_MODE_PAYLOAD, "updated_at": _utc_iso()}

    try:
        payload = json.loads(row[0]) if row[0] else {}
    except (TypeError, json.JSONDecodeError):
        payload = {}

    mode = payload.get("mode") if isinstance(payload, dict) else None
    reason = payload.get("reason") if isinstance(payload, dict) else None
    operator = payload.get("operator") if isinstance(payload, dict) else None
    updated_at = payload.get("updated_at") if isinstance(payload, dict) else None

    return {
        "mode": mode if mode in {"PASSIVE", "ACTIVE"} else "PASSIVE",
        "reason": reason,
        "operator": operator if operator else "system",
        "updated_at": updated_at if updated_at else _utc_iso(row[1]),
    }


def set_mode(
    db: Session,
    *,
    mode: str,
    reason: Optional[str],
    operator: str,
    env: str,
    trace_id: Optional[str],
) -> Dict[str, str]:
    now = _utc_now()
    payload = {
        "mode": mode,
        "reason": reason,
        "operator": operator,
        "updated_at": _utc_iso(now),
    }

    snapshot = SystemConfigSnapshot(
        config_key=MODE_CONFIG_KEY,
        config_value=json.dumps(payload, ensure_ascii=False),
        source="api",
        is_sensitive=0,
        env=env,
        loaded_at=now,
        created_at=now,
    )

    try:
        db.add(snapshot)
        AuditService.log(
            db=db,
            actor=operator,
            action=f"set_mode:{mode}",
            target="system_mode",
            target_type="system",
            reason=reason,
            result="success",
            trace_id=trace_id,
            auto_commit=False,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return payload
