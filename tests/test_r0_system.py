"""
R0 最小测试：版本查询与回滚接口
"""

import sys
import os
from importlib import import_module
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

backend_main = import_module("main")
backend_db = import_module("core.database")
app = backend_main.app
Base = backend_db.Base
get_db = backend_db.get_db


# 测试数据库
TEST_DATABASE_URL = "sqlite:///./test_r0.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """初始化测试数据库"""
    # 先删除旧表，确保使用最新 ORM 模型
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # 创建测试用户
    db.execute(
        text("""
        INSERT INTO user (username, password_hash, email, enabled, created_at, updated_at)
        VALUES ('admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'admin@test.com', 1, :now, :now)
    """),
        {"now": now},
    )

    # 创建角色
    db.execute(
        text("""
        INSERT INTO role (name, description, created_at, updated_at)
        VALUES ('admin', '管理员', :now, :now)
    """),
        {"now": now},
    )

    # 绑定用户角色
    db.execute(
        text("""
        INSERT INTO user_role (user_id, role_id, granted_by, created_at, updated_at)
        VALUES (1, 1, 'system', :now, :now)
    """),
        {"now": now},
    )

    # 创建权限并绑定角色
    db.execute(
        text(
            """
            INSERT INTO permission (name, resource, action, description, created_at)
            VALUES ('manage_system', 'system', 'manage', '系统管理权限', :now)
            """
        ),
        {"now": now},
    )
    db.execute(
        text(
            """
            INSERT INTO role_permission (role_id, permission_id, created_at)
            VALUES (1, 1, :now)
            """
        ),
        {"now": now},
    )

    # 插入版本历史
    db.execute(
        text("""
        INSERT INTO release_history (version, git_commit, schema_version, deploy_env, status, deployed_by, created_at, updated_at)
        VALUES 
            ('v0.1.0', 'initial', '1.0.0', 'dev', 'active', 'system', :now, :now),
            ('v0.0.9', 'prev', '0.9.0', 'dev', 'rolled_back', 'system', :now, :now)
    """),
        {"now": now},
    )

    db.commit()
    db.close()

    yield

    # 清理
    Base.metadata.drop_all(bind=engine)


def get_token():
    """获取测试 token"""
    response = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_get_version():
    """测试查询版本成功"""
    response = client.get("/api/system/version")
    assert response.status_code == 200
    data = response.json()
    assert "app_version" in data
    assert "git_commit" in data
    assert "build_time" in data
    assert "schema_version" in data
    assert "env" in data


def test_get_version_v1():
    """测试 v1 路径兼容"""
    response = client.get("/api/v1/system/version")
    assert response.status_code == 200


def test_trace_id_header_passthrough():
    """测试 trace_id 透传"""
    response = client.get("/api/system/version", headers={"X-Trace-ID": "trace-r0-001"})
    assert response.status_code == 200
    assert response.headers.get("X-Trace-ID") == "trace-r0-001"


def test_get_system_profile_v1():
    """测试 system profile 返回用户资料和权限"""
    token = get_token()
    response = client.get(
        "/api/v1/system/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"
    assert "manage_system" in data["permissions"]


def test_rollback_without_auth():
    """测试未授权回滚返回 401"""
    response = client.post(
        "/api/system/rollback", json={"target_version": "v0.0.9", "reason": "测试回滚"}
    )
    assert response.status_code == 401


def test_rollback_to_invalid_version():
    """测试回滚到不存在版本返回 40404"""
    token = get_token()
    response = client.post(
        "/api/system/rollback",
        json={"target_version": "v9.9.9", "reason": "测试不存在版本"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 40404
    data = response.json()
    assert "available_versions" in data["message"]


def test_rollback_success():
    """测试回滚到合法版本成功"""
    token = get_token()
    response = client.post(
        "/api/system/rollback",
        json={"target_version": "v0.0.9", "reason": "测试回滚到 v0.0.9"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["rolled_back_to"] == "v0.0.9"
    assert "actions_taken" in data


def test_rollback_success_v1_route():
    """测试 v1 路由回滚成功"""
    token = get_token()
    response = client.post(
        "/api/v1/system/rollback",
        json={
            "target_version": "v0.0.9",
            "reason": "测试 v1 路由回滚",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["rolled_back_to"] == "v0.0.9"


def test_rollback_writes_audit_log():
    """测试回滚操作写入审计日志"""
    db = TestingSessionLocal()
    try:
        rollback_count = (
            db.execute(
                text("SELECT COUNT(*) FROM audit_log WHERE action = 'system_rollback'")
            ).scalar()
            or 0
        )
        assert rollback_count >= 2

        latest = db.execute(
            text(
                """
                SELECT action, target, reason, result
                FROM audit_log
                WHERE action = 'system_rollback'
                ORDER BY id DESC
                LIMIT 1
                """
            )
        ).fetchone()
        assert latest is not None
        assert latest[0] == "system_rollback"
        assert latest[1] == "v0.0.9"
        assert latest[3] == "success"
    finally:
        db.close()


def test_mode_switch_persisted_and_audited():
    """测试模式切换持久化到 system_config_snapshot 并写审计"""
    token = get_token()
    response = client.post(
        "/api/v1/system/mode",
        json={"mode": "ACTIVE", "reason": "测试切换"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    mode_data = response.json()
    assert mode_data["mode"] == "ACTIVE"
    assert mode_data["reason"] == "测试切换"

    db = TestingSessionLocal()
    try:
        latest_snapshot = db.execute(
            text(
                """
                SELECT config_value
                FROM system_config_snapshot
                WHERE config_key = 'system_mode'
                ORDER BY loaded_at DESC, id DESC
                LIMIT 1
                """
            )
        ).fetchone()
        assert latest_snapshot is not None
        snapshot_payload = json.loads(latest_snapshot[0])
        assert snapshot_payload["mode"] == "ACTIVE"
        assert snapshot_payload["reason"] == "测试切换"

        latest_audit = db.execute(
            text(
                """
                SELECT action, target, result
                FROM audit_log
                WHERE action = 'set_mode:ACTIVE'
                ORDER BY id DESC
                LIMIT 1
                """
            )
        ).fetchone()
        assert latest_audit is not None
        assert latest_audit[0] == "set_mode:ACTIVE"
        assert latest_audit[1] == "system_mode"
        assert latest_audit[2] == "success"
    finally:
        db.close()


def test_logout_invalidates_token():
    """测试登出后 token 失效"""
    token = get_token()
    logout_response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == 200

    profile_response = client.get(
        "/api/v1/system/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile_response.status_code == 40102
