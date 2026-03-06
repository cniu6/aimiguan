"""
HFish 蜜罐数据采集服务
从 HFish API 拉取攻击日志并转换为 ThreatEvent
"""
import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import urllib3
import requests
from sqlalchemy.orm import Session

from core.database import ThreatEvent, CollectorConfig, SessionLocal

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class HFishCollector:
    """HFish 数据采集器"""
    
    def __init__(self):
        self.host_port: Optional[str] = None
        self.api_key: Optional[str] = None
        self.sync_interval: int = 60
        self.enabled: bool = False
        self._config_loaded: bool = False
    
    def _ensure_config_loaded(self):
        """懒加载配置（仅在首次使用时加载）"""
        if self._config_loaded:
            return
        self._load_config()
        self._config_loaded = True
    
    def _load_config(self):
        """从数据库加载配置"""
        db = SessionLocal()
        try:
            configs = db.query(CollectorConfig).filter(
                CollectorConfig.collector_type == "hfish",
                CollectorConfig.enabled == 1
            ).all()
            
            for config in configs:
                if config.config_key == "host_port":
                    self.host_port = config.config_value
                elif config.config_key == "api_key":
                    self.api_key = config.config_value
                elif config.config_key == "sync_interval":
                    self.sync_interval = int(config.config_value)
                elif config.config_key == "enabled":
                    self.enabled = config.config_value == "true"
        except Exception as e:
            logger.warning(f"加载 HFish 配置失败: {e}")
        finally:
            db.close()
    
    def save_config(self, host_port: str, api_key: str, sync_interval: int = 60, enabled: bool = True):
        """保存配置到数据库"""
        db = SessionLocal()
        try:
            configs = {
                "host_port": (host_port, 0),
                "api_key": (api_key, 1),  # 敏感信息
                "sync_interval": (str(sync_interval), 0),
                "enabled": ("true" if enabled else "false", 0)
            }
            
            for key, (value, is_sensitive) in configs.items():
                existing = db.query(CollectorConfig).filter(
                    CollectorConfig.collector_type == "hfish",
                    CollectorConfig.config_key == key
                ).first()
                
                if existing:
                    existing.config_value = value
                    existing.is_sensitive = is_sensitive
                    existing.updated_at = datetime.now(timezone.utc)
                else:
                    new_config = CollectorConfig(
                        collector_type="hfish",
                        config_key=key,
                        config_value=value,
                        is_sensitive=is_sensitive,
                        enabled=1
                    )
                    db.add(new_config)
            
            db.commit()
            self._load_config()  # 重新加载配置
        finally:
            db.close()
    
    @staticmethod
    def _timestamp_to_datetime(timestamp: Any) -> Optional[datetime]:
        """时间戳转 datetime"""
        if not timestamp or timestamp == 0:
            return None
        try:
            ts = int(timestamp)
            if ts > 10000000000:  # 毫秒级时间戳
                ts = ts / 1000
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (ValueError, TypeError):
            return None
    
    def fetch_attack_logs(self, start_time: int = 0, end_time: int = 0) -> List[Dict[str, Any]]:
        """
        从 HFish API 获取攻击日志
        
        Args:
            start_time: 开始时间戳（秒）
            end_time: 结束时间戳（秒，0表示最新）
        
        Returns:
            攻击日志列表
        """
        if not self.host_port or not self.api_key:
            logger.error("HFish 配置未设置")
            return []
        
        url = f"https://{self.host_port}/api/v1/attack/detail?api_key={self.api_key}"
        
        payload = {
            "start_time": start_time,
            "end_time": end_time,
            "page_no": 1,
            "page_size": 1000,
            "intranet": -1,
            "threat_label": [],
            "client_id": [],
            "service_name": [],
            "info_confirm": "0"
        }
        
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(payload),
                verify=False,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != 200:
                logger.error(f"HFish API 错误: {data.get('msg', '未知错误')}")
                return []
            
            # 提取详情列表
            if "data" in data and "detail_list" in data.get("data", {}):
                return data["data"]["detail_list"]
            
            return []
        
        except Exception as e:
            logger.error(f"HFish API 请求失败: {e}", exc_info=True)
            return []
    
    def _build_event_id(self, log: Dict[str, Any]) -> str:
        """构建唯一事件ID（用于去重）"""
        key_parts = [
            log.get("attack_ip", ""),
            log.get("service_name", ""),
            log.get("service_port", ""),
            str(log.get("create_time", ""))
        ]
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _map_threat_level_to_score(self, threat_level: str) -> int:
        """威胁等级映射为 AI 评分"""
        mapping = {
            "高危": 80,
            "中危": 50,
            "低危": 20,
            "high": 80,
            "medium": 50,
            "low": 20
        }
        return mapping.get(threat_level, 50)
    
    def ingest_logs(self, logs: List[Dict[str, Any]], db: Session, trace_id: str) -> int:
        """
        将 HFish 日志转换为 ThreatEvent 并入库
        
        Args:
            logs: HFish 日志列表
            db: 数据库会话
            trace_id: 追踪ID
        
        Returns:
            新增事件数量
        """
        if not logs:
            return 0
        
        count = 0
        for log in logs:
            try:
                # 构建唯一事件ID
                event_id = self._build_event_id(log)
                
                # 检查是否已存在
                existing = db.query(ThreatEvent).filter(
                    ThreatEvent.source_event_id == event_id
                ).first()
                
                if existing:
                    continue  # 跳过重复事件
                
                # 转换时间戳
                create_time = self._timestamp_to_datetime(log.get("create_time"))
                
                # 创建 ThreatEvent
                event = ThreatEvent(
                    ip=log.get("attack_ip", ""),
                    source="hfish",
                    source_vendor="hfish",
                    source_type="honeypot",
                    source_event_id=event_id,
                    attack_count=1,
                    asset_ip=log.get("client_ip", ""),
                    service_name=log.get("service_name", ""),
                    service_type=log.get("service_type", ""),
                    service_port=str(log.get("service_port", "")),
                    threat_label=log.get("threat_level", ""),
                    ip_location=log.get("ip_location", ""),
                    client_id=log.get("client_id", ""),
                    client_name=log.get("client_name", ""),
                    ai_score=self._map_threat_level_to_score(log.get("threat_level", "")),
                    status="PENDING",
                    trace_id=trace_id,
                    raw_payload=json.dumps(log, ensure_ascii=False),
                    created_at=create_time or datetime.now(timezone.utc)
                )
                
                db.add(event)
                count += 1
            
            except Exception as e:
                logger.error(f"处理 HFish 日志失败: {e}", exc_info=True)
                continue
        
        db.commit()
        return count
    
    def get_last_sync_timestamp(self, db: Session) -> int:
        """获取最后同步的时间戳"""
        last_event = db.query(ThreatEvent).filter(
            ThreatEvent.source == "hfish"
        ).order_by(ThreatEvent.created_at.desc()).first()
        
        if last_event and last_event.created_at:
            return int(last_event.created_at.timestamp())
        return 0
    
    async def sync_once(self, trace_id: str) -> Dict[str, Any]:
        """
        执行一次同步
        
        Args:
            trace_id: 追踪ID
        
        Returns:
            同步结果
        """
        self._ensure_config_loaded()
        
        if not self.enabled:
            return {"success": False, "message": "HFish 采集器未启用"}
        
        db = SessionLocal()
        try:
            # 获取最后同步时间戳
            last_timestamp = self.get_last_sync_timestamp(db)
            
            logger.info(f"[{trace_id}] 开始 HFish 同步，从时间戳 {last_timestamp} 开始")
            
            # 拉取日志
            logs = self.fetch_attack_logs(start_time=last_timestamp)
            
            if not logs:
                logger.info(f"[{trace_id}] 无新数据")
                return {"success": True, "message": "无新数据", "count": 0}
            
            # 入库
            count = self.ingest_logs(logs, db, trace_id)
            
            logger.info(f"[{trace_id}] HFish 同步完成，新增 {count} 条事件")
            
            return {
                "success": True,
                "message": f"同步完成，新增 {count} 条事件",
                "count": count,
                "total_fetched": len(logs)
            }
        
        except Exception as e:
            logger.error(f"[{trace_id}] HFish 同步失败: {e}", exc_info=True)
            return {"success": False, "message": str(e)}
        
        finally:
            db.close()


# 全局单例
hfish_collector = HFishCollector()
