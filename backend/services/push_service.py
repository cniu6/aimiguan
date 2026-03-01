"""推送服务 - 支持多种告警通道"""
import json
import httpx
from typing import Optional
from sqlalchemy.orm import Session
from backend.core.database import PushChannel


class PushService:
    """推送服务"""
    
    @staticmethod
    async def send_alert(db: Session, channel_id: int, message: str) -> bool:
        """发送告警消息
        
        Args:
            db: 数据库会话
            channel_id: 推送通道 ID
            message: 消息内容
            
        Returns:
            bool: 发送是否成功
        """
        channel = db.query(PushChannel).filter(PushChannel.id == channel_id).first()
        if not channel or not channel.enabled:
            return False
        
        try:
            if channel.channel_type == "webhook":
                return await PushService._send_webhook(channel, message)
            elif channel.channel_type == "wecom":
                return await PushService._send_wecom(channel, message)
            else:
                return False
        except Exception:
            return False
    
    @staticmethod
    async def _send_webhook(channel: PushChannel, message: str) -> bool:
        """发送 Webhook 推送"""
        config = json.loads(channel.config_json) if channel.config_json else {}
        method = config.get("method", "POST").upper()
        headers = config.get("headers", {"Content-Type": "application/json"})
        
        payload = {"message": message, "channel": channel.channel_name}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            if method == "POST":
                resp = await client.post(channel.target, json=payload, headers=headers)
            else:
                resp = await client.get(channel.target, params=payload, headers=headers)
            return resp.status_code < 400
    
    @staticmethod
    async def _send_wecom(channel: PushChannel, message: str) -> bool:
        """发送企业微信机器人推送"""
        payload = {
            "msgtype": "text",
            "text": {"content": message}
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(channel.target, json=payload)
            if resp.status_code == 200:
                result = resp.json()
                return result.get("errcode") == 0
            return False
