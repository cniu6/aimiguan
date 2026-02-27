"""MCP Client Service - MCP 工具调用"""

import os
import json
import asyncio
from typing import Dict, Any, Optional, List
import httpx
from datetime import datetime

from core.database import SessionLocal, Device, Credential, ExecutionTask
from services.audit_service import AuditService


class MCPClient:
    """MCP 客户端 - 调用 MCP 工具执行交换机操作

    支持两种模式:
    - http: 通过 HTTP API 调用外部 MCP 服务器
    - stdio: 通过子进程调用本地 MCP 工具
    - mock: 模拟模式（用于测试）
    """

    def __init__(self):
        self.mode = os.getenv("MCP_MODE", "mock")  # mock, http, stdio
        self.server_url = os.getenv("MCP_SERVER_URL", "http://localhost:3000")
        self.server_name = os.getenv("MCP_SERVER_NAME", "switch-controller")
        self.timeout = float(os.getenv("MCP_TIMEOUT", "30.0"))
        self.http_client = httpx.AsyncClient(timeout=self.timeout)

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用 MCP 工具"""
        if self.mode == "mock":
            return await self._call_mock(tool_name, arguments)
        elif self.mode == "http":
            return await self._call_http(tool_name, arguments)
        elif self.mode == "stdio":
            return await self._call_stdio(tool_name, arguments)
        else:
            raise ValueError(f"Unsupported MCP mode: {self.mode}")

    async def _call_mock(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """模拟模式 - 用于开发和测试"""
        await asyncio.sleep(0.5)  # 模拟网络延迟

        if tool_name == "block_ip":
            return {
                "success": True,
                "result": {
                    "action": "block",
                    "ip": arguments.get("ip"),
                    "device_id": arguments.get("device_id"),
                    "rule_id": f"rule_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "timestamp": datetime.utcnow().isoformat(),
                },
                "tool": tool_name,
            }
        elif tool_name == "unblock_ip":
            return {
                "success": True,
                "result": {
                    "action": "unblock",
                    "ip": arguments.get("ip"),
                    "device_id": arguments.get("device_id"),
                    "timestamp": datetime.utcnow().isoformat(),
                },
                "tool": tool_name,
            }
        elif tool_name == "get_device_status":
            return {
                "success": True,
                "result": {
                    "device_id": arguments.get("device_id"),
                    "status": "online",
                    "cpu_usage": 45.2,
                    "memory_usage": 62.1,
                    "uptime": "15d 3h 22m",
                    "timestamp": datetime.utcnow().isoformat(),
                },
                "tool": tool_name,
            }
        elif tool_name == "get_acl_rules":
            return {
                "success": True,
                "result": {
                    "device_id": arguments.get("device_id"),
                    "rules": [
                        {
                            "id": "acl_001",
                            "action": "deny",
                            "src": "192.168.1.100",
                            "dst": "any",
                        },
                        {
                            "id": "acl_002",
                            "action": "permit",
                            "src": "any",
                            "dst": "any",
                        },
                    ],
                },
                "tool": tool_name,
            }
        else:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "tool": tool_name,
            }

    async def _call_http(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """通过 HTTP API 调用 MCP 工具"""
        try:
            payload = {"tool": tool_name, "arguments": arguments}

            response = await self.http_client.post(
                f"{self.server_url}/api/tools/call",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            result = response.json()
            return {"success": True, "result": result.get("result"), "tool": tool_name}

        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"HTTP error: {e.response.status_code}",
                "detail": e.response.text[:500],
                "tool": tool_name,
            }
        except httpx.ConnectError as e:
            return {
                "success": False,
                "error": f"Connection error: Cannot connect to MCP server at {self.server_url}",
                "tool": tool_name,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "tool": tool_name,
            }

    async def _call_stdio(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """通过 stdio 调用本地 MCP 工具"""
        try:
            # 构建命令
            cmd = [
                "python",
                "-m",
                "mcp_tools",  # 假设有 mcp_tools 模块
                "--tool",
                tool_name,
                "--args",
                json.dumps(arguments),
            ]

            # 执行子进程
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout
            )

            if process.returncode != 0:
                return {
                    "success": False,
                    "error": stderr.decode("utf-8", errors="ignore")[:500],
                    "tool": tool_name,
                }

            # 解析输出
            output = stdout.decode("utf-8", errors="ignore")
            try:
                result = json.loads(output)
                return {"success": True, "result": result, "tool": tool_name}
            except json.JSONDecodeError:
                return {
                    "success": True,
                    "result": {"raw_output": output},
                    "tool": tool_name,
                }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Timeout after {self.timeout}s",
                "tool": tool_name,
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "MCP tool not found. Please install mcp_tools package.",
                "tool": tool_name,
            }
        except Exception as e:
            return {"success": False, "error": str(e)[:500], "tool": tool_name}

    # ===== 业务方法 =====

    async def block_ip(
        self, ip: str, device_id: Optional[int] = None, operator: str = "system"
    ) -> Dict[str, Any]:
        """封禁 IP"""
        result = await self.call_tool("block_ip", {"ip": ip, "device_id": device_id})

        # 记录审计
        db = SessionLocal()
        try:
            AuditService.log(
                db=db,
                actor=operator,
                action="mcp_block_ip",
                target=f"ip:{ip}",
                target_type="firewall_rule",
                result="success" if result.get("success") else "failed",
                reason=result.get("error")
                if not result.get("success")
                else f"Blocked IP {ip}",
            )
        finally:
            db.close()

        return result

    async def unblock_ip(
        self, ip: str, device_id: Optional[int] = None, operator: str = "system"
    ) -> Dict[str, Any]:
        """解封 IP"""
        result = await self.call_tool("unblock_ip", {"ip": ip, "device_id": device_id})

        # 记录审计
        db = SessionLocal()
        try:
            AuditService.log(
                db=db,
                actor=operator,
                action="mcp_unblock_ip",
                target=f"ip:{ip}",
                target_type="firewall_rule",
                result="success" if result.get("success") else "failed",
                reason=result.get("error")
                if not result.get("success")
                else f"Unblocked IP {ip}",
            )
        finally:
            db.close()

        return result

    async def get_device_status(self, device_id: int) -> Dict[str, Any]:
        """获取设备状态"""
        return await self.call_tool("get_device_status", {"device_id": device_id})

    async def get_acl_rules(self, device_id: int) -> Dict[str, Any]:
        """获取 ACL 规则列表"""
        return await self.call_tool("get_acl_rules", {"device_id": device_id})

    async def execute_on_device(
        self, device_id: int, command: str, credential_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """在设备上执行命令（SSH/Telnet）"""
        db = SessionLocal()
        try:
            # 获取设备信息
            device = db.query(Device).filter(Device.id == device_id).first()
            if not device:
                return {"success": False, "error": f"Device {device_id} not found"}

            # 获取凭据
            if credential_id:
                credential = (
                    db.query(Credential).filter(Credential.id == credential_id).first()
                )
            else:
                credential = (
                    db.query(Credential)
                    .filter(Credential.device_id == device_id)
                    .first()
                )

            if not credential:
                return {
                    "success": False,
                    "error": f"No credential found for device {device_id}",
                }

            # 调用 MCP 工具执行命令
            return await self.call_tool(
                "execute_command",
                {
                    "device_id": device_id,
                    "device_ip": device.ip,
                    "device_port": device.port,
                    "vendor": device.vendor,
                    "username": credential.username,
                    "password": credential.secret_ciphertext,  # 需要解密
                    "command": command,
                },
            )
        finally:
            db.close()

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.http_client.aclose()


# Global instance
mcp_client = MCPClient()
