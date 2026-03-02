"""测试 S1-03：对话上下文隔离"""
import pytest
import hashlib
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.core.database import User, AIChatSession, AIChatMessage, Role, UserRole

client = TestClient(app)

def hash_password(password: str) -> str:
    """与 auth.py 保持一致的密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()

@pytest.fixture
def user1_token(db: Session):
    """创建用户1并获取token"""
    # 创建用户（使用正确的密码哈希）
    user = User(
        username="user1", 
        password_hash=hash_password("password123"), 
        enabled=True
    )
    db.add(user)
    db.flush()
    
    # 分配角色（需要角色才能通过权限验证）
    role = db.query(Role).filter(Role.name == "admin").first()
    if role:
        user_role = UserRole(user_id=user.id, role_id=role.id)
        db.add(user_role)
    
    db.commit()
    
    response = client.post("/api/v1/auth/login", json={
        "username": "user1",
        "password": "password123"
    })
    return response.json()["access_token"]

@pytest.fixture
def user2_token(db: Session):
    """创建用户2并获取token"""
    # 创建用户（使用正确的密码哈希）
    user = User(
        username="user2", 
        password_hash=hash_password("password123"), 
        enabled=True
    )
    db.add(user)
    db.flush()
    
    # 分配角色
    role = db.query(Role).filter(Role.name == "admin").first()
    if role:
        user_role = UserRole(user_id=user.id, role_id=role.id)
        db.add(user_role)
    
    db.commit()
    
    response = client.post("/api/v1/auth/login", json={
        "username": "user2",
        "password": "password123"
    })
    return response.json()["access_token"]

def test_session_ownership_isolation(db: Session, user1_token: str, user2_token: str):
    """测试会话归属隔离：用户只能访问自己的会话"""
    # 用户1创建会话
    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "Hello from user1"},
        headers={"Authorization": f"Bearer {user1_token}"}
    )
    assert response.status_code == 200
    session_id = response.json()["data"]["session_id"]
    
    # 用户2尝试访问用户1的会话 - 应该被拒绝
    response = client.get(
        f"/api/v1/ai/sessions/{session_id}/messages",
        headers={"Authorization": f"Bearer {user2_token}"}
    )
    assert response.status_code == 403
    assert "无权访问" in response.json()["message"]

def test_session_list_isolation(db: Session, user1_token: str, user2_token: str):
    """测试会话列表隔离：用户只能看到自己的会话"""
    # 用户1创建会话
    client.post(
        "/api/v1/ai/chat",
        json={"message": "User1 message"},
        headers={"Authorization": f"Bearer {user1_token}"}
    )
    
    # 用户2创建会话
    client.post(
        "/api/v1/ai/chat",
        json={"message": "User2 message"},
        headers={"Authorization": f"Bearer {user2_token}"}
    )
    
    # 用户1查看会话列表
    response = client.get(
        "/api/v1/ai/sessions",
        headers={"Authorization": f"Bearer {user1_token}"}
    )
    assert response.status_code == 200
    sessions = response.json()["data"]
    
    # 验证只返回用户1的会话
    user1 = db.query(User).filter(User.username == "user1").first()
    for session in sessions:
        assert session["user_id"] == user1.id

def test_context_endpoint_rbac(db: Session, user1_token: str, user2_token: str):
    """测试 /context 端点的 RBAC 校验"""
    # 用户1创建会话
    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "Test message"},
        headers={"Authorization": f"Bearer {user1_token}"}
    )
    session_id = response.json()["data"]["session_id"]
    
    # 用户1访问自己的上下文 - 应该成功
    response = client.get(
        f"/api/v1/ai/chat/{session_id}/context",
        headers={"Authorization": f"Bearer {user1_token}"}
    )
    assert response.status_code == 200
    context = response.json()["data"]
    assert context["session_id"] == session_id
    assert len(context["messages"]) > 0
    
    # 用户2尝试访问用户1的上下文 - 应该被拒绝
    response = client.get(
        f"/api/v1/ai/chat/{session_id}/context",
        headers={"Authorization": f"Bearer {user2_token}"}
    )
    assert response.status_code == 403

def test_session_expiration(db: Session, user1_token: str):
    """测试会话过期后拒绝访问"""
    # 创建已过期的会话
    user1 = db.query(User).filter(User.username == "user1").first()
    expired_session = AIChatSession(
        user_id=user1.id,
        operator="user1",
        started_at=datetime.now(timezone.utc) - timedelta(hours=25),
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    db.add(expired_session)
    db.commit()
    
    # 尝试访问过期会话 - 应该返回 410
    response = client.get(
        f"/api/v1/ai/sessions/{expired_session.id}/messages",
        headers={"Authorization": f"Bearer {user1_token}"}
    )
    assert response.status_code == 410
    assert "已过期" in response.json()["message"]

def test_session_cleanup_service(db: Session):
    """测试会话清理服务"""
    from backend.services.session_cleanup import SessionCleanupService
    
    # 创建测试用户
    user = User(username="cleanup_test", password_hash="hash", enabled=True)
    db.add(user)
    db.flush()
    
    # 创建过期会话
    expired_session = AIChatSession(
        user_id=user.id,
        operator="cleanup_test",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    db.add(expired_session)
    db.flush()
    
    # 添加消息
    msg = AIChatMessage(
        session_id=expired_session.id,
        role="user",
        content="Test message",
        created_at=datetime.now(timezone.utc)
    )
    db.add(msg)
    db.commit()
    
    # 执行清理
    cleaned = SessionCleanupService.cleanup_expired_sessions(db)
    assert cleaned == 1
    
    # 验证会话已标记为结束
    db.refresh(expired_session)
    assert expired_session.ended_at is not None
    
    # 验证消息已删除
    messages = db.query(AIChatMessage).filter(
        AIChatMessage.session_id == expired_session.id
    ).all()
    assert len(messages) == 0

def test_multi_turn_conversation_isolation(db: Session, user1_token: str):
    """测试多轮对话的上下文隔离"""
    # 创建第一个会话
    response1 = client.post(
        "/api/v1/ai/chat",
        json={"message": "First session message"},
        headers={"Authorization": f"Bearer {user1_token}"}
    )
    session1_id = response1.json()["data"]["session_id"]
    
    # 创建第二个会话
    response2 = client.post(
        "/api/v1/ai/chat",
        json={"message": "Second session message"},
        headers={"Authorization": f"Bearer {user1_token}"}
    )
    session2_id = response2.json()["data"]["session_id"]
    
    # 验证两个会话的上下文完全隔离
    context1 = client.get(
        f"/api/v1/ai/chat/{session1_id}/context",
        headers={"Authorization": f"Bearer {user1_token}"}
    ).json()["data"]
    
    context2 = client.get(
        f"/api/v1/ai/chat/{session2_id}/context",
        headers={"Authorization": f"Bearer {user1_token}"}
    ).json()["data"]
    
    # 验证消息内容不同
    assert context1["messages"][0]["content"] != context2["messages"][0]["content"]
    assert "First session" in context1["messages"][0]["content"]
    assert "Second session" in context2["messages"][0]["content"]

def test_force_end_session(db: Session, user1_token: str):
    """测试强制结束会话并清除上下文"""
    from backend.services.session_cleanup import SessionCleanupService
    
    # 创建会话
    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "Test"},
        headers={"Authorization": f"Bearer {user1_token}"}
    )
    session_id = response.json()["data"]["session_id"]
    
    # 强制结束会话
    result = SessionCleanupService.force_end_session(db, session_id)
    assert result is True
    
    # 验证会话已结束
    session = db.query(AIChatSession).filter(AIChatSession.id == session_id).first()
    assert session.ended_at is not None
    
    # 验证消息已清除
    messages = db.query(AIChatMessage).filter(
        AIChatMessage.session_id == session_id
    ).all()
    assert len(messages) == 0
