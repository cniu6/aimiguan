"""Step 3 防御链路最小验证：HFish 入站解析、去重与审计"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from importlib import import_module

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

backend_main = import_module("main")
backend_db = import_module("core.database")
defense_module = import_module("api.defense")
app = backend_main.app
Base = backend_db.Base
get_db = backend_db.get_db

TEST_DATABASE_URL = "sqlite:///./test_step3.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    app.dependency_overrides[get_db] = override_get_db

    db = TestingSessionLocal()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    db.execute(
        text(
            """
            INSERT INTO user (username, password_hash, email, enabled, created_at, updated_at)
            VALUES ('admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'admin@test.com', 1, :now, :now)
            """
        ),
        {"now": now},
    )
    db.execute(
        text(
            """
            INSERT INTO role (name, description, created_at, updated_at)
            VALUES ('admin', '管理员', :now, :now)
            """
        ),
        {"now": now},
    )
    db.execute(
        text(
            """
            INSERT INTO role (name, description, created_at, updated_at)
            VALUES ('viewer', '只读用户', :now, :now)
            """
        ),
        {"now": now},
    )
    db.execute(
        text(
            """
            INSERT INTO user_role (user_id, role_id, granted_by, created_at, updated_at)
            VALUES (1, 1, 'system', :now, :now)
            """
        ),
        {"now": now},
    )
    db.execute(
        text(
            """
            INSERT INTO user (username, password_hash, email, enabled, created_at, updated_at)
            VALUES ('viewer', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'viewer@test.com', 1, :now, :now)
            """
        ),
        {"now": now},
    )
    db.execute(
        text(
            """
            INSERT INTO user_role (user_id, role_id, granted_by, created_at, updated_at)
            VALUES (2, 2, 'system', :now, :now)
            """
        ),
        {"now": now},
    )
    db.execute(
        text(
            """
            INSERT INTO permission (name, resource, action, description, created_at)
            VALUES
              ('view_events', 'defense', 'read', '查看威胁事件', :now),
              ('approve_event', 'defense', 'approve', '审批威胁事件', :now),
              ('reject_event', 'defense', 'reject', '驳回威胁事件', :now)
            """
        ),
        {"now": now},
    )
    db.execute(
        text(
            """
            INSERT INTO role_permission (role_id, permission_id, created_at)
            VALUES (1, 1, :now), (1, 2, :now), (1, 3, :now)
            """
        ),
        {"now": now},
    )
    db.commit()
    db.close()

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_hfish_response_code_validation():
    payload = {
        "response_code": 500,
        "response_message": "upstream failed",
        "list_infos": [],
        "attack_infos": [],
        "attack_trend": [],
    }
    response = client.post("/alerts", json=payload)
    assert response.status_code == 50201
    body = response.json()
    assert body["code"] == 50201
    assert body["message"]["error"] == "upstream_response_invalid"
    assert body["message"]["response_code"] == 500


def get_token(username: str = "admin", password: str = "admin123") -> str:
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    return data["access_token"]


def test_hfish_ingest_normalize_and_dedupe():
    payload = {
        "response_code": 0,
        "response_message": "ok",
        "list_infos": [
            {
                "client_id": "source-1",
                "client_ip": "10.0.0.8",
                "service_name": "ssh-honeypot",
                "service_type": "ssh",
                "attack_ip": "1.2.3.4",
                "attack_count": 3,
                "last_attack_time": "2026-02-25 10:00:00",
                "labels": "bruteforce",
                "labels_cn": "暴力破解",
                "is_white": 0,
                "intranet": 1,
            }
        ],
        "attack_infos": [
            {
                "info_id": "detail-1",
                "attack_ip": "5.6.7.8",
                "attack_port": 445,
                "attack_time": "2026-02-25T10:05:00Z",
                "victim_ip": "10.0.0.9",
                "attack_rule": ["smb-probe"],
                "info": {
                    "url": "/login",
                    "method": "POST",
                    "status_code": 401,
                    "user_agent": "scanner",
                },
                "session": "sess-1",
            }
        ],
        "attack_trend": [
            {"attack_time": "2026-02-25 10:00:00", "attack_count": 5},
            {"attack_time": "2026-02-25 10:05:00", "attack_count": 9},
        ],
    }

    first = client.post("/alerts", json=payload)
    assert first.status_code == 200
    body = first.json()
    assert body["code"] == 0
    assert len(body["data"]["event_ids"]) == 2
    assert len(body["data"]["trend_points"]) == 2

    second = client.post("/alerts", json=payload)
    assert second.status_code == 200
    body2 = second.json()
    assert body2["code"] == 0
    assert body2["data"]["event_ids"] == []
    assert len(body2["data"]["deduped_event_ids"]) >= 2

    db = TestingSessionLocal()
    try:
        count = db.execute(text("SELECT COUNT(*) FROM threat_event")).scalar() or 0
        assert count == 2

        src = db.execute(
            text(
                """
                SELECT source_vendor, source_type, source_event_id, raw_payload, extra_json
                FROM threat_event
                WHERE source_event_id = 'source-1'
                LIMIT 1
                """
            )
        ).fetchone()
        assert src is not None
        assert src[0] == "hfish"
        assert src[1] == "attack_source"
        assert src[2] == "source-1"
        assert src[3]
        assert src[4]

        extra = json.loads(src[4])
        assert "normalized_attack_time" in extra
        assert str(extra["normalized_attack_time"]).endswith("Z")

        audit_ok = (
            db.execute(
                text(
                    """
                SELECT COUNT(*)
                FROM audit_log
                WHERE action = 'hfish_ingest' AND result = 'success'
                """
                )
            ).scalar()
            or 0
        )
        assert audit_ok >= 2
    finally:
        db.close()


def test_hfish_ai_scoring_success(monkeypatch):
    async def fake_assess_threat(
        ip: str, attack_type: str, attack_count: int, history=None
    ):
        return {
            "score": 93,
            "reason": f"AI score for {ip}",
            "action_suggest": "BLOCK",
        }

    monkeypatch.setattr(defense_module.ai_engine, "assess_threat", fake_assess_threat)

    payload = {
        "response_code": 0,
        "list_infos": [
            {
                "client_id": "source-ai-ok",
                "service_name": "ssh-honeypot",
                "service_type": "ssh",
                "attack_ip": "2.2.2.2",
                "attack_count": 2,
                "labels": "ssh-brute",
            }
        ],
        "attack_infos": [],
        "attack_trend": [],
    }

    response = client.post("/alerts", json=payload)
    assert response.status_code == 200
    assert response.json()["code"] == 0

    db = TestingSessionLocal()
    try:
        row = db.execute(
            text(
                """
                SELECT ai_score, ai_reason, action_suggest, extra_json
                FROM threat_event
                WHERE source_event_id = 'source-ai-ok'
                LIMIT 1
                """
            )
        ).fetchone()
        assert row is not None
        assert row[0] == 93
        assert row[1] == "AI score for 2.2.2.2"
        assert row[2] == "BLOCK"

        extra = json.loads(row[3])
        ai_meta = extra.get("ai_assessment", {})
        assert ai_meta.get("degraded") is False
        assert ai_meta.get("provider") == "ai_engine"
    finally:
        db.close()


def test_hfish_ai_scoring_degraded_marker(monkeypatch):
    async def fake_assess_threat_fail(
        ip: str, attack_type: str, attack_count: int, history=None
    ):
        raise RuntimeError("llm timeout")

    monkeypatch.setattr(
        defense_module.ai_engine, "assess_threat", fake_assess_threat_fail
    )

    payload = {
        "response_code": 0,
        "list_infos": [
            {
                "client_id": "source-ai-degraded",
                "service_name": "ssh-honeypot",
                "service_type": "ssh",
                "attack_ip": "3.3.3.3",
                "attack_count": 2,
                "labels": "ssh-brute",
            }
        ],
        "attack_infos": [],
        "attack_trend": [],
    }

    response = client.post("/alerts", json=payload)
    assert response.status_code == 200
    assert response.json()["code"] == 0

    db = TestingSessionLocal()
    try:
        row = db.execute(
            text(
                """
                SELECT ai_score, ai_reason, action_suggest, extra_json
                FROM threat_event
                WHERE source_event_id = 'source-ai-degraded'
                LIMIT 1
                """
            )
        ).fetchone()
        assert row is not None
        assert row[0] == 70
        assert "规则评估" in (row[1] or "")
        assert row[2] == "MONITOR"

        extra = json.loads(row[3])
        ai_meta = extra.get("ai_assessment", {})
        assert ai_meta.get("degraded") is True
        assert ai_meta.get("fallback") == "rule_engine"
        assert "llm timeout" in str(ai_meta.get("degrade_reason", ""))
    finally:
        db.close()


def test_approve_event_block_retry_to_manual_required(monkeypatch):
    async def fake_assess_threat(
        ip: str, attack_type: str, attack_count: int, history=None
    ):
        return {"score": 92, "reason": "AI high", "action_suggest": "BLOCK"}

    async def fake_block_ip(ip: str, device_id=None):
        return {"success": False, "error": "switch timeout"}

    async def fast_sleep(seconds: float):
        return None

    monkeypatch.setattr(defense_module.ai_engine, "assess_threat", fake_assess_threat)
    monkeypatch.setattr(defense_module.mcp_client, "block_ip", fake_block_ip)
    monkeypatch.setattr(defense_module, "_sleep_for_retry", fast_sleep)

    ingest_payload = {
        "response_code": 0,
        "list_infos": [
            {
                "client_id": "source-approve-manual",
                "service_name": "ssh-honeypot",
                "service_type": "ssh",
                "attack_ip": "7.7.7.7",
                "attack_count": 5,
                "labels": "bruteforce",
            }
        ],
        "attack_infos": [],
        "attack_trend": [],
    }

    ingest = client.post("/alerts", json=ingest_payload)
    assert ingest.status_code == 200
    event_id = ingest.json()["data"]["event_id"]
    assert event_id is not None

    token = get_token()
    approve = client.post(
        f"/events/{event_id}/approve",
        json={"reason": "go"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert approve.status_code == 200
    body = approve.json()
    assert body["code"] == 0
    assert body["data"]["task_state"] in {"QUEUED", "RUNNING", "FAILED", "RETRYING"}

    db = TestingSessionLocal()
    try:
        task_row = None
        for _ in range(30):
            task_row = db.execute(
                text(
                    """
                    SELECT state, retry_count, error_message, ended_at
                    FROM execution_task
                    WHERE event_id = :event_id
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ),
                {"event_id": int(event_id)},
            ).fetchone()
            if task_row is not None and task_row[0] == "MANUAL_REQUIRED":
                break
            time.sleep(0.05)

        assert task_row is not None
        assert task_row[0] == "MANUAL_REQUIRED"
        assert task_row[1] == 3
        assert "switch timeout" in (task_row[2] or "")
        assert task_row[3] is not None

        event_row = db.execute(
            text("SELECT status FROM threat_event WHERE id = :event_id"),
            {"event_id": int(event_id)},
        ).fetchone()
        assert event_row is not None
        assert event_row[0] == "FAILED"
    finally:
        db.close()


def test_pending_events_filter_pagination_and_sorting():
    token = get_token()
    payload = {
        "response_code": 0,
        "response_message": "ok",
        "list_infos": [
            {
                "client_id": "pending-source-low",
                "client_ip": "10.0.1.10",
                "service_name": "pending-filter-service",
                "service_type": "ssh",
                "attack_ip": "11.11.11.11",
                "attack_count": 1,
                "last_attack_time": "2026-02-26 08:00:00",
                "labels": "probe",
                "labels_cn": "探测",
                "is_white": 0,
                "intranet": 0,
            },
            {
                "client_id": "pending-source-high",
                "client_ip": "10.0.1.11",
                "service_name": "pending-filter-service",
                "service_type": "ssh",
                "attack_ip": "22.22.22.22",
                "attack_count": 4,
                "last_attack_time": "2026-02-26 08:10:00",
                "labels": "bruteforce",
                "labels_cn": "暴力破解",
                "is_white": 0,
                "intranet": 0,
            },
        ],
        "attack_infos": [],
        "attack_trend": [],
    }

    ingest_resp = client.post("/alerts", json=payload)
    assert ingest_resp.status_code == 200
    assert ingest_resp.json()["code"] == 0

    high_filter_resp = client.get(
        "/api/v1/defense/pending",
        params={
            "status": "PENDING",
            "source": "pending-filter-service",
            "min_score": 80,
            "start_time": "2026-02-26T08:05:00Z",
            "end_time": "2026-02-26T08:20:00Z",
            "page": 1,
            "page_size": 10,
            "sort_by": "ai_score",
            "sort_order": "desc",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert high_filter_resp.status_code == 200
    high_body = high_filter_resp.json()
    assert high_body["code"] == 0
    assert high_body["message"] == "Pending events fetched"

    high_data = high_body["data"]
    assert high_data["total"] == 1
    assert high_data["page"] == 1
    assert high_data["page_size"] == 10
    assert high_data["total_pages"] == 1
    assert len(high_data["items"]) == 1
    assert high_data["items"][0]["ip"] == "22.22.22.22"
    assert high_data["items"][0]["ai_score"] == 90

    medium_filter_resp = client.get(
        "/api/v1/defense/pending",
        params={
            "status": "PENDING",
            "source": "pending-filter-service",
            "risk_level": "MEDIUM",
            "sort_by": "created_at",
            "sort_order": "asc",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert medium_filter_resp.status_code == 200
    medium_body = medium_filter_resp.json()
    assert medium_body["code"] == 0
    medium_items = medium_body["data"]["items"]
    assert len(medium_items) == 1
    assert medium_items[0]["ip"] == "11.11.11.11"
    assert medium_items[0]["ai_score"] == 60


def test_pending_events_invalid_query_validation():
    token = get_token()
    bad_resp = client.get(
        "/api/v1/defense/pending",
        params={
            "sort_by": "unknown_field",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bad_resp.status_code == 40000
    body = bad_resp.json()
    assert body["code"] == 40000
    assert "sort_by" in str(body["message"])


def test_approve_event_permission_denied_for_viewer(monkeypatch):
    async def fake_assess_threat(
        ip: str, attack_type: str, attack_count: int, history=None
    ):
        return {"score": 90, "reason": "AI high", "action_suggest": "BLOCK"}

    async def fake_block_ip(ip: str, device_id=None):
        return {"success": True}

    monkeypatch.setattr(defense_module.ai_engine, "assess_threat", fake_assess_threat)
    monkeypatch.setattr(defense_module.mcp_client, "block_ip", fake_block_ip)

    ingest_payload = {
        "response_code": 0,
        "list_infos": [
            {
                "client_id": "source-viewer-deny",
                "service_name": "ssh-honeypot",
                "service_type": "ssh",
                "attack_ip": "8.8.8.8",
                "attack_count": 5,
                "labels": "bruteforce",
            }
        ],
        "attack_infos": [],
        "attack_trend": [],
    }
    ingest = client.post("/alerts", json=ingest_payload)
    assert ingest.status_code == 200
    event_id = ingest.json()["data"]["event_id"]
    assert event_id is not None

    viewer_token = get_token(username="viewer", password="admin123")
    approve = client.post(
        f"/events/{event_id}/approve",
        json={"reason": "viewer try"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert approve.status_code == 40301
    body = approve.json()
    assert body["code"] == 40301
    assert body["message"]["error"] == "permission_denied"
    assert body["message"]["required_permission"] == "approve_event"
