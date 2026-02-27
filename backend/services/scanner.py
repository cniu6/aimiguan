"""Scanner Service - 扫描任务调度"""

import os
import asyncio
import json
import xml.etree.ElementTree as ET
import subprocess
import tempfile
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from core.database import SessionLocal, ScanTask, ScanFinding, Asset
from services.ai_engine import ai_engine
from services.audit_service import AuditService


class NmapParser:
    """Nmap XML 结果解析器"""

    @staticmethod
    def parse_xml(xml_content: str) -> List[Dict[str, Any]]:
        """解析 Nmap XML 输出为结构化数据"""
        findings = []

        try:
            root = ET.fromstring(xml_content)

            for host in root.findall(".//host"):
                host_addr = host.find('.//address[@addrtype="ipv4"]')
                if host_addr is None:
                    host_addr = host.find(".//address")

                ip = (
                    host_addr.get("addr", "unknown")
                    if host_addr is not None
                    else "unknown"
                )

                # 解析主机状态
                status = host.find("status")
                host_state = (
                    status.get("state", "unknown") if status is not None else "unknown"
                )

                if host_state != "up":
                    continue

                # 解析端口信息
                for port in host.findall(".//port"):
                    port_id = port.get("portid", "0")
                    protocol = port.get("protocol", "tcp")

                    # 端口状态
                    port_state_elem = port.find("state")
                    port_state = (
                        port_state_elem.get("state", "unknown")
                        if port_state_elem is not None
                        else "unknown"
                    )

                    if port_state != "open":
                        continue

                    # 服务信息
                    service_elem = port.find("service")
                    service_name = "unknown"
                    service_version = ""
                    service_product = ""

                    if service_elem is not None:
                        service_name = service_elem.get("name", "unknown")
                        service_version = service_elem.get("version", "")
                        service_product = service_elem.get("product", "")

                    # 构建版本字符串
                    version_str = service_product
                    if service_version:
                        version_str += (
                            f" {service_version}" if version_str else service_version
                        )

                    # 脚本输出（漏洞检测）
                    scripts = []
                    for script in port.findall(".//script"):
                        script_id = script.get("id", "")
                        script_output = script.get("output", "")
                        if script_id and script_output:
                            scripts.append(
                                {
                                    "id": script_id,
                                    "output": script_output[:500],  # 限制长度
                                }
                            )

                    finding = {
                        "ip": ip,
                        "port": int(port_id) if port_id.isdigit() else 0,
                        "protocol": protocol,
                        "service": service_name,
                        "version": version_str.strip() or "unknown",
                        "state": port_state,
                        "scripts": scripts,
                    }
                    findings.append(finding)

        except ET.ParseError as e:
            print(f"XML parse error: {e}")
        except Exception as e:
            print(f"Parse error: {e}")

        return findings

    @staticmethod
    def determine_severity(service: str, port: int, scripts: List[Dict]) -> str:
        """根据服务、端口和脚本输出确定严重级别"""
        # 高危端口
        high_risk_ports = [21, 23, 3389, 445, 135, 139, 593]  # FTP, Telnet, RDP, SMB等
        # 中危端口
        medium_risk_ports = [
            22,
            25,
            53,
            110,
            143,
            3306,
            5432,
            6379,
            27017,
        ]  # SSH, SMTP, DNS, DB等

        # 检查脚本输出中是否有漏洞关键词
        vuln_keywords = ["vulnerable", "cve", "exploit", "overflow", "injection"]
        script_text = " ".join([s.get("output", "").lower() for s in scripts])
        has_vuln = any(kw in script_text for kw in vuln_keywords)

        if has_vuln:
            return "HIGH"
        elif port in high_risk_ports:
            return "HIGH"
        elif port in medium_risk_ports:
            return "MEDIUM"
        elif port < 1024:  # 系统端口
            return "LOW"
        else:
            return "INFO"


class Scanner:
    """扫描器 - 调度和执行扫描任务"""

    def __init__(self):
        self.max_concurrent = int(os.getenv("SCANNER_MAX_CONCURRENT", "3"))
        self.running_tasks: Dict[int, asyncio.Task] = {}
        self.output_dir = Path(os.getenv("SCAN_OUTPUT_DIR", "./scan_outputs"))
        self.output_dir.mkdir(exist_ok=True)

    async def execute_scan(
        self,
        task_id: int,
        target: str,
        tool_name: str = "nmap",
        profile: Optional[str] = None,
        script_set: Optional[str] = None,
    ) -> Dict[str, Any]:
        """执行扫描任务"""
        if tool_name == "nmap":
            return await self._execute_nmap(task_id, target, profile, script_set)
        else:
            raise ValueError(f"Unsupported scan tool: {tool_name}")

    async def _execute_nmap(
        self,
        task_id: int,
        target: str,
        profile: Optional[str] = None,
        script_set: Optional[str] = None,
    ) -> Dict[str, Any]:
        """执行 Nmap 扫描（真实实现）"""

        # 构建输出文件路径
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"scan_{task_id}_{timestamp}.xml"

        # 构建 nmap 命令
        cmd = ["nmap", "-oX", str(output_file)]

        # 根据 profile 选择扫描参数
        if profile == "quick":
            cmd.extend(["-sS", "-T4", "-F"])  # 快速扫描，仅常用端口
        elif profile == "comprehensive":
            cmd.extend(["-sS", "-sV", "-O", "-A", "-T4", "-p-"])  # 全面扫描
        elif profile == "vuln":
            cmd.extend(["-sV", "--script=vuln", "-T4"])  # 漏洞扫描
        else:
            # 默认扫描
            cmd.extend(["-sS", "-sV", "-T4", "-p", "1-1000"])

        # 添加脚本
        if script_set:
            cmd.extend(["--script", script_set])

        # 添加目标
        cmd.append(target)

        # 执行扫描
        try:
            # 使用 asyncio.create_subprocess_exec 异步执行
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="ignore")[:500]
                return {
                    "task_id": task_id,
                    "target": target,
                    "status": "failed",
                    "error": f"Nmap execution failed: {error_msg}",
                    "findings": [],
                }

            # 读取 XML 输出
            if output_file.exists():
                xml_content = output_file.read_text(encoding="utf-8")
                findings = NmapParser.parse_xml(xml_content)

                return {
                    "task_id": task_id,
                    "target": target,
                    "status": "completed",
                    "output_file": str(output_file),
                    "findings": findings,
                    "raw_output": xml_content[:10000],  # 限制返回大小
                }
            else:
                return {
                    "task_id": task_id,
                    "target": target,
                    "status": "failed",
                    "error": "Output file not generated",
                    "findings": [],
                }

        except FileNotFoundError:
            return {
                "task_id": task_id,
                "target": target,
                "status": "failed",
                "error": "nmap command not found. Please install nmap.",
                "findings": [],
            }
        except Exception as e:
            return {
                "task_id": task_id,
                "target": target,
                "status": "failed",
                "error": str(e)[:500],
                "findings": [],
            }

    async def schedule_scan(
        self,
        task_id: int,
        target: str,
        tool_name: str = "nmap",
        profile: Optional[str] = None,
        script_set: Optional[str] = None,
        operator: Optional[str] = None,
    ) -> None:
        """调度扫描任务（异步执行，带完整状态机）"""
        if len(self.running_tasks) >= self.max_concurrent:
            raise RuntimeError("Too many concurrent scans")

        # 创建异步任务
        task = asyncio.create_task(
            self._run_scan_workflow(
                task_id, target, tool_name, profile, script_set, operator
            )
        )
        self.running_tasks[task_id] = task

        # 清理回调
        def cleanup(t):
            self.running_tasks.pop(task_id, None)

        task.add_done_callback(cleanup)

    async def _run_scan_workflow(
        self,
        task_id: int,
        target: str,
        tool_name: str,
        profile: Optional[str],
        script_set: Optional[str],
        operator: Optional[str],
    ) -> Dict[str, Any]:
        """完整的扫描工作流（含状态机推进）"""
        db = SessionLocal()
        trace_id = f"scan_{task_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        try:
            # 1. 更新状态为 DISPATCHED
            scan_task = db.query(ScanTask).filter(ScanTask.id == task_id).first()
            if not scan_task:
                return {"error": "Task not found"}

            scan_task.state = "DISPATCHED"
            scan_task.trace_id = trace_id
            db.commit()

            # 2. 更新状态为 RUNNING
            scan_task.state = "RUNNING"
            scan_task.started_at = datetime.utcnow()
            db.commit()

            # 记录审计
            AuditService.log(
                db=db,
                actor=operator or "system",
                action="scan_start",
                target=f"task:{task_id}",
                target_type="scan_task",
                result="success",
                trace_id=trace_id,
                reason=f"开始扫描目标: {target}",
            )

            # 3. 执行扫描
            result = await self.execute_scan(
                task_id, target, tool_name, profile, script_set
            )

            if result["status"] == "failed":
                # 扫描失败
                scan_task.state = "FAILED"
                scan_task.error_message = result.get("error", "Unknown error")
                scan_task.ended_at = datetime.utcnow()
                db.commit()

                AuditService.log(
                    db=db,
                    actor=operator or "system",
                    action="scan_failed",
                    target=f"task:{task_id}",
                    target_type="scan_task",
                    result="failed",
                    trace_id=trace_id,
                    reason=result.get("error", "Unknown error"),
                )

                return result

            # 4. 解析结果并入库
            findings = result.get("findings", [])
            scan_task.raw_output_path = result.get("output_file", "")

            # 保存发现项
            for finding in findings:
                severity = NmapParser.determine_severity(
                    finding.get("service", ""),
                    finding.get("port", 0),
                    finding.get("scripts", []),
                )

                # 构建证据字符串
                evidence = f"Port: {finding.get('port')}/{finding.get('protocol')}\n"
                evidence += (
                    f"Service: {finding.get('service')} {finding.get('version')}\n"
                )
                if finding.get("scripts"):
                    evidence += "Scripts:\n"
                    for script in finding["scripts"]:
                        evidence += f"  - {script['id']}: {script['output'][:200]}\n"

                scan_finding = ScanFinding(
                    scan_task_id=task_id,
                    asset=target,
                    port=finding.get("port"),
                    service=finding.get("service"),
                    vuln_id=None,  # 可从脚本输出中提取
                    cve=None,  # 可从脚本输出中提取
                    severity=severity,
                    evidence=evidence[:2000],
                    status="NEW",
                    trace_id=trace_id,
                )
                db.add(scan_finding)

            # 5. AI 分析 (记录到日志，不存储到数据库)
            if findings:
                try:
                    ai_analysis = await ai_engine.analyze_scan_result(
                        {
                            "target": target,
                            "findings_count": len(findings),
                            "findings": findings[:10],  # 限制数量
                        }
                    )
                    if ai_analysis:
                        print(f"AI Analysis for task {task_id}: {ai_analysis[:500]}...")
                except Exception as e:
                    print(f"AI analysis error: {e}")
            # 6. 更新状态为 PARSED
            scan_task.state = "PARSED"
            db.commit()

            # 7. 生成报告并更新为 REPORTED
            scan_task.state = "REPORTED"
            scan_task.ended_at = datetime.utcnow()
            db.commit()

            # 记录成功审计
            AuditService.log(
                db=db,
                actor=operator or "system",
                action="scan_completed",
                target=f"task:{task_id}",
                target_type="scan_task",
                result="success",
                trace_id=trace_id,
                reason=f"扫描完成，发现 {len(findings)} 个开放端口/服务",
            )

            return result

        except Exception as e:
            db.rollback()
            # 更新失败状态
            scan_task = db.query(ScanTask).filter(ScanTask.id == task_id).first()
            if scan_task:
                scan_task.state = "FAILED"
                scan_task.error_message = str(e)[:500]
                scan_task.ended_at = datetime.utcnow()
                db.commit()

            AuditService.log(
                db=db,
                actor=operator or "system",
                action="scan_error",
                target=f"task:{task_id}",
                target_type="scan_task",
                result="failed",
                trace_id=trace_id,
                reason=str(e)[:500],
            )

            raise
        finally:
            db.close()

    def get_task_status(self, task_id: int) -> Optional[str]:
        """获取任务状态"""
        if task_id not in self.running_tasks:
            return None

        task = self.running_tasks[task_id]
        if task.done():
            return "completed"
        else:
            return "running"

    async def cancel_scan(self, task_id: int) -> bool:
        """取消扫描任务"""
        if task_id not in self.running_tasks:
            return False

        task = self.running_tasks[task_id]
        task.cancel()

        # 更新数据库状态
        db = SessionLocal()
        try:
            scan_task = db.query(ScanTask).filter(ScanTask.id == task_id).first()
            if scan_task:
                scan_task.state = "FAILED"
                scan_task.error_message = "Cancelled by user"
                db.commit()
        finally:
            db.close()

        return True


# Global instance
scanner = Scanner()
