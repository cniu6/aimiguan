-- Aimiguan MVP Schema
-- 本文件包含所有核心表与P0补充表的建表语句
-- 执行顺序：核心业务表 -> RBAC权限表 -> 系统管理表 -> 审计与监控表

-- ============================================================
-- 核心业务表（MVP）
-- ============================================================

-- 威胁事件表
CREATE TABLE IF NOT EXISTS threat_event (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ip TEXT NOT NULL,
  source TEXT NOT NULL,
  source_vendor TEXT,
  source_type TEXT,
  source_event_id TEXT,
  attack_count INTEGER DEFAULT 1,
  asset_ip TEXT,
  service_name TEXT,
  service_type TEXT,
  threat_label TEXT,
  is_white INTEGER DEFAULT 0,
  ai_score INTEGER,
  ai_reason TEXT,
  action_suggest TEXT,
  status TEXT NOT NULL CHECK(status IN ('PENDING','APPROVED','REJECTED','EXECUTING','DONE','FAILED')) DEFAULT 'PENDING',
  trace_id TEXT NOT NULL,
  raw_payload TEXT,
  extra_json TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_threat_event_status ON threat_event(status);
CREATE INDEX IF NOT EXISTS idx_threat_event_trace_id ON threat_event(trace_id);
CREATE INDEX IF NOT EXISTS idx_threat_event_ip ON threat_event(ip);
CREATE INDEX IF NOT EXISTS idx_threat_event_created_at ON threat_event(created_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_threat_event_dedup ON threat_event(source_vendor, source_event_id) WHERE source_event_id IS NOT NULL;

-- 执行任务表
CREATE TABLE IF NOT EXISTS execution_task (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id INTEGER NOT NULL,
  device_id INTEGER,
  action TEXT NOT NULL CHECK(action IN ('BLOCK','UNBLOCK','MONITOR')),
  state TEXT NOT NULL CHECK(state IN ('QUEUED','RUNNING','SUCCESS','FAILED','RETRYING','MANUAL_REQUIRED')) DEFAULT 'QUEUED',
  retry_count INTEGER NOT NULL DEFAULT 0,
  error_message TEXT,
  started_at TEXT,
  ended_at TEXT,
  trace_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (event_id) REFERENCES threat_event(id)
);

CREATE INDEX IF NOT EXISTS idx_execution_task_state ON execution_task(state);
CREATE INDEX IF NOT EXISTS idx_execution_task_event_id ON execution_task(event_id);
CREATE INDEX IF NOT EXISTS idx_execution_task_trace_id ON execution_task(trace_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_execution_task_idempotent ON execution_task(event_id, device_id, action) WHERE state NOT IN ('SUCCESS','FAILED');

-- 资产表
CREATE TABLE IF NOT EXISTS asset (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  target TEXT NOT NULL UNIQUE,
  target_type TEXT NOT NULL CHECK(target_type IN ('IP','CIDR','DOMAIN')),
  tags TEXT,
  priority INTEGER DEFAULT 5,
  enabled INTEGER NOT NULL DEFAULT 1,
  description TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_asset_enabled ON asset(enabled);
CREATE INDEX IF NOT EXISTS idx_asset_priority ON asset(priority);

-- 扫描任务表
CREATE TABLE IF NOT EXISTS scan_task (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_id INTEGER NOT NULL,
  target TEXT NOT NULL,
  target_type TEXT NOT NULL,
  tool_name TEXT NOT NULL,
  profile TEXT,
  script_set TEXT,
  state TEXT NOT NULL CHECK(state IN ('CREATED','DISPATCHED','RUNNING','PARSED','REPORTED','FAILED','FAILED_TIMEOUT','FAILED_PARSE','UNREACHABLE')) DEFAULT 'CREATED',
  priority INTEGER DEFAULT 5,
  timeout_seconds INTEGER DEFAULT 3600,
  retry_count INTEGER DEFAULT 0,
  raw_output_path TEXT,
  error_message TEXT,
  started_at TEXT,
  ended_at TEXT,
  trace_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (asset_id) REFERENCES asset(id)
);

CREATE INDEX IF NOT EXISTS idx_scan_task_state ON scan_task(state);
CREATE INDEX IF NOT EXISTS idx_scan_task_asset_id ON scan_task(asset_id);
CREATE INDEX IF NOT EXISTS idx_scan_task_trace_id ON scan_task(trace_id);
CREATE INDEX IF NOT EXISTS idx_scan_task_created_at ON scan_task(created_at);

-- 扫描发现表
CREATE TABLE IF NOT EXISTS scan_finding (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scan_task_id INTEGER NOT NULL,
  asset TEXT NOT NULL,
  port INTEGER,
  service TEXT,
  vuln_id TEXT,
  cve TEXT,
  severity TEXT CHECK(severity IN ('CRITICAL','HIGH','MEDIUM','LOW','INFO')),
  evidence TEXT,
  status TEXT NOT NULL CHECK(status IN ('NEW','CONFIRMED','FALSE_POSITIVE','FIXED','IGNORED')) DEFAULT 'NEW',
  trace_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (scan_task_id) REFERENCES scan_task(id)
);

CREATE INDEX IF NOT EXISTS idx_scan_finding_task_id ON scan_finding(scan_task_id);
CREATE INDEX IF NOT EXISTS idx_scan_finding_severity ON scan_finding(severity);
CREATE INDEX IF NOT EXISTS idx_scan_finding_status ON scan_finding(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_scan_finding_dedup ON scan_finding(asset, port, vuln_id) WHERE vuln_id IS NOT NULL;

-- 设备表
CREATE TABLE IF NOT EXISTS device (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  ip TEXT NOT NULL,
  port INTEGER NOT NULL DEFAULT 23,
  vendor TEXT NOT NULL,
  device_type TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  description TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_device_enabled ON device(enabled);

-- 凭据表（敏感）
CREATE TABLE IF NOT EXISTS credential (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id INTEGER NOT NULL,
  username TEXT NOT NULL,
  secret_ciphertext TEXT NOT NULL,
  key_version TEXT NOT NULL DEFAULT 'v1',
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (device_id) REFERENCES device(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_credential_device_id ON credential(device_id);
CREATE INDEX IF NOT EXISTS idx_credential_key_version ON credential(key_version);

-- AI决策日志表
CREATE TABLE IF NOT EXISTS ai_decision_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id INTEGER,
  scan_task_id INTEGER,
  context_type TEXT NOT NULL CHECK(context_type IN ('threat','scan','chat')),
  model_name TEXT NOT NULL,
  decision TEXT,
  confidence REAL,
  reason TEXT,
  prompt_tokens INTEGER,
  completion_tokens INTEGER,
  trace_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (event_id) REFERENCES threat_event(id),
  FOREIGN KEY (scan_task_id) REFERENCES scan_task(id)
);

CREATE INDEX IF NOT EXISTS idx_ai_decision_event_id ON ai_decision_log(event_id);
CREATE INDEX IF NOT EXISTS idx_ai_decision_scan_task_id ON ai_decision_log(scan_task_id);
CREATE INDEX IF NOT EXISTS idx_ai_decision_trace_id ON ai_decision_log(trace_id);

-- AI对话会话表
CREATE TABLE IF NOT EXISTS ai_chat_session (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  context_type TEXT CHECK(context_type IN ('threat','scan','general')),
  context_id INTEGER,
  operator TEXT NOT NULL,
  started_at TEXT NOT NULL DEFAULT (datetime('now')),
  ended_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ai_chat_session_operator ON ai_chat_session(operator);
CREATE INDEX IF NOT EXISTS idx_ai_chat_session_context ON ai_chat_session(context_type, context_id);

-- AI对话消息表
CREATE TABLE IF NOT EXISTS ai_chat_message (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
  content TEXT NOT NULL,
  evidence_refs TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (session_id) REFERENCES ai_chat_session(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ai_chat_message_session_id ON ai_chat_message(session_id);

-- AI报告表
CREATE TABLE IF NOT EXISTS ai_report (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_type TEXT NOT NULL CHECK(report_type IN ('threat_summary','scan_analysis','daily','weekly','incident')),
  scope TEXT,
  summary TEXT NOT NULL,
  detail_path TEXT,
  format TEXT DEFAULT 'markdown',
  trace_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ai_report_type ON ai_report(report_type);
CREATE INDEX IF NOT EXISTS idx_ai_report_created_at ON ai_report(created_at);

-- AI TTS任务表
CREATE TABLE IF NOT EXISTS ai_tts_task (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_type TEXT NOT NULL CHECK(source_type IN ('alert','report','message')),
  source_id INTEGER,
  text_content TEXT NOT NULL,
  voice_model TEXT NOT NULL DEFAULT 'local-tts-v1',
  audio_path TEXT,
  state TEXT NOT NULL CHECK(state IN ('PENDING','PROCESSING','COMPLETED','FAILED')) DEFAULT 'PENDING',
  error_message TEXT,
  trace_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ai_tts_task_state ON ai_tts_task(state);
CREATE INDEX IF NOT EXISTS idx_ai_tts_task_source ON ai_tts_task(source_type, source_id);

-- 插件注册表
CREATE TABLE IF NOT EXISTS plugin_registry (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  plugin_name TEXT NOT NULL UNIQUE,
  plugin_type TEXT NOT NULL CHECK(plugin_type IN ('mcp','webhook','bot')),
  endpoint TEXT,
  config_json TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_plugin_enabled ON plugin_registry(enabled);

-- 推送通道表
CREATE TABLE IF NOT EXISTS push_channel (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  channel_type TEXT NOT NULL CHECK(channel_type IN ('dingtalk','wecom','email','webhook')),
  channel_name TEXT NOT NULL UNIQUE,
  target TEXT NOT NULL,
  config_json TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_push_channel_enabled ON push_channel(enabled);

-- 防火墙同步任务表
CREATE TABLE IF NOT EXISTS firewall_sync_task (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ip TEXT NOT NULL,
  firewall_vendor TEXT NOT NULL,
  policy_id TEXT,
  action TEXT NOT NULL CHECK(action IN ('ADD','REMOVE')),
  request_hash TEXT NOT NULL UNIQUE,
  state TEXT NOT NULL CHECK(state IN ('PENDING','RUNNING','SUCCESS','FAILED','RETRYING','MANUAL_REQUIRED')) DEFAULT 'PENDING',
  retry_count INTEGER NOT NULL DEFAULT 0,
  response_digest TEXT,
  error_message TEXT,
  trace_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_firewall_sync_state ON firewall_sync_task(state);
CREATE INDEX IF NOT EXISTS idx_firewall_sync_ip ON firewall_sync_task(ip);
CREATE INDEX IF NOT EXISTS idx_firewall_sync_trace_id ON firewall_sync_task(trace_id);

-- 模型配置表
CREATE TABLE IF NOT EXISTS model_profile (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  model_name TEXT NOT NULL UNIQUE,
  model_type TEXT NOT NULL CHECK(model_type IN ('llm','tts','embedding')),
  is_local INTEGER NOT NULL DEFAULT 1,
  endpoint TEXT,
  priority INTEGER DEFAULT 10,
  enabled INTEGER NOT NULL DEFAULT 1,
  config_json TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_model_profile_enabled ON model_profile(enabled);
CREATE INDEX IF NOT EXISTS idx_model_profile_priority ON model_profile(priority);

-- ============================================================
-- P0 系统管理表
-- ============================================================

-- 版本与发布历史
CREATE TABLE IF NOT EXISTS release_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  version TEXT NOT NULL,
  git_commit TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  deploy_env TEXT NOT NULL CHECK(deploy_env IN ('dev','staging','production')),
  status TEXT NOT NULL CHECK(status IN ('deployed','active','rolled_back','failed')),
  deployed_by TEXT,
  rollback_reason TEXT,
  trace_id TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_release_history_env_status ON release_history(deploy_env, status);
CREATE INDEX IF NOT EXISTS idx_release_history_version ON release_history(version);

-- 配置快照（用于审计和回滚）
CREATE TABLE IF NOT EXISTS system_config_snapshot (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  config_key TEXT NOT NULL,
  config_value TEXT,
  source TEXT NOT NULL CHECK(source IN ('env','dotenv','default')),
  is_sensitive INTEGER NOT NULL DEFAULT 0,
  env TEXT NOT NULL CHECK(env IN ('dev','staging','production')),
  loaded_at TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_config_snapshot_key_env ON system_config_snapshot(config_key, env);
CREATE INDEX IF NOT EXISTS idx_config_snapshot_loaded_at ON system_config_snapshot(loaded_at);

-- ============================================================
-- P0 RBAC权限体系
-- ============================================================

-- 角色表
CREATE TABLE IF NOT EXISTS role (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 权限表
CREATE TABLE IF NOT EXISTS permission (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  resource TEXT NOT NULL,
  action TEXT NOT NULL,
  description TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_permission_resource_action ON permission(resource, action);

-- 角色权限关联表
CREATE TABLE IF NOT EXISTS role_permission (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  role_id INTEGER NOT NULL,
  permission_id INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (role_id) REFERENCES role(id) ON DELETE CASCADE,
  FOREIGN KEY (permission_id) REFERENCES permission(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_role_permission_unique ON role_permission(role_id, permission_id);

-- 用户表
CREATE TABLE IF NOT EXISTS user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  email TEXT,
  full_name TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_user_enabled ON user(enabled);

-- 用户角色关联表
CREATE TABLE IF NOT EXISTS user_role (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  role_id INTEGER NOT NULL,
  granted_by TEXT,
  reason TEXT,
  trace_id TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
  FOREIGN KEY (role_id) REFERENCES role(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_role_user_id ON user_role(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_role_unique ON user_role(user_id, role_id);

-- 访问审计表
CREATE TABLE IF NOT EXISTS access_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  username TEXT,
  action TEXT NOT NULL,
  resource TEXT NOT NULL,
  permission_required TEXT,
  result TEXT NOT NULL CHECK(result IN ('granted','denied')),
  reason TEXT,
  trace_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_access_audit_user_id ON access_audit(user_id);
CREATE INDEX IF NOT EXISTS idx_access_audit_result ON access_audit(result);
CREATE INDEX IF NOT EXISTS idx_access_audit_trace_id ON access_audit(trace_id);
CREATE INDEX IF NOT EXISTS idx_access_audit_created_at ON access_audit(created_at);

-- ============================================================
-- P0 备份与恢复
-- ============================================================

-- 备份任务表
CREATE TABLE IF NOT EXISTS backup_job (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_type TEXT NOT NULL CHECK(job_type IN ('full','incremental')),
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL CHECK(status IN ('pending','running','success','failed')),
  artifact_uri TEXT,
  checksum TEXT,
  size_bytes INTEGER,
  error_message TEXT,
  triggered_by TEXT,
  trace_id TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_backup_job_status ON backup_job(status);
CREATE INDEX IF NOT EXISTS idx_backup_job_started_at ON backup_job(started_at);

-- 恢复任务表
CREATE TABLE IF NOT EXISTS restore_job (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  backup_id INTEGER NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL CHECK(status IN ('pending','running','success','failed')),
  consistency_check_result TEXT,
  error_message TEXT,
  triggered_by TEXT,
  reason TEXT,
  trace_id TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (backup_id) REFERENCES backup_job(id)
);

CREATE INDEX IF NOT EXISTS idx_restore_job_status ON restore_job(status);
CREATE INDEX IF NOT EXISTS idx_restore_job_backup_id ON restore_job(backup_id);

-- ============================================================
-- P0 安全扫描报告
-- ============================================================

CREATE TABLE IF NOT EXISTS security_scan_report (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scan_type TEXT NOT NULL CHECK(scan_type IN ('dependency_vulnerability','container_image','code_analysis')),
  tool TEXT NOT NULL,
  summary_json TEXT NOT NULL,
  critical_count INTEGER NOT NULL DEFAULT 0,
  high_count INTEGER NOT NULL DEFAULT 0,
  medium_count INTEGER NOT NULL DEFAULT 0,
  low_count INTEGER NOT NULL DEFAULT 0,
  sbom_uri TEXT,
  passed_gate INTEGER NOT NULL DEFAULT 0,
  gate_rule TEXT,
  scanned_at TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_security_scan_type ON security_scan_report(scan_type);
CREATE INDEX IF NOT EXISTS idx_security_scan_scanned_at ON security_scan_report(scanned_at);
CREATE INDEX IF NOT EXISTS idx_security_scan_passed_gate ON security_scan_report(passed_gate);

-- ============================================================
-- P0 告警与事故闭环
-- ============================================================

CREATE TABLE IF NOT EXISTS alert_event (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  level TEXT NOT NULL CHECK(level IN ('info','warning','critical')),
  type TEXT NOT NULL,
  source TEXT NOT NULL,
  summary TEXT NOT NULL,
  payload_json TEXT,
  status TEXT NOT NULL CHECK(status IN ('NEW','ACKED','RESOLVED','POSTMORTEM')) DEFAULT 'NEW',
  acked_by TEXT,
  acked_at TEXT,
  resolved_by TEXT,
  resolved_at TEXT,
  resolution TEXT,
  postmortem_author TEXT,
  postmortem_at TEXT,
  postmortem_content TEXT,
  trace_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_alert_event_status ON alert_event(status);
CREATE INDEX IF NOT EXISTS idx_alert_event_level ON alert_event(level);
CREATE INDEX IF NOT EXISTS idx_alert_event_type ON alert_event(type);
CREATE INDEX IF NOT EXISTS idx_alert_event_trace_id ON alert_event(trace_id);
CREATE INDEX IF NOT EXISTS idx_alert_event_created_at ON alert_event(created_at);

-- ============================================================
-- P0 指标采集与阈值告警
-- ============================================================

CREATE TABLE IF NOT EXISTS metric_point (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  metric TEXT NOT NULL,
  value REAL NOT NULL,
  labels_json TEXT,
  ts TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_metric_point_metric_ts ON metric_point(metric, ts);
CREATE INDEX IF NOT EXISTS idx_metric_point_ts ON metric_point(ts);

CREATE TABLE IF NOT EXISTS metric_rule (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  metric TEXT NOT NULL UNIQUE,
  operator TEXT NOT NULL CHECK(operator IN ('gt','lt','gte','lte','eq')),
  threshold REAL NOT NULL,
  window_seconds INTEGER NOT NULL DEFAULT 300,
  enabled INTEGER NOT NULL DEFAULT 1,
  alert_level TEXT NOT NULL CHECK(alert_level IN ('info','warning','critical')),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_metric_rule_enabled ON metric_rule(enabled);

-- ============================================================
-- P0 审计日志与导出
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  target TEXT NOT NULL,
  target_type TEXT,
  target_ip TEXT,
  reason TEXT,
  result TEXT NOT NULL CHECK(result IN ('success','failed')),
  error_message TEXT,
  trace_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_audit_log_actor ON audit_log(actor);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_trace_id ON audit_log(trace_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_result ON audit_log(result);

CREATE TABLE IF NOT EXISTS audit_export_job (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  filters_json TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('pending','running','completed','failed')),
  file_uri TEXT,
  file_hash TEXT,
  row_count INTEGER,
  error_message TEXT,
  requested_by TEXT NOT NULL,
  reason TEXT,
  progress REAL DEFAULT 0,
  trace_id TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_audit_export_status ON audit_export_job(status);
CREATE INDEX IF NOT EXISTS idx_audit_export_requested_by ON audit_export_job(requested_by);
CREATE INDEX IF NOT EXISTS idx_audit_export_created_at ON audit_export_job(created_at);
