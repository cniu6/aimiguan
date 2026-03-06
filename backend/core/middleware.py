from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Callable
from collections import defaultdict
import time
import uuid
from functools import wraps


class TraceIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response


# ── 接口限流中间件 ──

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    滑动窗口限流。
    - 全局默认：60 次/分
    - 登录接口：5 次/分（防暴力）
    """

    def __init__(self, app, global_rpm: int = 60, login_rpm: int = 5):
        super().__init__(app)
        self.global_rpm = global_rpm
        self.login_rpm = login_rpm
        self._hits: dict[str, list[float]] = defaultdict(list)

    def _client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_limited(self, key: str, rpm: int) -> bool:
        now = time.monotonic()
        window = 60.0
        hits = self._hits[key]
        # 清理窗口外数据
        self._hits[key] = [t for t in hits if now - t < window]
        if len(self._hits[key]) >= rpm:
            return True
        self._hits[key].append(now)
        return False

    async def dispatch(self, request: Request, call_next: Callable):
        client_ip = self._client_ip(request)
        path = request.url.path

        # 登录接口加严限流
        is_login = path.endswith("/auth/login") and request.method == "POST"
        if is_login:
            key = f"login:{client_ip}"
            if self._is_limited(key, self.login_rpm):
                return JSONResponse(
                    status_code=429,
                    content={
                        "code": 42900,
                        "message": "登录尝试过于频繁，请 1 分钟后重试",
                    },
                )

        # 全局限流
        global_key = f"global:{client_ip}"
        if self._is_limited(global_key, self.global_rpm):
            return JSONResponse(
                status_code=429,
                content={
                    "code": 42901,
                    "message": "请求过于频繁，请稍后重试",
                },
                headers={"Retry-After": "60"},
            )

        response = await call_next(request)
        return response


def require_role(*allowed_roles: str):
    """RBAC 权限装饰器"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(status_code=403, detail="需要登录")

            if current_user.role not in allowed_roles:
                raise HTTPException(
                    status_code=403, detail=f"需要权限: {', '.join(allowed_roles)}"
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
