import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, "aimiguard.db")

def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库表结构"""
    conn = get_connection()
    cursor = conn.cursor()

    # ================= Nmap网络扫描相关表 =================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT NOT NULL,
            ip_ranges TEXT,
            arguments TEXT,
            hosts_count INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hosts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER NOT NULL,
            ip TEXT NOT NULL,
            mac_address TEXT,
            vendor TEXT,
            hostname TEXT,
            state TEXT,
            os_type TEXT,
            os_accuracy TEXT,
            os_tags TEXT,
            open_ports TEXT,
            services TEXT,
            scan_time TEXT,
            last_seen TEXT,
            FOREIGN KEY (scan_id) REFERENCES scans(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mac_address TEXT UNIQUE,
            current_ip TEXT,
            hostname TEXT,
            vendor TEXT,
            state TEXT,
            os_type TEXT,
            os_accuracy TEXT,
            os_tags TEXT,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            last_scan_id INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asset_ip_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id INTEGER NOT NULL,
            ip TEXT NOT NULL,
            scan_id INTEGER,
            seen_time TEXT NOT NULL,
            UNIQUE(asset_id, ip, scan_id),
            FOREIGN KEY (asset_id) REFERENCES assets(id)
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_assets_mac ON assets(mac_address)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_assets_ip ON assets(current_ip)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_asset_ip_history_asset ON asset_ip_history(asset_id)')

    # ================= 漏洞扫描相关表 =================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vuln_scan_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mac_address TEXT NOT NULL,
            ip TEXT NOT NULL,
            vuln_name TEXT NOT NULL,
            vuln_result TEXT,
            vuln_details TEXT,
            os_tags TEXT,
            scan_time TEXT NOT NULL,
            UNIQUE(mac_address, vuln_name)
        )
    ''')
    
    # ================= HFish蜜罐攻击日志相关表 =================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attack_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attack_ip TEXT,
            ip_location TEXT,
            client_id TEXT,
            client_name TEXT,
            service_name TEXT,
            service_port TEXT,
            threat_level TEXT,
            create_time_str TEXT,
            create_time_timestamp INTEGER
        )
    ''')
    
    # ================= AI 分析记录表 =================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_analysis_logs (
            ip TEXT PRIMARY KEY,
            analysis_text TEXT,
            decision TEXT,
            scan_time TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database aimiguard.db initialized.")
