"""Step 4 资产管理最小验证：模型字段与创建校验"""

import os
import sys
from datetime import datetime, timezone
from importlib import import_module

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

backend_main = import_module("main")
backend_db = import_module("core.database")
app = backend_main.app
Base = backend_db.Base
get_db = backend_db.get_db

TEST_DATABASE_URL = "sqlite:///./test_step4_scan_assets.db"
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
            INSERT INTO user_role (user_id, role_id, granted_by, created_at, updated_at)
            VALUES (1, 1, 'system', :now, :now)
            """
        ),
        {"now": now},
    )

    db.commit()
    db.close()

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def get_token() -> str:
    response = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_create_asset_ip_with_default_tag_and_enabled():
    token = get_token()
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


def test_create_asset_duplicate_rejected():
    token = get_token()
    response = client.post(
        "/api/v1/scan/assets",
        json={"target": "192.168.1.10", "target_type": "IP"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == 40000
    assert "资产已存在" in body["message"]


def test_create_asset_invalid_cidr_rejected():
    token = get_token()
    response = client.post(
        "/api/v1/scan/assets",
        json={"target": "10.0.0.1", "target_type": "CIDR"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == 40000
    assert "CIDR" in body["message"]


def test_update_asset_enabled_and_tags():
    token = get_token()

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
