from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import uuid
from functools import wraps

class TraceIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response

def require_role(*allowed_roles: str):
    """RBAC 权限装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from api.auth import get_current_user
            from fastapi import Depends
            
            # 从 kwargs 中获取 current_user
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(status_code=40301, detail="需要登录")
            
            if current_user.role not in allowed_roles:
                raise HTTPException(status_code=40302, detail=f"需要权限: {', '.join(allowed_roles)}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
