"""
R0 最小测试：版本查询与回滚接口
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from main import app
from core.database import Base, get_db


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
    now = datetime.utcnow()
    
    # 创建测试用户
    db.execute(text("""
        INSERT INTO user (username, password_hash, email, enabled, created_at, updated_at)
        VALUES ('admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'admin@test.com', 1, :now, :now)
    """), {"now": now})
    
    # 创建角色
    db.execute(text("""
        INSERT INTO role (name, description, created_at, updated_at)
        VALUES ('admin', '管理员', :now, :now)
    """), {"now": now})
    
    # 绑定用户角色
    db.execute(text("""
        INSERT INTO user_role (user_id, role_id, granted_by, created_at, updated_at)
        VALUES (1, 1, 'system', :now, :now)
    """), {"now": now})
    
    # 插入版本历史
    db.execute(text("""
        INSERT INTO release_history (version, git_commit, schema_version, deploy_env, status, deployed_by, created_at, updated_at)
        VALUES 
            ('v0.1.0', 'initial', '1.0.0', 'dev', 'active', 'system', :now, :now),
            ('v0.0.9', 'prev', '0.9.0', 'dev', 'rolled_back', 'system', :now, :now)
    """), {"now": now})
    
    db.commit()
    db.close()
    
    yield
    
    # 清理
    Base.metadata.drop_all(bind=engine)


def get_token():
    """获取测试 token"""
    response = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
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


def test_rollback_without_auth():
    """测试未授权回滚返回 401"""
    response = client.post("/api/system/rollback", json={
        "target_version": "v0.0.9",
        "reason": "测试回滚"
    })
    assert response.status_code == 401


def test_rollback_to_invalid_version():
    """测试回滚到不存在版本返回 40404"""
    token = get_token()
    response = client.post("/api/system/rollback", 
        json={
            "target_version": "v9.9.9",
            "reason": "测试不存在版本"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 40404
    data = response.json()
    assert "available_versions" in data["message"]


def test_rollback_success():
    """测试回滚到合法版本成功"""
    token = get_token()
    response = client.post("/api/system/rollback",
        json={
            "target_version": "v0.0.9",
            "reason": "测试回滚到 v0.0.9"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["rolled_back_to"] == "v0.0.9"
    assert "actions_taken" in data
