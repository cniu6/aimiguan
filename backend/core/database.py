from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aimiguard.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ThreatEvent(Base):
    __tablename__ = "threat_event"
    
    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False)
    risk_level = Column(String)
    ai_score = Column(Integer)
    ai_reason = Column(Text)
    status = Column(String, nullable=False, index=True)
    trace_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ExecutionTask(Base):
    __tablename__ = "execution_task"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("threat_event.id"))
    device_id = Column(Integer, ForeignKey("device.id"))
    action = Column(String, nullable=False)
    state = Column(String, nullable=False)
    retry_count = Column(Integer, default=0)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    trace_id = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ScanTask(Base):
    __tablename__ = "scan_task"
    
    id = Column(Integer, primary_key=True, index=True)
    target = Column(String, nullable=False)
    target_type = Column(String)
    tool_name = Column(String)
    state = Column(String, nullable=False)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    trace_id = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ScanFinding(Base):
    __tablename__ = "scan_finding"
    
    id = Column(Integer, primary_key=True, index=True)
    scan_task_id = Column(Integer, ForeignKey("scan_task.id"))
    asset = Column(String)
    port = Column(Integer)
    service = Column(String)
    vuln_id = Column(String)
    severity = Column(String)
    evidence = Column(Text)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Device(Base):
    __tablename__ = "device"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ip = Column(String, nullable=False)
    port = Column(Integer)
    vendor = Column(String)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Credential(Base):
    __tablename__ = "credential"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("device.id"))
    username = Column(String, nullable=False)
    secret_ciphertext = Column(Text, nullable=False)
    key_version = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AIDecisionLog(Base):
    __tablename__ = "ai_decision_log"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("threat_event.id"))
    model_name = Column(String)
    decision = Column(String)
    confidence = Column(Integer)
    reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class AIChatSession(Base):
    __tablename__ = "ai_chat_session"
    
    id = Column(Integer, primary_key=True, index=True)
    context_type = Column(String)
    context_id = Column(String)
    operator = Column(String)
    started_at = Column(DateTime, default=datetime.utcnow)

class AIChatMessage(Base):
    __tablename__ = "ai_chat_message"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("ai_chat_session.id"))
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    evidence_refs = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class AIReport(Base):
    __tablename__ = "ai_report"
    
    id = Column(Integer, primary_key=True, index=True)
    report_type = Column(String)
    scope = Column(String)
    summary = Column(Text)
    detail_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class AITTSTask(Base):
    __tablename__ = "ai_tts_task"
    
    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String)
    source_id = Column(String)
    voice_model = Column(String)
    audio_path = Column(String)
    state = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class PluginRegistry(Base):
    __tablename__ = "plugin_registry"
    
    id = Column(Integer, primary_key=True, index=True)
    plugin_name = Column(String, nullable=False)
    plugin_type = Column(String)
    endpoint = Column(String)
    enabled = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PushChannel(Base):
    __tablename__ = "push_channel"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_type = Column(String, nullable=False)
    target = Column(String)
    enabled = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FirewallSyncTask(Base):
    __tablename__ = "firewall_sync_task"
    
    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String, nullable=False)
    firewall_vendor = Column(String)
    policy_id = Column(String)
    request_hash = Column(String, unique=True, nullable=False)
    state = Column(String, nullable=False)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class ModelProfile(Base):
    __tablename__ = "model_profile"
    
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, nullable=False)
    model_type = Column(String)
    is_local = Column(Boolean, default=True)
    priority = Column(Integer)
    enabled = Column(Boolean, default=True)

class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True, index=True)
    operator = Column(String)
    module = Column(String)
    action = Column(String)
    result = Column(String)
    trace_id = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
