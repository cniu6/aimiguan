from __future__ import annotations

import json
from datetime import datetime, timezone
from threading import Lock
from typing import Any

_LOCK_GUARD = Lock()
_LOCKS: dict[int, Lock] = {}


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def get_publish_lock(workflow_id: int) -> Lock:
    with _LOCK_GUARD:
        lock = _LOCKS.get(workflow_id)
        if lock is None:
            lock = Lock()
            _LOCKS[workflow_id] = lock
        return lock


def apply_release_metadata(
    dsl_payload: dict[str, Any],
    *,
    canary_percent: int,
    effective_at: datetime | None,
    approval_reason: str,
    actor: str,
    trace_id: str | None,
) -> dict[str, Any]:
    payload = json.loads(json.dumps(dsl_payload, ensure_ascii=False))
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    metadata["release"] = {
        "canary_percent": canary_percent,
        "effective_at": _iso(effective_at),
        "approval_reason": approval_reason,
        "published_by": actor,
        "published_at": _iso(datetime.now(timezone.utc)),
        "trace_id": trace_id,
    }
    payload["metadata"] = metadata
    return payload
