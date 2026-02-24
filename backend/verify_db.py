#!/usr/bin/env python3
"""Verify database structure and sample data"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "aimiguard.db"

def main():
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📊 Database Structure Verification")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"\n✅ Database: {DB_PATH}")
    print(f"✅ Total Tables: {len(tables)}\n")
    
    # Core business tables
    core_tables = ['threat_event', 'execution_task', 'scan_task', 'scan_finding', 
                   'asset', 'device', 'credential', 'ai_decision_log']
    
    # RBAC tables
    rbac_tables = ['user', 'role', 'permission', 'user_role', 'role_permission', 'access_audit']
    
    # System tables
    system_tables = ['release_history', 'system_config_snapshot', 'backup_job', 
                     'restore_job', 'security_scan_report', 'alert_event', 
                     'metric_point', 'metric_rule', 'audit_log', 'audit_export_job']
    
    # AI & Integration tables
    ai_tables = ['ai_chat_session', 'ai_chat_message', 'ai_report', 'ai_tts_task',
                 'plugin_registry', 'push_channel', 'firewall_sync_task', 'model_profile']
    
    table_names = [t[0] for t in tables]
    
    def check_tables(category, table_list):
        print(f"📦 {category}:")
        for table in table_list:
            status = "✓" if table in table_names else "✗"
            print(f"  {status} {table}")
        print()
    
    check_tables("Core Business Tables", core_tables)
    check_tables("RBAC Tables", rbac_tables)
    check_tables("System Management Tables", system_tables)
    check_tables("AI & Integration Tables", ai_tables)
    
    # Check sample data
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📋 Sample Data Verification")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    # Users
    cursor.execute("SELECT username, full_name FROM user")
    users = cursor.fetchall()
    print(f"👤 Users ({len(users)}):")
    for username, full_name in users:
        print(f"  • {username} - {full_name}")
    
    # Roles
    cursor.execute("SELECT name, description FROM role")
    roles = cursor.fetchall()
    print(f"\n🔐 Roles ({len(roles)}):")
    for name, desc in roles:
        print(f"  • {name} - {desc}")
    
    # Permissions
    cursor.execute("SELECT COUNT(*) FROM permission")
    perm_count = cursor.fetchone()[0]
    print(f"\n🔑 Permissions: {perm_count}")
    
    # Devices
    cursor.execute("SELECT name, ip, vendor FROM device")
    devices = cursor.fetchall()
    print(f"\n🖥️  Devices ({len(devices)}):")
    for name, ip, vendor in devices:
        print(f"  • {name} ({vendor}) - {ip}")
    
    # Model profiles
    cursor.execute("SELECT model_name, model_type, endpoint FROM model_profile")
    models = cursor.fetchall()
    print(f"\n🤖 Model Profiles ({len(models)}):")
    for name, mtype, endpoint in models:
        print(f"  • {name} ({mtype}) - {endpoint}")
    
    # Release history
    cursor.execute("SELECT version, schema_version, deploy_env, status FROM release_history")
    releases = cursor.fetchall()
    print(f"\n📦 Release History ({len(releases)}):")
    for version, schema_ver, env, status in releases:
        print(f"  • {version} (schema {schema_ver}) - {env} [{status}]")
    
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("✅ Database verification complete!")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    conn.close()

if __name__ == "__main__":
    main()
