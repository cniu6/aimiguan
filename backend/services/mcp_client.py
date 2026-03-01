"""MCP Client Service - MCP 工具调用"""

import os
import json
import asyncio
from typing import Dict, Any, Optional, List
import httpx
from datetime import datetime, timezone

from core.database import SessionLocal, Device, Credential, ExecutionTask
from services.audit_service import AuditService


def _classify_error_retryable(error_msg: str, status_code: Optional[int] = None) -> bool:
    """判断错误是否可重试
    
    可重试错误：网络超时、临时服务不可用、速率限制
    不可重试错误：认证失败、参数错误、资源不存在
    """
    error_lower = error_msg.lower()
    
    # 不可重试的错误模式
    non_retryable_patterns = [
        "authentication", "auth", "unauthorized", "forbidden",
        "invalid", "not found", "does not exist",
        "bad request", "malformed", "syntax error",
        "permission denied", "access denied",
    ]
    
    for pattern in non_retryable_patterns:
        if pattern in error_lower:
            return False
    
    # HTTP 状态码判断
    if status_code:
        if status_code in [400, 401, 403, 404, 422]:  # 客户端错误
            return False
        if status_code in [429, 500, 502, 503, 504]:  # 速率限制或临时服务错误
            return True
    
    # 可重试的错误模式
    retryable_patterns = [
        "timeout", "connection", "network", "unavailable",
        "rate limit", "too many requests", "temporary",
    ]
    
    for pattern in retryable_patterns:
        if pattern in error_lower:
            return True
    
    # 默认可重试（保守策略）
    return True


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
                    "timestamp": datetime.now(timezone.utc).isoformat(),
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
                    "timestamp": datetime.now(timezone.utc).isoformat(),
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
                    "timestamp": datetime.now(timezone.utc).isoformat(),
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
            error_msg = f"Unknown tool: {tool_name}"
            return {
                "success": False,
                "error": error_msg,
                "tool": tool_name,
                "retryable": False,  # 未知工具不可重试
            }

    async def _call_http(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """通过 HTTP/SSE 调用 MCP 工具（JSON-RPC 2.0 协议）"""
        try:
            # 1. Initialize session
            init_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "aimiguard", "version": "1.0.0"},
                },
            }

            init_response = await self.http_client.post(
                f"{self.server_url}/mcp/v1",
                json=init_payload,
                headers={"Content-Type": "application/json"},
            )
            init_response.raise_for_status()
            init_data = init_response.json()

            if "error" in init_data:
                raise Exception(f"Initialize failed: {init_data['error']}")

            # 2. Call tool
            call_payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            }

            call_response = await self.http_client.post(
                f"{self.server_url}/mcp/v1",
                json=call_payload,
                headers={"Content-Type": "application/json"},
            )
            call_response.raise_for_status()
            call_data = call_response.json()

            if "error" in call_data:
                error_msg = call_data["error"].get("message", str(call_data["error"]))
                return {
                    "success": False,
                    "error": error_msg,
                    "tool": tool_name,
                    "retryable": _classify_error_retryable(error_msg),
                }

            return {
                "success": True,
                "result": call_data.get("result", {}),
                "tool": tool_name,
            }

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}"
            return {
                "success": False,
                "error": error_msg,
                "detail": e.response.text[:500],
                "tool": tool_name,
                "retryable": _classify_error_retryable(error_msg, e.response.status_code),
            }
        except httpx.ConnectError:
            return {
                "success": False,
                "error": f"Cannot connect to MCP server at {self.server_url}",
                "tool": tool_name,
                "retryable": True,
            }
        except Exception as e:
            error_msg = str(e)[:500]
            return {
                "success": False,
                "error": error_msg,
                "tool": tool_name,
                "retryable": _classify_error_retryable(error_msg),
            }

    async def _call_stdio(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """通过 stdio 调用本地 MCP 工具（JSON-RPC 2.0 协议）"""
        try:
            # 获取 MCP 服务器命令
            mcp_command = os.getenv("MCP_STDIO_COMMAND", "npx -y @modelcontextprotocol/server-everything")
            cmd = mcp_command.split()

            # 启动 MCP 服务器进程
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # 1. 发送 initialize 请求
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "aimiguard", "version": "1.0.0"},
                },
            }
            process.stdin.write((json.dumps(init_request) + "\n").encode())
            await process.stdin.drain()

            # 读取 initialize 响应
            init_response = await asyncio.wait_for(
                process.stdout.readline(), timeout=5.0
            )
            init_data = json.loads(init_response.decode())
            if "error" in init_data:
                raise Exception(f"Initialize failed: {init_data['error']}")

            # 2. 发送 tools/call 请求
            call_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            }
            process.stdin.write((json.dumps(call_request) + "\n").encode())
            await process.stdin.drain()

            # 读取 tools/call 响应
            call_response = await asyncio.wait_for(
                process.stdout.readline(), timeout=self.timeout
            )
            call_data = json.loads(call_response.decode())

            # 关闭进程
            process.stdin.close()
            await process.wait()

            if "error" in call_data:
                error_msg = call_data["error"].get("message", str(call_data["error"]))
                return {
                    "success": False,
                    "error": error_msg,
                    "tool": tool_name,
                    "retryable": _classify_error_retryable(error_msg),
                }

            return {
                "success": True,
                "result": call_data.get("result", {}),
                "tool": tool_name,
            }

        except asyncio.TimeoutError:
            if process:
                process.kill()
            return {
                "success": False,
                "error": f"Timeout after {self.timeout}s",
                "tool": tool_name,
                "retryable": True,
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": f"MCP command not found: {mcp_command}",
                "tool": tool_name,
                "retryable": False,
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON response: {str(e)}",
                "tool": tool_name,
                "retryable": False,
            }
        except Exception as e:
            if process:
                process.kill()
            error_msg = str(e)[:500]
            return {
                "success": False,
                "error": error_msg,
                "tool": tool_name,
                "retryable": _classify_error_retryable(error_msg),
            }

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
