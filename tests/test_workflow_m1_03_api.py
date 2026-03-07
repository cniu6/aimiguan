from copy import deepcopy
from uuid import uuid4

from services.workflow_dsl import load_default_defense_workflow


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_payload() -> dict:
    suffix = uuid4().hex[:8]
    workflow_key = f"wf-{suffix}"
    dsl = deepcopy(load_default_defense_workflow())
    dsl["workflow_id"] = workflow_key
    dsl["name"] = f"Workflow {suffix}"
    dsl["version"] = 1
    dsl["status"] = "DRAFT"
    return {
        "workflow_key": workflow_key,
        "name": dsl["name"],
        "description": "workflow api contract test",
        "dsl": dsl,
        "change_note": "initial draft",
    }


def test_workflow_api_requires_auth(client):
    resp = client.get("/api/v1/workflows")
    assert resp.status_code == 401


def test_workflow_api_forbidden_for_viewer(client, viewer_token):
    resp = client.get("/api/v1/workflows", headers=_auth(viewer_token))
    assert resp.status_code == 403
    body = resp.json()
    assert body["code"] == 40301


def test_workflow_api_crud_validate_contract(client, admin_token):
    headers = _auth(admin_token)
    payload = _create_payload()

    create_resp = client.post("/api/v1/workflows", json=payload, headers=headers)
    assert create_resp.status_code == 200
    create_body = create_resp.json()
    assert create_body["code"] == 0
    workflow_id = create_body["data"]["id"]
    assert create_body["data"]["workflow_key"] == payload["workflow_key"]
    assert create_body["data"]["latest_version"] == 1
    assert create_body["data"]["version_tag"] == 1

    list_resp = client.get(
        f"/api/v1/workflows?page=1&page_size=10&keyword={payload['workflow_key']}",
        headers=headers,
    )
    assert list_resp.status_code == 200
    list_body = list_resp.json()
    assert list_body["code"] == 0
    assert list_body["data"]["page"] == 1
    assert list_body["data"]["page_size"] == 10
    assert list_body["data"]["total"] >= 1
    assert any(item["id"] == workflow_id for item in list_body["data"]["items"])

    get_resp = client.get(f"/api/v1/workflows/{workflow_id}", headers=headers)
    assert get_resp.status_code == 200
    get_body = get_resp.json()
    assert get_body["code"] == 0
    assert get_body["data"]["workflow"]["id"] == workflow_id
    assert get_body["data"]["dsl"]["workflow_id"] == payload["workflow_key"]
    assert isinstance(get_body["data"]["dsl"]["nodes"], list)
    assert isinstance(get_body["data"]["dsl"]["edges"], list)

    stale_update = deepcopy(get_body["data"]["dsl"])
    stale_update["description"] = "stale update"
    stale_resp = client.put(
        f"/api/v1/workflows/{workflow_id}",
        json={
            "version_tag": 2,
            "name": "stale",
            "description": "should fail",
            "dsl": stale_update,
            "change_note": "stale update",
        },
        headers=headers,
    )
    assert stale_resp.status_code == 409

    next_dsl = deepcopy(get_body["data"]["dsl"])
    next_dsl["description"] = "updated by api test"
    update_resp = client.put(
        f"/api/v1/workflows/{workflow_id}",
        json={
            "version_tag": 1,
            "name": "Workflow Updated",
            "description": "updated description",
            "dsl": next_dsl,
            "change_note": "update draft",
        },
        headers=headers,
    )
    assert update_resp.status_code == 200
    update_body = update_resp.json()
    assert update_body["code"] == 0
    assert update_body["data"]["latest_version"] == 2
    assert update_body["data"]["version_tag"] == 2
    assert update_body["data"]["name"] == "Workflow Updated"

    validate_resp = client.post(f"/api/v1/workflows/{workflow_id}/validate", headers=headers)
    assert validate_resp.status_code == 200
    validate_body = validate_resp.json()
    assert validate_body["code"] == 0
    assert validate_body["data"]["valid"] is True
    assert validate_body["data"]["version"] == 2

    final_resp = client.get(f"/api/v1/workflows/{workflow_id}", headers=headers)
    assert final_resp.status_code == 200
    final_body = final_resp.json()
    assert final_body["data"]["workflow"]["definition_state"] == "VALIDATED"
    assert final_body["data"]["workflow"]["latest_version"] == 2
