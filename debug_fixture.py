"""调试 fixture 中的 Base 对象"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from sqlalchemy import create_engine
from importlib import import_module

# 导入模块（模拟测试文件的导入顺序）
backend_main = import_module("main")
backend_db = import_module("core.database")
app = backend_main.app
Base = backend_db.Base
get_db = backend_db.get_db
PushChannel = backend_db.PushChannel

# 创建引擎
TEST_DATABASE_URL = "sqlite:///./debug_fixture.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

print(f"Base object id: {id(Base)}")
print(f"Base.metadata.tables keys: {list(Base.metadata.tables.keys())}")
print(f"PushChannel.__table__ in Base.metadata.tables: {PushChannel.__table__ in Base.metadata.tables.values()}")
print(f"PushChannel.__table__.key: {PushChannel.__table__.key}")

# 尝试创建表
print("\nCreating tables...")
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# 检查结果
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"Tables created: {tables}")
print(f"push_channel in tables: {'push_channel' in tables}")
