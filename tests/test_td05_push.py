"""TD-05: 告警通道补全测试"""
import sys
import os

# 设置测试数据库环境变量（必须在导入 app 之前）
os.environ["DATABASE_URL"] = "sqlite:///./test_td05.db"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from importlib import import_module

backend_main = import_module("main")
backend_db = import_module("core.database")
app = backend_main.app
Base = backend_db.Base
get_db = backend_db.get_db

TEST_DATABASE_URL = "sqlite:///./test_td05.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
PushChannel = backend_db.PushChannel

TEST_DATABASE_URL = "sqlite:///./test_td05.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """创建测试数据库"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    
    # 清理测试数据库文件
    import os
    db_path = "test_td05.db"
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except PermissionError:
            pass  # File in use, skip cleanup


@pytest.fixture(scope="module")
def client(setup_database):
    """创建测试客户端"""
    return TestClient(app)


def test_create_webhook_channel(client):
    """测试创建 Webhook 通道"""
    response = client.post("/api/v1/push/channels", json={
        "channel_type": "webhook",
        "channel_name": "test_webhook",
        "target": "https://httpbin.org/post",
        "config_json": '{"method": "POST", "headers": {"Content-Type": "application/json"}}',
        "enabled": 1
    })
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["message"] == "创建成功"


def test_create_wecom_channel(client):
    """测试创建企业微信通道"""
    response = client.post("/api/v1/push/channels", json={
        "channel_type": "wecom",
        "channel_name": "test_wecom",
        "target": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test",
        "enabled": 1
    })
    assert response.status_code == 200
    data = response.json()
    assert "id" in data


def test_create_duplicate_channel(client):
    """测试创建重复通道名称"""
    client.post("/api/v1/push/channels", json={
        "channel_type": "webhook",
        "channel_name": "duplicate_test",
        "target": "https://httpbin.org/post"
    })
    
    response = client.post("/api/v1/push/channels", json={
        "channel_type": "webhook",
        "channel_name": "duplicate_test",
        "target": "https://httpbin.org/post"
    })
    assert response.status_code == 400
    assert "通道名称已存在" in response.json()["message"]


def test_list_channels(client):
    """测试获取通道列表"""
    response = client.get("/api/v1/push/channels")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) >= 2


def test_update_channel(client):
    """测试更新通道"""
    # 先创建一个通道
    create_resp = client.post("/api/v1/push/channels", json={
        "channel_type": "webhook",
        "channel_name": "update_test",
        "target": "https://httpbin.org/post"
    })
    channel_id = create_resp.json()["id"]
    
    # 更新通道
    response = client.put(f"/api/v1/push/channels/{channel_id}", json={
        "target": "https://httpbin.org/anything",
        "enabled": 0
    })
    assert response.status_code == 200
    assert response.json()["message"] == "更新成功"


def test_delete_channel(client):
    """测试删除通道"""
    # 先创建一个通道
    create_resp = client.post("/api/v1/push/channels", json={
        "channel_type": "webhook",
        "channel_name": "delete_test",
        "target": "https://httpbin.org/post"
    })
    channel_id = create_resp.json()["id"]
    
    # 删除通道
    response = client.delete(f"/api/v1/push/channels/{channel_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "删除成功"
    
    # 验证已删除
    get_resp = client.get("/api/v1/push/channels")
    channels = get_resp.json()["data"]
    assert not any(c["id"] == channel_id for c in channels)


def test_test_webhook_channel(client):
    """测试 Webhook 通道推送（使用 httpbin.org）"""
    # 创建通道
    create_resp = client.post("/api/v1/push/channels", json={
        "channel_type": "webhook",
        "channel_name": "test_webhook_push",
        "target": "https://httpbin.org/post",
        "config_json": '{"method": "POST"}'
    })
    channel_id = create_resp.json()["id"]
    
    # 测试推送
    response = client.post(f"/api/v1/push/channels/{channel_id}/test")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_test_nonexistent_channel(client):
    """测试不存在的通道"""
    response = client.post("/api/v1/push/channels/99999/test")
    assert response.status_code == 404
    assert "通道不存在" in response.json()["message"]


def test_invalid_channel_type(client):
    """测试不支持的通道类型"""
    response = client.post("/api/v1/push/channels", json={
        "channel_type": "invalid_type",
        "channel_name": "invalid_test",
        "target": "https://example.com"
    })
    assert response.status_code == 400
    assert "不支持的通道类型" in response.json()["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
