"""测试表创建"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from sqlalchemy import create_engine, inspect
from importlib import import_module

# 导入模块
backend_db = import_module("core.database")
Base = backend_db.Base
PushChannel = backend_db.PushChannel

# 创建测试数据库
TEST_DATABASE_URL = "sqlite:///./test_create_tables.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

print(f"Base.metadata.tables keys: {list(Base.metadata.tables.keys())}")
print(f"PushChannel in metadata: {'push_channel' in Base.metadata.tables}")

# 创建所有表
print("\nCreating tables...")
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# 检查创建的表
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"\nTables created: {tables}")
print(f"push_channel table exists: {'push_channel' in tables}")

if 'push_channel' in tables:
    columns = inspector.get_columns('push_channel')
    print(f"\npush_channel columns: {[col['name'] for col in columns]}")
