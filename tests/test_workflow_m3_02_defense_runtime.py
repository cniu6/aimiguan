import time
from copy import deepcopy
from uuid import uuid4

from api import defense as defense_module
from core.database import ExecutionTask, ThreatEvent, WorkflowRun, WorkflowStepRun
from services import workflow_runtime as workflow_runtime_module
from services.workflow_dsl import load_default_defense_workflow
from services.workflow_rollout import set_defense_workflow_rollout


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_published_defense_workflow(client, admin_token) -> str:
    suffix = uuid4().hex[:8]
    workflow_key = f"defense-runtime-{suffix}"
    dsl = deepcopy(load_default_defense_workflow())
    dsl["workflow_id"] = workflow_key
    dsl["name"] = f"Defense Runtime {suffix}"
    dsl["version"] = 1
    payload = {
        "workflow_key": workflow_key,
        "name": dsl["name"],
        "description": "defense runtime integration test",
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
            "approval_reason": "publish defense runtime",
            "approval_passed": True,
            "confirmation_text": workflow_key,
        },
        headers=headers,
    )
    assert publish_resp.status_code == 200
    return workflow_key


def _wait_task_state(test_db, event_id: int, expected: set[str], timeout_seconds: float = 3.0):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        test_db.expire_all()
        task = (
            test_db.query(ExecutionTask)
            .filter(ExecutionTask.event_id == event_id)
            .order_by(ExecutionTask.id.desc())
            .first()
        )
        if task is not None and task.state in expected:
            return task
        time.sleep(0.05)
    test_db.expire_all()
    return (
        test_db.query(ExecutionTask)
        .filter(ExecutionTask.event_id == event_id)
        .order_by(ExecutionTask.id.desc())
        .first()
    )


def test_approve_event_uses_runtime_and_finishes_success(monkeypatch, client, admin_token, test_db):
    workflow_key = _create_published_defense_workflow(client, admin_token)
    monkeypatch.setattr(defense_module, "_get_defense_runtime_workflow_key", lambda: workflow_key)
    set_defense_workflow_rollout(
        test_db,
        mode="workflow_full",
        gray_percent=100,
        double_write_metrics=False,
        reason="m3-02 runtime test",
        operator="tester",
        env="dev",
        trace_id="trace-m3-02-success",
    )

    async def fake_assess_threat(ip: str, attack_type: str, attack_count: int, history=None, trace_id=None):
        return {
            "score": 96,
            "reason": "runtime high risk",
            "action_suggest": "BLOCK",
            "trace_id": trace_id,
        }

    async def fake_block_ip(ip: str, device_id=None, operator: str = "system"):
        return {"success": True, "result": {"ip": ip, "device_id": device_id, "operator": operator}}

    monkeypatch.setattr(defense_module.ai_engine, "assess_threat", fake_assess_threat)
    monkeypatch.setattr(workflow_runtime_module.ai_engine, "assess_threat", fake_assess_threat)
    monkeypatch.setattr(defense_module.mcp_client, "block_ip", fake_block_ip)
    monkeypatch.setattr(workflow_runtime_module.mcp_client, "block_ip", fake_block_ip)

    ingest_resp = client.post(
        "/alerts",
        json={
            "response_code": 0,
            "list_infos": [
                {
                    "client_id": f"runtime-success-{uuid4().hex[:8]}",
                    "service_name": "ssh-honeypot",
                    "service_type": "ssh",
                    "attack_ip": "9.9.9.9",
                    "attack_count": 6,
                    "labels": "bruteforce",
                }
            ],
            "attack_infos": [],
            "attack_trend": [],
        },
    )
    assert ingest_resp.status_code == 200
    event_id = ingest_resp.json()["data"]["event_id"]

    approve_resp = client.post(
        f"/events/{event_id}/approve",
        json={"reason": "runtime approve"},
        headers=_auth(admin_token),
    )
    assert approve_resp.status_code == 200
    task_id = approve_resp.json()["data"]["task_id"]

    task = _wait_task_state(test_db, int(event_id), {"SUCCESS", "MANUAL_REQUIRED", "FAILED"})
    assert task is not None
    assert task.id == task_id
    assert task.state == "SUCCESS"
    assert task.retry_count == 0
    assert task.error_message in (None, "")

    event = test_db.query(ThreatEvent).filter(ThreatEvent.id == int(event_id)).first()
    assert event is not None
    assert event.status == "DONE"

    workflow_run = (
        test_db.query(WorkflowRun)
        .filter(WorkflowRun.trigger_ref == f"execution_task:{task_id}")
        .order_by(WorkflowRun.id.desc())
        .first()
    )
    assert workflow_run is not None
    assert workflow_run.run_state == "SUCCESS"

    steps = (
        test_db.query(WorkflowStepRun)
        .filter(WorkflowStepRun.workflow_run_id == workflow_run.id)
        .order_by(WorkflowStepRun.id.asc())
        .all()
    )
    assert [step.node_id for step in steps] == [
        "trigger_hfish",
        "assess_ai",
        "approval",
        "block_action",
        "audit_log",
    ]
    assert all(step.step_state == "SUCCESS" for step in steps)


def test_approve_event_runtime_failure_maps_to_manual_required(monkeypatch, client, admin_token, test_db):
    workflow_key = _create_published_defense_workflow(client, admin_token)
    monkeypatch.setattr(defense_module, "_get_defense_runtime_workflow_key", lambda: workflow_key)
    set_defense_workflow_rollout(
        test_db,
        mode="workflow_full",
        gray_percent=100,
        double_write_metrics=False,
        reason="m3-02 runtime failure test",
        operator="tester",
        env="dev",
        trace_id="trace-m3-02-failure",
    )

    async def fake_assess_threat(ip: str, attack_type: str, attack_count: int, history=None, trace_id=None):
        return {
            "score": 94,
            "reason": "runtime high risk",
            "action_suggest": "BLOCK",
            "trace_id": trace_id,
        }

    async def fake_block_ip(ip: str, device_id=None, operator: str = "system"):
        return {"success": False, "error": "switch timeout", "retryable": True}

    async def fast_sleep(_seconds: float):
        return None

    monkeypatch.setattr(defense_module.ai_engine, "assess_threat", fake_assess_threat)
    monkeypatch.setattr(workflow_runtime_module.ai_engine, "assess_threat", fake_assess_threat)
    monkeypatch.setattr(defense_module.mcp_client, "block_ip", fake_block_ip)
    monkeypatch.setattr(workflow_runtime_module.mcp_client, "block_ip", fake_block_ip)
    monkeypatch.setattr(workflow_runtime_module.asyncio, "sleep", fast_sleep)

    ingest_resp = client.post(
        "/alerts",
        json={
            "response_code": 0,
            "list_infos": [
                {
                    "client_id": f"runtime-fail-{uuid4().hex[:8]}",
                    "service_name": "ssh-honeypot",
                    "service_type": "ssh",
                    "attack_ip": "10.10.10.10",
                    "attack_count": 7,
                    "labels": "bruteforce",
                }
            ],
            "attack_infos": [],
            "attack_trend": [],
        },
    )
    assert ingest_resp.status_code == 200
    event_id = ingest_resp.json()["data"]["event_id"]

    approve_resp = client.post(
        f"/events/{event_id}/approve",
        json={"reason": "runtime approve fail"},
        headers=_auth(admin_token),
    )
    assert approve_resp.status_code == 200
    task_id = approve_resp.json()["data"]["task_id"]

    task = _wait_task_state(test_db, int(event_id), {"MANUAL_REQUIRED", "SUCCESS", "FAILED"})
    assert task is not None
    assert task.id == task_id
    assert task.state == "MANUAL_REQUIRED"
    assert task.retry_count == 3
    assert "switch timeout" in str(task.error_message or "")

    event = test_db.query(ThreatEvent).filter(ThreatEvent.id == int(event_id)).first()
    assert event is not None
    assert event.status == "FAILED"

    workflow_run = (
        test_db.query(WorkflowRun)
        .filter(WorkflowRun.trigger_ref == f"execution_task:{task_id}")
        .order_by(WorkflowRun.id.desc())
        .first()
    )
    assert workflow_run is not None
    assert workflow_run.run_state == "FAILED"

    block_steps = (
        test_db.query(WorkflowStepRun)
        .filter(
            WorkflowStepRun.workflow_run_id == workflow_run.id,
            WorkflowStepRun.node_id == "block_action",
        )
        .order_by(WorkflowStepRun.attempt.asc())
        .all()
    )
    assert [step.step_state for step in block_steps] == ["RETRYING", "RETRYING", "RETRYING", "FAILED"]
