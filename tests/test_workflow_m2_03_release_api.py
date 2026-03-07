from copy import deepcopy
from uuid import uuid4

from core.database import AuditLog, WorkflowDefinition, WorkflowVersion
from services.workflow_dsl import load_default_defense_workflow
from services.workflow_release import get_publish_lock


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_payload() -> dict:
    suffix = uuid4().hex[:8]
    workflow_key = f"wf-m2-03-{suffix}"
    dsl = deepcopy(load_default_defense_workflow())
    dsl["workflow_id"] = workflow_key
    dsl["name"] = f"Workflow {suffix}"
    dsl["version"] = 1
    dsl["status"] = "DRAFT"
    return {
        "workflow_key": workflow_key,
        "name": dsl["name"],
        "description": "workflow release api test",
        "dsl": dsl,
        "change_note": "initial draft",
    }


def test_workflow_publish_and_rollback_flow(client, admin_token, test_db):
    headers = _auth(admin_token)
    payload = _create_payload()

    create_resp = client.post("/api/v1/workflows", json=payload, headers=headers)
    assert create_resp.status_code == 200
    workflow_id = create_resp.json()["data"]["id"]

    publish_v1 = client.post(
        f"/api/v1/workflows/{workflow_id}/publish",
        json={
            "version_tag": 1,
            "canary_percent": 10,
            "effective_at": "2026-03-07T12:00:00Z",
            "approval_reason": "首次灰度发布",
            "trace_id": "trace-m2-03-publish-v1",
        },
        headers=headers,
    )
    assert publish_v1.status_code == 200
    publish_v1_body = publish_v1.json()
    assert publish_v1_body["code"] == 0
    assert publish_v1_body["data"]["published_version"] == 1
    assert publish_v1_body["data"]["canary_percent"] == 10
    assert publish_v1_body["data"]["definition_state"] == "PUBLISHED"

    detail_v1 = client.get(f"/api/v1/workflows/{workflow_id}", headers=headers)
    assert detail_v1.status_code == 200
    detail_v1_body = detail_v1.json()
    assert detail_v1_body["data"]["workflow"]["definition_state"] == "PUBLISHED"
    assert detail_v1_body["data"]["workflow"]["published_version"] == 1
    assert detail_v1_body["data"]["dsl"]["metadata"]["release"]["canary_percent"] == 10
    assert detail_v1_body["data"]["dsl"]["metadata"]["release"]["approval_reason"] == "首次灰度发布"

    update_dsl = deepcopy(detail_v1_body["data"]["dsl"])
    update_dsl["description"] = "version 2"
    update_dsl["metadata"].pop("release", None)
    update_resp = client.put(
        f"/api/v1/workflows/{workflow_id}",
        json={
            "version_tag": 1,
            "name": "Workflow Updated v2",
            "description": "version 2",
            "dsl": update_dsl,
            "change_note": "prepare v2",
        },
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["version_tag"] == 2

    publish_v2 = client.post(
        f"/api/v1/workflows/{workflow_id}/publish",
        json={
            "version_tag": 2,
            "canary_percent": 50,
            "approval_reason": "扩大灰度",
            "trace_id": "trace-m2-03-publish-v2",
        },
        headers=headers,
    )
    assert publish_v2.status_code == 200
    assert publish_v2.json()["data"]["published_version"] == 2
    assert publish_v2.json()["data"]["previous_published_version"] == 1

    rollback_resp = client.post(
        f"/api/v1/workflows/{workflow_id}/rollback",
        json={
            "target_version": 1,
            "reason": "回滚演练",
            "trace_id": "trace-m2-03-rollback-v1",
        },
        headers=headers,
    )
    assert rollback_resp.status_code == 200
    rollback_body = rollback_resp.json()
    assert rollback_body["code"] == 0
    assert rollback_body["data"]["rolled_back_to_version"] == 1
    assert rollback_body["data"]["published_version"] == 1
    assert rollback_body["data"]["previous_published_version"] == 2
    assert rollback_body["data"]["definition_state"] == "PUBLISHED"

    definition = test_db.query(WorkflowDefinition).filter(WorkflowDefinition.id == workflow_id).first()
    assert definition is not None
    assert definition.published_version == 1
    assert definition.definition_state == "PUBLISHED"

    version1 = (
        test_db.query(WorkflowVersion)
        .filter(WorkflowVersion.workflow_id == workflow_id, WorkflowVersion.version == 1)
        .first()
    )
    version2 = (
        test_db.query(WorkflowVersion)
        .filter(WorkflowVersion.workflow_id == workflow_id, WorkflowVersion.version == 2)
        .first()
    )
    assert version1 is not None and version1.definition_state == "PUBLISHED"
    assert version2 is not None and version2.definition_state == "VALIDATED"

    publish_audits = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == "workflow_publish", AuditLog.target.like(f"{payload['workflow_key']}:%"))
        .order_by(AuditLog.id.asc())
        .all()
    )
    rollback_audits = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == "workflow_rollback", AuditLog.target == f"{payload['workflow_key']}:v1")
        .order_by(AuditLog.id.asc())
        .all()
    )
    assert len(publish_audits) == 2
    assert [audit.reason for audit in publish_audits] == ["首次灰度发布", "扩大灰度"]
    assert len(rollback_audits) == 1
    assert rollback_audits[0].reason == "回滚演练"
    assert rollback_audits[0].trace_id == "trace-m2-03-rollback-v1"


def test_workflow_publish_conflict_returns_409(client, admin_token):
    headers = _auth(admin_token)
    payload = _create_payload()

    create_resp = client.post("/api/v1/workflows", json=payload, headers=headers)
    assert create_resp.status_code == 200
    workflow_id = create_resp.json()["data"]["id"]

    lock = get_publish_lock(workflow_id)
    acquired = lock.acquire(blocking=False)
    assert acquired is True
    try:
        response = client.post(
            f"/api/v1/workflows/{workflow_id}/publish",
            json={
                "version_tag": 1,
                "canary_percent": 10,
                "approval_reason": "模拟并发冲突",
            },
            headers=headers,
        )
    finally:
        lock.release()

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == 40941
    assert body["message"] == "workflow publish already in progress"
