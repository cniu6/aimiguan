"""pytest 配置文件 - 统一管理测试数据库隔离"""
import os
import sys
import pytest
from datetime import datetime, timezone

# 在导入任何 backend 模块之前设置测试数据库
TEST_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test_all.db"))
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

# 添加 backend 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from importlib import import_module

# 导入 backend 模块
backend_main = import_module("main")
backend_db = import_module("core.database")

app = backend_main.app
Base = backend_db.Base
get_db = backend_db.get_db

# 创建测试数据库引擎
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """测试数据库会话生成器"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """会话级别的数据库设置 - 所有测试共享同一个数据库"""
    # 清除之前的覆盖
    app.dependency_overrides.clear()
    
    # 创建所有表
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    
    # 设置依赖覆盖
    app.dependency_overrides[get_db] = override_get_db
    
    # 初始化测试数据（admin 用户等）
    db = TestingSessionLocal()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        # 创建 admin 用户（密码：admin123，使用 SHA256 哈希）
        import hashlib
        password_hash = hashlib.sha256("admin123".encode()).hexdigest()
        db.execute(
            text(
                """
                INSERT OR IGNORE INTO user (id, username, password_hash, email, enabled, created_at, updated_at)
                VALUES (1, 'admin', :password_hash, 'admin@example.com', 1, :now, :now)
                """
            ),
            {"password_hash": password_hash, "now": now}
        )
        
        # 创建默认角色
        db.execute(
            text(
                """
                INSERT OR IGNORE INTO role (id, name, description, created_at, updated_at)
                VALUES (1, 'admin', 'Administrator', :now, :now)
                """
            ),
            {"now": now}
        )
        
        # 关联用户和角色
        db.execute(
            text(
                """
                INSERT OR IGNORE INTO user_role (user_id, role_id)
                VALUES (1, 1)
                """
            )
        )
        
        # 创建权限
        permissions = [
            ("ai_chat", "ai", "chat", "AI 对话"),
            ("view_ai_sessions", "ai", "view", "查看 AI 会话"),
        ]
        for name, resource, action, desc in permissions:
            db.execute(
                text(
                    """
                    INSERT OR IGNORE INTO permission (name, resource, action, description, created_at)
                    VALUES (:name, :resource, :action, :desc, :now)
                    """
                ),
                {"name": name, "resource": resource, "action": action, "desc": desc, "now": now}
            )
        
        # 将所有权限分配给 admin 角色
        db.execute(
            text(
                """
                INSERT OR IGNORE INTO role_permission (role_id, permission_id, created_at)
                SELECT 1, id, :now FROM permission
                """
            ),
            {"now": now}
        )
        
        db.commit()
    finally:
        db.close()
    
    yield
    
    # 清理
    app.dependency_overrides.clear()
    test_engine.dispose()


@pytest.fixture(scope="session")
def client(setup_test_database):
    """会话级别的测试客户端"""
    return TestClient(app)


@pytest.fixture(scope="function")
def db():
    """函数级别的数据库会话 fixture"""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function", autouse=True)
def reset_test_data():
    """每个测试函数运行前清理非核心数据"""
    db = TestingSessionLocal()
    try:
        # 清理测试数据（保留 admin 用户和角色）
        db.execute(text("DELETE FROM ai_chat_message"))
        db.execute(text("DELETE FROM ai_chat_session"))
        db.execute(text("DELETE FROM push_channel"))
        db.execute(text("DELETE FROM scan_task"))
        db.execute(text("DELETE FROM scan_finding"))
        db.execute(text("DELETE FROM asset WHERE id > 0"))  # 清理所有资产
        db.execute(text("DELETE FROM threat_event"))
        db.execute(text("DELETE FROM user WHERE id > 1"))  # 清理测试用户（保留 admin）
        db.commit()
    finally:
        db.close()
    
    yield
