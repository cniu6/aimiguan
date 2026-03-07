import asyncio
from uuid import uuid4

from services import workflow_runtime as workflow_runtime_module
from services.workflow_runtime import run_published_workflow


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _replay_workflow_dsl(workflow_key: str) -> dict:
    return {
        "schema_version": "1.0.0",
        "workflow_id": workflow_key,
        "version": 1,
        "name": f"Replay Workflow {workflow_key}",
        "description": "workflow replay debug test",
        "status": "DRAFT",
        "context": {
            "inputs": {},
            "outputs": {},
            "trace_id": "{{ trace_id }}",
        },
        "runtime": {
            "initial_state": "QUEUED",
            "terminal_states": ["SUCCESS", "FAILED", "MANUAL_REQUIRED", "CANCELLED"],
            "state_enum": ["QUEUED", "RUNNING", "RETRYING", "SUCCESS", "FAILED", "MANUAL_REQUIRED", "CANCELLED"],
        },
        "nodes": [
            {
                "id": "trigger_node",
                "type": "trigger",
                "name": "Trigger",
                "config": {"source_type": "replay-test"},
                "timeout": 10,
                "retry_policy": {"max_retries": 0, "backoff_seconds": 1, "backoff_multiplier": 1.0, "retry_on": []},
            },
            {
                "id": "audit_log",
                "type": "audit",
                "name": "Audit",
                "config": {"service": "audit_service.log"},
                "timeout": 10,
                "retry_policy": {"max_retries": 0, "backoff_seconds": 1, "backoff_multiplier": 1.0, "retry_on": []},
            },
            {
                "id": "block_action",
                "type": "mcp_action",
                "name": "Block IP",
                "config": {"service": "mcp_client.block_ip", "device_id": 1},
                "timeout": 10,
                "retry_policy": {"max_retries": 0, "backoff_seconds": 1, "backoff_multiplier": 1.0, "retry_on": []},
            },
        ],
        "edges": [
            {"from": "trigger_node", "to": "audit_log", "condition": "true", "priority": 100},
            {"from": "audit_log", "to": "block_action", "condition": "true", "priority": 100},
        ],
        "metadata": {"owner": "secops"},
    }


def _publish_workflow(client, admin_token) -> str:
    workflow_key = f"replay-{uuid4().hex[:8]}"
    payload = {
        "workflow_key": workflow_key,
        "name": f"Replay {workflow_key}",
        "description": "workflow replay debug test",
        "dsl": _replay_workflow_dsl(workflow_key),
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
            "approval_reason": "publish replay workflow",
            "approval_passed": True,
            "confirmation_text": workflow_key,
        },
        headers=headers,
    )
    assert publish_resp.status_code == 200
    return workflow_key


def test_workflow_replay_and_resume_debug(monkeypatch, client, admin_token, test_db):
    workflow_key = _publish_workflow(client, admin_token)

    async def fake_block_ip(ip: str, device_id=None, operator=None):
        return {"success": True, "ip": ip, "device_id": device_id, "operator": operator}

    monkeypatch.setattr(workflow_runtime_module.mcp_client, "block_ip", fake_block_ip)

    failed_result = asyncio.run(
        run_published_workflow(
            test_db,
            workflow_key=workflow_key,
            input_payload={},
            trigger_source="replay_test",
            trigger_ref=f"failed-{uuid4().hex[:6]}",
            actor="tester",
        )
    )
    assert failed_result.run_state == "FAILED"

    headers = _auth(admin_token)
    debug_resp = client.get(f"/api/v1/workflows/runs/{failed_result.run_id}/debug-report", headers=headers)
    assert debug_resp.status_code == 200
    debug_data = debug_resp.json()["data"]
    assert debug_data["source_run"]["run_id"] == failed_result.run_id
    assert debug_data["resume_candidate"]["node_id"] == "block_action"
    assert any("ip" in item.lower() for item in debug_data["recommendations"])

    full_replay_resp = client.post(
        f"/api/v1/workflows/runs/{failed_result.run_id}/replay",
        json={"mode": "full", "overrides": {"ip": "8.8.8.8"}},
        headers=headers,
    )
    assert full_replay_resp.status_code == 200
    full_replay_data = full_replay_resp.json()["data"]
    assert full_replay_data["mode"] == "full"
    assert full_replay_data["replay_run_state"] == "SUCCESS"
    assert full_replay_data["resumed_from_node_id"] is None

    full_detail_resp = client.get(f"/api/v1/workflows/runs/{full_replay_data['replay_run_id']}", headers=headers)
    assert full_detail_resp.status_code == 200
    full_steps = full_detail_resp.json()["data"]["steps"]
    assert [step["node_id"] for step in full_steps] == ["trigger_node", "audit_log", "block_action"]

    resume_resp = client.post(
        f"/api/v1/workflows/runs/{failed_result.run_id}/replay",
        json={"mode": "resume_from_failure", "overrides": {"ip": "1.1.1.1"}},
        headers=headers,
    )
    assert resume_resp.status_code == 200
    resume_data = resume_resp.json()["data"]
    assert resume_data["mode"] == "resume_from_failure"
    assert resume_data["resumed_from_node_id"] == "block_action"
    assert resume_data["replay_run_state"] == "SUCCESS"
    assert resume_data["debug_report"]["resume_candidate"]["node_id"] == "block_action"

    resume_detail_resp = client.get(f"/api/v1/workflows/runs/{resume_data['replay_run_id']}", headers=headers)
    assert resume_detail_resp.status_code == 200
    resume_steps = resume_detail_resp.json()["data"]["steps"]
    assert [step["node_id"] for step in resume_steps] == ["block_action"]
