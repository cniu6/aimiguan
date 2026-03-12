import requests
import json
import re
import urllib3
import threading
import logging
from netmiko import ConnectHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_and_ban(ip, logs, config):
    """
    使用 AI 分析特定 IP 的攻击日志，并根据分析结果决定是否执行封禁。
    """
    ai_config = config.get("ai", {})
    if not ai_config.get("enabled", False):
        return

    api_url = ai_config.get("api_url", "")
    api_key = ai_config.get("api_key", "")
    model = ai_config.get("model", "")
    timeout = ai_config.get("timeout", 60)
    
    if not api_key or not api_url:
        logger.error("AI API 密钥或接口地址 (api_url) 未配置，跳过 AI 分析阶段。")
        return

    # 精简及聚合日志数据，合并重复攻击，大幅缩小 Prompt 体积
    ip_location = ""
    if logs and "ip_location" in logs[0]:
        ip_location = logs[0].get("ip_location", "")
        
    agg_logs = {}
    for log in logs:
        service = log.get("service_name", "未知")
        port = log.get("service_port", "未知")
        ctime = log.get("create_time_str", "")
        
        key = f"{service}_{port}"
        if key not in agg_logs:
            agg_logs[key] = {
                "service": service,
                "port": port,
                "count": 0,
                "times": []
            }
        
        agg_logs[key]["count"] += 1
        if ctime:
            agg_logs[key]["times"].append(ctime)
            
    simplified_logs = []
    for info in agg_logs.values():
        times = sorted(info["times"])
        simplified_logs.append({
            "service_name": info["service"],
            "port": info["port"],
            "attack_count": info["count"],
            "first_seen": times[0] if times else "",
            "last_seen": times[-1] if len(times) > 1 else (times[0] if times else "")
        })
        
    # 限制发送分类的数量，防止极端情况下超出上下文限制
    simplified_logs = simplified_logs[-20:]

    # 准备提示词 (Prompt)
    prompt = f"""
请分析以下来自同一IP ({ip}) 的蜜罐攻击日志。
作为专业的网络安全专家，请判断该IP的攻击行为是否具有高威胁且严重到了需要封禁的程度。

要求：
1. 请简要陈述你的分析理由简单回答不要超过200字。
2. 必须在回复的最后使用特定标签包裹你的最终判断：
   - 如果需要封禁，请输出：<ban>true</ban>
   - 如果不需要封禁，请输出：<ban>false</ban>

攻击源IP: {ip}
源IP归属地: {ip_location}
攻击行为日志明细：
{json.dumps(simplified_logs, ensure_ascii=False, indent=2)}
"""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "/no_think 你是一个专业的安全分析与自动化防御策略分配专家助手。"},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        logger.info(f"正在将 IP [{ip}] 的 {len(logs)} 条日志发送给 AI 进行决断 (超时设置: {timeout}s)...")
        logger.info(f"发送给 AI 的请求体:\n{json.dumps(payload, ensure_ascii=False, indent=2)}")
        response = requests.post(api_url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        result = response.json()
        
        reply = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        logger.info(f"AI 对 IP [{ip}] 的分析回复:\n{reply}")
        
        # 匹配 <ban>true</ban> 或 <ban>false</ban> 标签
        match = re.search(r"<ban>(.*?)</ban>", reply, re.IGNORECASE)
        decision = "false"
        if match:
            decision = match.group(1).strip().lower()
            if decision == "true":
                auto_ban = ai_config.get("auto_ban", False)
                if auto_ban:
                    logger.warning(f"🚨 AI 决断结果: 必须封禁 IP [{ip}]! 准备执行多台交换机访问控制 ACL 更新...")
                    
                    switches = config.get("switches", [])
                    
                    if not switches:
                        logger.error("未在 config.json 中找到 'switches' 配置。")
                        
                    for switch_config in switches:
                        execute_switch_ban(ip, switch_config)
                else:
                    logger.warning(f"🚨 AI 决断结果: 建议封禁 IP [{ip}]，但设定的 'auto_ban' 自动封禁开关未开启，已跳过设备执行。")
            else:
                logger.info(f"ℹ️ AI 决断结果: 无需封禁 IP [{ip}]。")
        else:
            logger.error(f"❌ 无法在 AI 的回复中提取到 <ban> 标签 (IP: {ip})，默认不封禁。")
            
        # 隐藏 <ban> 和 <think> 标签内容并保存到数据库
        clean_reply = re.sub(r'<ban>.*?</ban>|<think>.*?</think>', '', reply, flags=re.IGNORECASE | re.DOTALL).strip()
        from database.models import AiModel
        AiModel.save_analysis(ip, clean_reply, decision)

    except Exception as e:
        logger.error(f"❌ 调用 AI 分析 IP [{ip}] 时发生错误: {e}")

def execute_switch_ban(ip, switch_config):
    """
    通过 Netmiko 登录交换机并配置 ACL 策略封禁指定 IP
    """
    host = switch_config.get("host", "")
    port = switch_config.get("port", 23)
    username = switch_config.get("username", "")
    password = switch_config.get("password", "")
    acl_number = switch_config.get("acl_number", 3000)
    device_type = switch_config.get("device_type")
    
    if not host or not username or not password or not device_type:
        logger.error(f"某台交换机(Switch: {host})的配置不完整。必须包含 host, username, password 和 device_type。")
        return
        
    try:
        logger.info(f"正在通过 Netmiko 连接到交换机 {host}:{port} ({device_type})...")
        device = {
            'device_type': device_type,
            'host': host,
            'username': username,
            'password': password,
            'port': port,
        }
        
        # 建立智能连接，自动处理登录和等待提示符
        net_connect = ConnectHandler(**device)
        
        logger.info(f"成功登录交换机 {host}。正在下发 ACL {acl_number} 封禁 {ip} 的命令集...")
        
        # 定义要执行的策略命令集合
        config_commands = [
            f'acl number {acl_number}',
            f'rule deny ip source {ip} 0'
        ]
        
        # Netmiko 会自动进入系统视图(system-view 或 conf t)并按顺序执行
        output = net_connect.send_config_set(config_commands)
        
        # 尝试保存配置并正常断开
        try:
            net_connect.save_config()
        except:
            pass # 部分设备可能不支持默认的 save_config 命令，不影响下发
            
        net_connect.disconnect()
        
        logger.info(f"✅ 成功在交换机 {host} 的 ACL {acl_number} 中添加了对 IP {ip} 的封禁策略！")
        logger.debug(f"交换机命令行输出记录:\n{output}")
        
    except Exception as e:
        logger.error(f"❌ 自动化封禁 IP {ip} 到交换机时发生异常: {e}")
