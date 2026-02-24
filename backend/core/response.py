from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Any, Optional

class APIResponse:
    @staticmethod
    def success(data: Any = None, message: str = "操作成功", trace_id: str = None):
        return {
            "code": 0,
            "message": message,
            "data": data,
            "trace_id": trace_id
        }
    
    @staticmethod
    def error(code: int, message: str, trace_id: str = None):
        return {
            "code": code,
            "message": message,
            "data": None,
            "trace_id": trace_id
        }

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    trace_id = getattr(request.state, "trace_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse.error(
            code=exc.status_code if exc.status_code < 1000 else exc.status_code,
            message=exc.detail,
            trace_id=trace_id
        )
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    trace_id = getattr(request.state, "trace_id", None)
    errors = exc.errors()
    message = f"参数验证失败: {errors[0]['msg']}" if errors else "参数验证失败"
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=APIResponse.error(
            code=40000,
            message=message,
            trace_id=trace_id
        )
    )

async def general_exception_handler(request: Request, exc: Exception):
    trace_id = getattr(request.state, "trace_id", None)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=APIResponse.error(
            code=50000,
            message=f"服务器内部错误: {str(exc)}",
            trace_id=trace_id
        )
    )
