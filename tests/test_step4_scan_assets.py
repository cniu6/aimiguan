"""Step 4 资产管理最小验证：模型字段与创建校验"""

import pytest


def get_token(client) -> str:
    """获取测试用的 JWT token"""
    response = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_create_asset_ip_with_default_tag_and_enabled(client):
    token = get_token(client)
    response = client.post(
        "/api/v1/scan/assets",
        json={"target": "192.168.1.10", "target_type": "ip"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["target"] == "192.168.1.10"
    assert body["data"]["target_type"] == "IP"
    assert body["data"]["tags"] == "ip"
    assert body["data"]["enabled"] is True

    db = TestingSessionLocal()
    try:
        row = db.execute(
            text(
                """
                SELECT target, target_type, tags, priority, enabled
                FROM asset
                WHERE id = :asset_id
                """
            ),
            {"asset_id": body["data"]["asset_id"]},
        ).fetchone()
        assert row is not None
        assert row[0] == "192.168.1.10"
        assert row[1] == "IP"
        assert row[2] == "ip"
        assert row[3] == 5
        assert row[4] == 1
    finally:
        db.close()


def test_create_asset_duplicate_rejected(client):
    token = get_token(client)
    response = client.post(
        "/api/v1/scan/assets",
        json={"target": "192.168.1.10", "target_type": "IP"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == 40001
    assert "资产已存在" in body["message"]


def test_create_asset_invalid_cidr_rejected(client):
    token = get_token(client)
    response = client.post(
        "/api/v1/scan/assets",
        json={"target": "10.0.0.1", "target_type": "CIDR"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == 40002
    assert "CIDR" in body["message"]


def test_update_asset_enabled_and_tags(client):
    token = get_token(client)

    create_resp = client.post(
        "/api/v1/scan/assets",
        json={"target": "example.com", "target_type": "DOMAIN"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 200
    asset_id = create_resp.json()["data"]["asset_id"]

    update_resp = client.put(
        f"/api/v1/scan/assets/{asset_id}",
        json={"enabled": False, "tags": "Prod, core, prod", "priority": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["code"] == 0

    db = TestingSessionLocal()
    try:
        row = db.execute(
            text(
                """
                SELECT enabled, tags, priority
                FROM asset
                WHERE id = :asset_id
                """
            ),
            {"asset_id": asset_id},
        ).fetchone()
        assert row is not None
        assert row[0] == 0
        assert row[1] == "prod,core"
        assert row[2] == 2
    finally:
        db.close()
