"""
Nmap 网络扫描服务
执行 Nmap 扫描并将结果存储到 ScanTask 和 ScanFinding
"""
import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from core.database import ScanTask, ScanFinding, Asset, CollectorConfig, SessionLocal

logger = logging.getLogger(__name__)


class NmapScanner:
    """Nmap 扫描器"""
    
    def __init__(self):
        self.nmap_path: Optional[str] = None
        self.ip_ranges: List[str] = []
        self.scan_interval: int = 604800  # 7天
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
                CollectorConfig.collector_type == "nmap",
                CollectorConfig.enabled == 1
            ).all()
            
            for config in configs:
                if config.config_key == "nmap_path":
                    self.nmap_path = config.config_value
                elif config.config_key == "ip_ranges":
                    self.ip_ranges = json.loads(config.config_value)
                elif config.config_key == "scan_interval":
                    self.scan_interval = int(config.config_value)
                elif config.config_key == "enabled":
                    self.enabled = config.config_value == "true"
        except Exception as e:
            logger.warning(f"加载 Nmap 配置失败: {e}")
        finally:
            db.close()
    
    def save_config(self, nmap_path: str, ip_ranges: List[str], scan_interval: int = 604800, enabled: bool = True):
        """保存配置到数据库"""
        db = SessionLocal()
        try:
            configs = {
                "nmap_path": (nmap_path, 0),
                "ip_ranges": (json.dumps(ip_ranges), 0),
                "scan_interval": (str(scan_interval), 0),
                "enabled": ("true" if enabled else "false", 0)
            }
            
            for key, (value, is_sensitive) in configs.items():
                existing = db.query(CollectorConfig).filter(
                    CollectorConfig.collector_type == "nmap",
                    CollectorConfig.config_key == key
                ).first()
                
                if existing:
                    existing.config_value = value
                    existing.is_sensitive = is_sensitive
                    existing.updated_at = datetime.now(timezone.utc)
                else:
                    new_config = CollectorConfig(
                        collector_type="nmap",
                        config_key=key,
                        config_value=value,
                        is_sensitive=is_sensitive,
                        enabled=1
                    )
                    db.add(new_config)
            
            db.commit()
            self._load_config()
        finally:
            db.close()
    
    def execute_nmap_scan(self, target: str, arguments: str, output_path: str) -> bool:
        """
        执行 Nmap 扫描
        
        Args:
            target: 扫描目标（IP/CIDR/域名）
            arguments: Nmap 参数
            output_path: XML 输出路径
        
        Returns:
            是否成功
        """
        if not self.nmap_path or not os.path.exists(self.nmap_path):
            logger.error(f"Nmap 路径不存在: {self.nmap_path}")
            return False
        
        # 构建命令
        cmd = [
            self.nmap_path,
            target,
            "-oX", output_path,  # XML 输出
        ] + arguments.split()
        
        try:
            logger.info(f"执行 Nmap 扫描: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,  # 1小时超时
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode != 0:
                logger.error(f"Nmap 扫描失败: {result.stderr}")
                return False
            
            logger.info(f"Nmap 扫描完成，输出: {output_path}")
            return True
        
        except subprocess.TimeoutExpired:
            logger.error("Nmap 扫描超时")
            return False
        except Exception as e:
            logger.error(f"Nmap 扫描异常: {e}", exc_info=True)
            return False
    
    def parse_nmap_xml(self, xml_path: str) -> List[Dict[str, Any]]:
        """
        解析 Nmap XML 输出
        
        Args:
            xml_path: XML 文件路径
        
        Returns:
            主机信息列表
        """
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            hosts_data = []
            
            for host in root.findall('host'):
                # 状态
                status = host.find('status')
                if status is None or status.get('state') != 'up':
                    continue
                
                host_info = {
                    'ip': '',
                    'mac_address': '',
                    'vendor': '',
                    'hostname': '',
                    'state': 'up',
                    'os_type': '',
                    'os_accuracy': '',
                    'open_ports': [],
                    'services': []
                }
                
                # IP 地址
                for addr in host.findall('address'):
                    if addr.get('addrtype') == 'ipv4':
                        host_info['ip'] = addr.get('addr', '')
                    elif addr.get('addrtype') == 'mac':
                        host_info['mac_address'] = addr.get('addr', '')
                        host_info['vendor'] = addr.get('vendor', '')
                
                # 主机名
                hostnames = host.find('hostnames')
                if hostnames is not None:
                    hostname = hostnames.find('hostname')
                    if hostname is not None:
                        host_info['hostname'] = hostname.get('name', '')
                
                # 操作系统
                os_elem = host.find('os')
                if os_elem is not None:
                    osmatch = os_elem.find('osmatch')
                    if osmatch is not None:
                        host_info['os_type'] = osmatch.get('name', '')
                        host_info['os_accuracy'] = osmatch.get('accuracy', '')
                
                # 端口和服务
                ports = host.find('ports')
                if ports is not None:
                    for port in ports.findall('port'):
                        state = port.find('state')
                        if state is not None and state.get('state') == 'open':
                            port_id = int(port.get('portid', 0))
                            host_info['open_ports'].append(port_id)
                            
                            service = port.find('service')
                            if service is not None:
                                service_info = {
                                    'port': port_id,
                                    'protocol': port.get('protocol', 'tcp'),
                                    'service': service.get('name', ''),
                                    'product': service.get('product', ''),
                                    'version': service.get('version', ''),
                                    'extrainfo': service.get('extrainfo', '')
                                }
                                host_info['services'].append(service_info)
                
                if host_info['ip']:
                    hosts_data.append(host_info)
            
            return hosts_data
        
        except Exception as e:
            logger.error(f"解析 Nmap XML 失败: {e}", exc_info=True)
            return []
    
    def save_scan_results(self, scan_task_id: int, hosts_data: List[Dict[str, Any]], db: Session, trace_id: str) -> int:
        """
        保存扫描结果到数据库
        
        Args:
            scan_task_id: 扫描任务ID
            hosts_data: 主机数据列表
            db: 数据库会话
            trace_id: 追踪ID
        
        Returns:
            保存的主机数量
        """
        count = 0
        
        for host in hosts_data:
            try:
                # 为每个主机创建一个 ScanFinding（主机发现）
                finding = ScanFinding(
                    scan_task_id=scan_task_id,
                    asset=host['ip'],
                    mac_address=host.get('mac_address', ''),
                    vendor=host.get('vendor', ''),
                    hostname=host.get('hostname', ''),
                    state=host.get('state', 'up'),
                    os_type=host.get('os_type', ''),
                    os_accuracy=host.get('os_accuracy', ''),
                    evidence=json.dumps({
                        'open_ports': host.get('open_ports', []),
                        'services': host.get('services', [])
                    }, ensure_ascii=False),
                    status="NEW",
                    trace_id=trace_id
                )
                db.add(finding)
                count += 1
                
                # 为每个开放端口创建一个 ScanFinding（服务发现）
                for service in host.get('services', []):
                    service_finding = ScanFinding(
                        scan_task_id=scan_task_id,
                        asset=host['ip'],
                        port=service['port'],
                        service=f"{service['service']} {service.get('product', '')} {service.get('version', '')}".strip(),
                        evidence=json.dumps(service, ensure_ascii=False),
                        status="NEW",
                        trace_id=trace_id
                    )
                    db.add(service_finding)
            
            except Exception as e:
                logger.error(f"保存主机 {host.get('ip')} 失败: {e}", exc_info=True)
                continue
        
        db.commit()
        return count
    
    def get_win7_hosts(self, scan_task_id: int, db: Session) -> List[Dict[str, Any]]:
        """
        筛选 Win7 主机（包含 Windows 7 和 Windows Server 2008 R2）
        
        Args:
            scan_task_id: 扫描任务ID
            db: 数据库会话
        
        Returns:
            Win7 主机列表
        """
        findings = db.query(ScanFinding).filter(
            ScanFinding.scan_task_id == scan_task_id,
            ScanFinding.os_type.isnot(None)
        ).all()
        
        win7_hosts = []
        for finding in findings:
            os_type = finding.os_type or ""
            os_lower = os_type.lower()
            
            # 识别 Win7 和 2008 R2
            if any(keyword in os_lower for keyword in ['windows 7', '2008 r2', 'windows 2008']):
                try:
                    evidence = json.loads(finding.evidence) if finding.evidence else {}
                    win7_hosts.append({
                        'ip': finding.asset,
                        'mac_address': finding.mac_address,
                        'vendor': finding.vendor,
                        'hostname': finding.hostname,
                        'state': finding.state,
                        'os_type': finding.os_type,
                        'os_accuracy': finding.os_accuracy,
                        'open_ports': evidence.get('open_ports', []),
                        'services': evidence.get('services', [])
                    })
                except Exception as e:
                    logger.error(f"解析 Win7 主机数据失败: {e}")
                    continue
        
        return win7_hosts
    
    async def scan_target(self, target: str, profile: str, db: Session, trace_id: str) -> Dict[str, Any]:
        """
        扫描单个目标
        
        Args:
            target: 扫描目标
            profile: 扫描配置（quick/default/comprehensive/vuln）
            db: 数据库会话
            trace_id: 追踪ID
        
        Returns:
            扫描结果
        """
        self._ensure_config_loaded()
        
        # 扫描配置映射
        profiles = {
            "quick": "-sS -T4 -F",
            "default": "-sS -sV -T4 -p 1-1000",
            "comprehensive": "-sS -sV -O -A -T4 -p-",
            "vuln": "-sV --script=vuln -T4"
        }
        
        arguments = profiles.get(profile, profiles["default"])
        
        # 查找或创建 Asset
        asset = db.query(Asset).filter(Asset.target == target).first()
        if not asset:
            asset = Asset(
                target=target,
                target_type="IP" if "." in target and "/" not in target else "CIDR",
                enabled=1
            )
            db.add(asset)
            db.commit()
            db.refresh(asset)
        
        # 创建 ScanTask
        scan_task = ScanTask(
            asset_id=asset.id,
            target=target,
            target_type=asset.target_type,
            tool_name="nmap",
            profile=profile,
            state="RUNNING",
            trace_id=trace_id,
            started_at=datetime.now(timezone.utc)
        )
        db.add(scan_task)
        db.commit()
        db.refresh(scan_task)
        
        # 输出路径
        output_dir = "scan_outputs"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"scan_{scan_task.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml")
        
        try:
            # 执行扫描
            success = self.execute_nmap_scan(target, arguments, output_path)
            
            if not success:
                scan_task.state = "FAILED"
                scan_task.error_message = "Nmap 扫描执行失败"
                scan_task.ended_at = datetime.now(timezone.utc)
                db.commit()
                return {"success": False, "message": "扫描执行失败", "task_id": scan_task.id}
            
            # 解析结果
            hosts_data = self.parse_nmap_xml(output_path)
            
            if not hosts_data:
                scan_task.state = "COMPLETED"
                scan_task.raw_output_path = output_path
                scan_task.ended_at = datetime.now(timezone.utc)
                db.commit()
                return {"success": True, "message": "扫描完成，未发现主机", "task_id": scan_task.id, "hosts_count": 0}
            
            # 保存结果
            count = self.save_scan_results(scan_task.id, hosts_data, db, trace_id)
            
            # 更新任务状态
            scan_task.state = "COMPLETED"
            scan_task.raw_output_path = output_path
            scan_task.ended_at = datetime.now(timezone.utc)
            db.commit()
            
            logger.info(f"[{trace_id}] 扫描完成，发现 {count} 个主机")
            
            return {
                "success": True,
                "message": f"扫描完成，发现 {count} 个主机",
                "task_id": scan_task.id,
                "hosts_count": count,
                "output_path": output_path
            }
        
        except Exception as e:
            logger.error(f"[{trace_id}] 扫描失败: {e}", exc_info=True)
            scan_task.state = "FAILED"
            scan_task.error_message = str(e)
            scan_task.ended_at = datetime.now(timezone.utc)
            db.commit()
            return {"success": False, "message": str(e), "task_id": scan_task.id}


# 全局单例
nmap_scanner = NmapScanner()
