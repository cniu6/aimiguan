import time
from copy import deepcopy
from uuid import uuid4

from api import defense as defense_module
from core.database import AuditLog, ExecutionTask, WorkflowRun
from services.metrics_service import metrics
from services.workflow_dsl import load_default_defense_workflow
from services.workflow_rollout import (
    get_defense_workflow_rollout,
    set_defense_workflow_rollout,
    should_route_to_workflow_runtime,
)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_published_defense_workflow(client, admin_token) -> str:
    suffix = uuid4().hex[:8]
    workflow_key = f"defense-rollout-{suffix}"
    dsl = deepcopy(load_default_defense_workflow())
    dsl["workflow_id"] = workflow_key
    dsl["name"] = f"Defense Rollout {suffix}"
    dsl["version"] = 1
    payload = {
        "workflow_key": workflow_key,
        "name": dsl["name"],
        "description": "defense rollout integration test",
        "dsl": dsl,
        "change_note": "initial draft",
    }
    headers = _auth(admin_token)
    create_resp = client.post("/api/v1/workflows", json=payload, headers=headers)
    assert create_resp.status_code == 200
    workflow_id = create_resp.json()["data"]["id"]
    publish_resp = client.post(
        f"/api/v1/workflows/{workflow_id}/publish",
        json={
            "version_tag": 1,
            "canary_percent": 100,
            "approval_reason": "publish defense rollout",
            "approval_passed": True,
            "confirmation_text": workflow_key,
        },
        headers=headers,
    )
    assert publish_resp.status_code == 200
    return workflow_key


def _wait_task(test_db, event_id: int, timeout_seconds: float = 3.0):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        test_db.expire_all()
        row = (
            test_db.query(ExecutionTask)
            .filter(ExecutionTask.event_id == event_id)
            .order_by(ExecutionTask.id.desc())
            .first()
        )
        if row is not None and row.state in {"SUCCESS", "MANUAL_REQUIRED", "FAILED"}:
            return row
        time.sleep(0.05)
    test_db.expire_all()
    return (
        test_db.query(ExecutionTask)
        .filter(ExecutionTask.event_id == event_id)
        .order_by(ExecutionTask.id.desc())
        .first()
    )


def _create_event_and_approve(client, admin_token, client_id: str) -> int:
    ingest_resp = client.post(
        "/alerts",
        json={
            "response_code": 0,
            "list_infos": [
                {
                    "client_id": client_id,
                    "service_name": "ssh-honeypot",
                    "service_type": "ssh",
                    "attack_ip": "11.11.11.11",
                    "attack_count": 6,
                    "labels": "bruteforce",
                }
            ],
            "attack_infos": [],
            "attack_trend": [],
        },
    )
    assert ingest_resp.status_code == 200
    event_id = int(ingest_resp.json()["data"]["event_id"])
    approve_resp = client.post(
        f"/events/{event_id}/approve",
        json={"reason": "rollout approve"},
        headers=_auth(admin_token),
    )
    assert approve_resp.status_code == 200
    return event_id


def test_rollout_service_persists_and_gray_routes(test_db):
    payload = set_defense_workflow_rollout(
        test_db,
        mode="workflow_gray",
        gray_percent=50,
        double_write_metrics=True,
        reason="gray test",
        operator="tester",
        env="dev",
        trace_id="trace-gray",
    )
    assert payload["mode"] == "workflow_gray"
    assert payload["gray_percent"] == 50
    assert payload["double_write_metrics"] is True

    current = get_defense_workflow_rollout(test_db, "dev")
    assert current["mode"] == "workflow_gray"
    assert current["gray_percent"] == 50
    assert current["double_write_metrics"] is True

    assert should_route_to_workflow_runtime(rollout={"mode": "legacy_only", "gray_percent": 100}, routing_key="a") is False
    assert should_route_to_workflow_runtime(rollout={"mode": "workflow_full", "gray_percent": 0}, routing_key="a") is True
    assert should_route_to_workflow_runtime(rollout={"mode": "workflow_gray", "gray_percent": 0}, routing_key="a") is False
    assert should_route_to_workflow_runtime(rollout={"mode": "workflow_gray", "gray_percent": 100}, routing_key="a") is True

    decisions = {
        should_route_to_workflow_runtime(
            rollout={"mode": "workflow_gray", "gray_percent": 50},
            routing_key=f"route-{index}",
        )
        for index in range(32)
    }
    assert decisions == {False, True}


def test_rollout_full_then_rollback_to_legacy(monkeypatch, client, admin_token, test_db):
    workflow_key = _create_published_defense_workflow(client, admin_token)
    monkeypatch.setattr(defense_module, "_get_defense_runtime_workflow_key", lambda: workflow_key)

    async def fake_assess_threat(ip: str, attack_type: str, attack_count: int, history=None, trace_id=None):
        return {
            "score": 95,
            "reason": "rollout runtime high risk",
            "action_suggest": "BLOCK",
            "trace_id": trace_id,
        }

    async def fake_block_ip(ip: str, device_id=None, operator: str = "system"):
        return {"success": True, "result": {"ip": ip, "device_id": device_id, "operator": operator}}

    monkeypatch.setattr(defense_module.ai_engine, "assess_threat", fake_assess_threat)
    monkeypatch.setattr(defense_module.mcp_client, "block_ip", fake_block_ip)

    full_resp = client.post(
        "/api/v1/defense/workflow-rollout",
        json={
            "mode": "workflow_full",
            "gray_percent": 100,
            "double_write_metrics": True,
            "reason": "full takeover",
        },
        headers=_auth(admin_token),
    )
    assert full_resp.status_code == 200
    assert full_resp.json()["data"]["mode"] == "workflow_full"

    workflow_counter_before = metrics.get_counter("defense_workflow_route_total")
    event_id_1 = _create_event_and_approve(client, admin_token, f"rollout-full-{uuid4().hex[:8]}")
    task_1 = _wait_task(test_db, event_id_1)
    assert task_1 is not None
    assert task_1.state == "SUCCESS"

    runtime_run = (
        test_db.query(WorkflowRun)
        .filter(WorkflowRun.trigger_ref == f"execution_task:{task_1.id}")
        .order_by(WorkflowRun.id.desc())
        .first()
    )
    assert runtime_run is not None
    assert runtime_run.run_state == "SUCCESS"
    assert metrics.get_counter("defense_workflow_route_total") >= workflow_counter_before + 1

    rollout_audit = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == "defense_workflow_route", AuditLog.target == f"execution_task:{task_1.id}")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert rollout_audit is not None

    rollback_resp = client.post(
        "/api/v1/defense/workflow-rollout",
        json={
            "mode": "legacy_only",
            "gray_percent": 0,
            "double_write_metrics": True,
            "reason": "rollback to legacy",
        },
        headers=_auth(admin_token),
    )
    assert rollback_resp.status_code == 200
    assert rollback_resp.json()["data"]["mode"] == "legacy_only"

    legacy_counter_before = metrics.get_counter("defense_legacy_route_total")
    event_id_2 = _create_event_and_approve(client, admin_token, f"rollout-legacy-{uuid4().hex[:8]}")
    task_2 = _wait_task(test_db, event_id_2)
    assert task_2 is not None
    assert task_2.state == "SUCCESS"
    assert metrics.get_counter("defense_legacy_route_total") >= legacy_counter_before + 1

    legacy_runtime_run = (
        test_db.query(WorkflowRun)
        .filter(WorkflowRun.trigger_ref == f"execution_task:{task_2.id}")
        .order_by(WorkflowRun.id.desc())
        .first()
    )
    assert legacy_runtime_run is None

    get_resp = client.get(
        "/api/v1/defense/workflow-rollout",
        headers=_auth(admin_token),
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["mode"] == "legacy_only"
