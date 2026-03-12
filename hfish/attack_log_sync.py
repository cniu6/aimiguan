import urllib.request
import json
import sqlite3
import time
from datetime import datetime
import os
import sys
import urllib3
import requests
import threading

# 添加项目根目录到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_connection
from database.models import HFishModel

# 配置文件路径 (从程序所在目录的上一级读取)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")


# ==================== 配置加载 ====================

def load_config():
    """加载配置文件"""
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


# ==================== API 获取 ====================

def timestamp_to_time(timestamp):
    """时间戳转可读时间"""
    if timestamp == 0:
        return "N/A"
    if timestamp > 10000000000:
        timestamp = timestamp / 1000
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


def get_attack_logs(start_time, end_time, host_port, api_key):
    """
    获取攻击详情列表

    参数:
        start_time: 开始时间戳
        end_time: 结束时间戳 (0 表示最新时间)
        host_port: 主机地址和端口，如 "127.0.0.1:4433"
        api_key: API密钥

    返回:
        处理后的攻击详情列表
    """
    url = f"https://{host_port}/api/v1/attack/detail?api_key={api_key}"

    payload = json.dumps({
        "start_time": start_time,
        "end_time": end_time,
        "page_no": 1,
        "page_size": 1000,
        "intranet": -1,
        "threat_label": [],
        "client_id": [],
        "service_name": [],
        "info_confirm": "0"
    })

    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, headers=headers, data=payload, verify=False, timeout=30)
        response.raise_for_status()
        data = response.json()

        # 列表处理
        if "data" in data and "detail_list" in data.get("data", {}):
            detail_list = data["data"]["detail_list"]

            for item in detail_list:
                # 1. 时间戳转换
                if "create_time" in item:
                    item["create_time_str"] = timestamp_to_time(item["create_time"])
                    del item["create_time"]

                # 2. 删除多余字段
                for key in ["attack_info", "threat_name", "threat_label", "threat_level"]:
                    item.pop(key, None)

            return detail_list

        return []

    except Exception as e:
        print(f"请求错误: {e}")
        import traceback
        traceback.print_exc()
        return []



# ==================== 主程序 ====================

def main():
    """主函数"""
    import argparse
    import signal
    import sys

    parser = argparse.ArgumentParser(description='HFish攻击日志同步工具')
    parser.add_argument('--host', type=str, help='HFish API地址 (如 127.0.0.1:4433)')
    parser.add_argument('--key', type=str, help='HFish API密钥')
    parser.add_argument('--interval', '-i', type=int, help='同步间隔(秒)')
    parser.add_argument('--once', '-o', action='store_true', help='只同步一次，不循环')
    args = parser.parse_args()

    print(f"[{datetime.now()}] 程序启动")

    # 加载配置
    raw_config = load_config()
    hfish_config = raw_config.get("hfish", {}).copy()

    # 命令行参数覆盖配置
    if args.host:
        hfish_config["host_port"] = args.host
    if args.key:
        hfish_config["api_key"] = args.key
    if args.interval:
        hfish_config["sync_interval"] = args.interval

    host_port = hfish_config.get("host_port", "127.0.0.1:4433")
    api_key = hfish_config.get("api_key", "")
    interval = hfish_config.get("sync_interval", 60)

    print(f"[{datetime.now()}] 配置加载: host={host_port}, interval={interval}秒")

    # 退出信号处理
    def signal_handler(sig, frame):
        print(f"\n[{datetime.now()}] 收到退出信号，正在关闭...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    def sync_once():
        """执行一次同步"""
        try:
            last_timestamp = HFishModel.get_last_timestamp()
            if last_timestamp == 0:
                start_time = 0
            else:
                start_time = last_timestamp

            print(f"[{datetime.now()}] 开始同步，从时间戳 {start_time} 开始")

            logs = get_attack_logs(start_time, 0, host_port, api_key)

            if logs:
                new_count = HFishModel.save_logs(logs)
                print(f"[{datetime.now()}] 同步完成: 获取 {len(logs)} 条, 新增 {new_count} 条")
                
                # 开始分组和调用 AI 分析
                try:
                    from hfish.ai_analyzer import analyze_and_ban
                    ip_logs = {}
                    for log in logs:
                        ip = log.get("attack_ip")
                        if ip:
                            if ip not in ip_logs:
                                ip_logs[ip] = []
                            ip_logs[ip].append(log)
                            
                    for ip, ip_log_list in ip_logs.items():
                        # 新建线程执行 AI 判定，避免阻塞全局同步日志任务
                        threading.Thread(target=analyze_and_ban, args=(ip, ip_log_list, raw_config), daemon=True).start()
                except Exception as e:
                    print(f"[{datetime.now()}] 调度 AI 分析线程时发生异常: {e}")
            else:
                print(f"[{datetime.now()}] 无新数据")

        except Exception as e:
            print(f"[{datetime.now()}] 同步错误: {e}")

    if args.once:
        sync_once()
    else:
        while True:
            sync_once()
            print(f"[{datetime.now()}] 等待 {interval} 秒后进行下一次同步")
            time.sleep(interval)


if __name__ == "__main__":
    main()
