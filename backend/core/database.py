from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Float,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, timezone
import sqlite3
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aimiguard.db")


def _adapt_datetime(value: datetime) -> str:
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.isoformat(sep=" ")


sqlite3.register_adapter(datetime, _adapt_datetime)


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Core Business ──


class ThreatEvent(Base):
    __tablename__ = "threat_event"
    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False)
    source_vendor = Column(String)
    source_type = Column(String)
    source_event_id = Column(String)
    attack_count = Column(Integer, default=1)
    asset_ip = Column(String)
    service_name = Column(String)
    service_type = Column(String)
    threat_label = Column(String)
    is_white = Column(Integer, default=0)
    ai_score = Column(Integer)
    ai_reason = Column(Text)
    action_suggest = Column(String)
    status = Column(String, nullable=False, default="PENDING", index=True)
    trace_id = Column(String, nullable=False, index=True)
    raw_payload = Column(Text)
    extra_json = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Asset(Base):
    __tablename__ = "asset"
    id = Column(Integer, primary_key=True, index=True)
    target = Column(String, unique=True, nullable=False)
    target_type = Column(String, nullable=False)
    tags = Column(Text)
    priority = Column(Integer, default=5)
    enabled = Column(Integer, default=1)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=lambda: datetime.now(timezone.utc))


class ExecutionTask(Base):
    __tablename__ = "execution_task"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("threat_event.id"), nullable=False)
    device_id = Column(Integer)
    action = Column(String, nullable=False)
    state = Column(String, nullable=False, default="QUEUED")
    retry_count = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    trace_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScanTask(Base):
    __tablename__ = "scan_task"
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("asset.id"), nullable=False)
    target = Column(String, nullable=False)
    target_type = Column(String, nullable=False)
    tool_name = Column(String, nullable=False)
    profile = Column(String)
    script_set = Column(String)
    state = Column(String, nullable=False, default="CREATED")
    priority = Column(Integer, default=5)
    timeout_seconds = Column(Integer, default=3600)
    retry_count = Column(Integer, default=0)
    raw_output_path = Column(String)
    error_message = Column(Text)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    trace_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScanFinding(Base):
    __tablename__ = "scan_finding"
    id = Column(Integer, primary_key=True, index=True)
    scan_task_id = Column(Integer, ForeignKey("scan_task.id"), nullable=False)
    asset = Column(String, nullable=False)
    port = Column(Integer)
    service = Column(String)
    vuln_id = Column(String)
    cve = Column(String)
    severity = Column(String)
    evidence = Column(Text)
    status = Column(String, nullable=False, default="NEW")
    trace_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Device(Base):
    __tablename__ = "device"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    ip = Column(String, nullable=False)
    port = Column(Integer, default=23)
    vendor = Column(String, nullable=False)
    device_type = Column(String)
    enabled = Column(Integer, default=1)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Credential(Base):
    __tablename__ = "credential"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("device.id"), nullable=False)
    username = Column(String, nullable=False)
    secret_ciphertext = Column(Text, nullable=False)
    key_version = Column(String, default="v1")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class AIDecisionLog(Base):
    __tablename__ = "ai_decision_log"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("threat_event.id"))
    scan_task_id = Column(Integer, ForeignKey("scan_task.id"))
    context_type = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    decision = Column(String)
    confidence = Column(Float)
    reason = Column(Text)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    trace_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AIChatSession(Base):
    __tablename__ = "ai_chat_session"
    id = Column(Integer, primary_key=True, index=True)
    context_type = Column(String)
    context_id = Column(Integer)
    operator = Column(String, nullable=False)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class AIChatMessage(Base):
    __tablename__ = "ai_chat_message"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("ai_chat_session.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    evidence_refs = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class AIReport(Base):
    __tablename__ = "ai_report"
    id = Column(Integer, primary_key=True, index=True)
    report_type = Column(String, nullable=False)
    scope = Column(String)
    summary = Column(Text, nullable=False)
    detail_path = Column(String)
    format = Column(String, default="markdown")
    trace_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AITTSTask(Base):
    __tablename__ = "ai_tts_task"
    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String, nullable=False)
    source_id = Column(Integer)
    text_content = Column(Text, nullable=False)
    voice_model = Column(String, default="local-tts-v1")
    audio_path = Column(String)
    state = Column(String, nullable=False, default="PENDING")
    error_message = Column(Text)
    trace_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PluginRegistry(Base):
    __tablename__ = "plugin_registry"
    id = Column(Integer, primary_key=True, index=True)
    plugin_name = Column(String, unique=True, nullable=False)
    plugin_type = Column(String, nullable=False)
    endpoint = Column(String)
    config_json = Column(Text)
    enabled = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PushChannel(Base):
    __tablename__ = "push_channel"
    id = Column(Integer, primary_key=True, index=True)
    channel_type = Column(String, nullable=False)
    channel_name = Column(String, unique=True, nullable=False)
    target = Column(String, nullable=False)
    config_json = Column(Text)
    enabled = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FirewallSyncTask(Base):
    __tablename__ = "firewall_sync_task"
    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String, nullable=False)
    firewall_vendor = Column(String, nullable=False)
    policy_id = Column(String)
    action = Column(String, nullable=False)
    request_hash = Column(String, unique=True, nullable=False)
    state = Column(String, nullable=False, default="PENDING")
    retry_count = Column(Integer, default=0)
    response_digest = Column(String)
    error_message = Column(Text)
    trace_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ModelProfile(Base):
    __tablename__ = "model_profile"
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, unique=True, nullable=False)
    model_type = Column(String, nullable=False)
    is_local = Column(Integer, default=1)
    endpoint = Column(String)
    priority = Column(Integer, default=10)
    enabled = Column(Integer, default=1)
    config_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── RBAC ──


class Role(Base):
    __tablename__ = "role"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Permission(Base):
    __tablename__ = "permission"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    resource = Column(String)
    action = Column(String)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserRole(Base):
    __tablename__ = "user_role"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("role.id"), nullable=False)
    granted_by = Column(String)
    reason = Column(Text)
    trace_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RolePermission(Base):
    __tablename__ = "role_permission"
    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("role.id"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permission.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    email = Column(String)
    full_name = Column(String)
    enabled = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_roles = relationship("UserRole", backref="user", lazy="joined")


# ── System Management ──


class ReleaseHistory(Base):
    __tablename__ = "release_history"
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String, nullable=False)
    git_commit = Column(String, nullable=False)
    schema_version = Column(String, nullable=False)
    deploy_env = Column(String, nullable=False)
    status = Column(String, nullable=False)
    deployed_by = Column(String)
    rollback_reason = Column(Text)
    trace_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SystemConfigSnapshot(Base):
    __tablename__ = "system_config_snapshot"
    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String, nullable=False, index=True)
    config_value = Column(Text)
    source = Column(String, nullable=False)
    is_sensitive = Column(Integer, nullable=False, default=0)
    env = Column(String, nullable=False, index=True)
    loaded_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Audit ──


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, index=True)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    target = Column(String, nullable=False)
    target_type = Column(String)
    target_ip = Column(String)
    reason = Column(Text)
    result = Column(String, nullable=False)
    error_message = Column(Text)
    trace_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)
