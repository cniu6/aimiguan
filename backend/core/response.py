from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Any, Optional, Tuple

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
    def error(code: int, message: str, trace_id: str = None, data: Any = None):
        return {
            "code": code,
            "message": message,
            "data": data,
            "trace_id": trace_id
        }

def _normalize_http_status(raw_status: int) -> int:
    if 100 <= raw_status <= 599:
        return raw_status
    if raw_status >= 1000:
        candidate = raw_status // 100
        if 100 <= candidate <= 599:
            return candidate
    return status.HTTP_500_INTERNAL_SERVER_ERROR


def _extract_error_payload(exc: StarletteHTTPException) -> Tuple[int, int, str, Optional[Any]]:
    raw_status = exc.status_code if isinstance(exc.status_code, int) else 500
    normalized_status = _normalize_http_status(raw_status)
    detail = exc.detail

    if isinstance(detail, dict):
        code_value = detail.get("code")
        if isinstance(code_value, int):
            business_code = code_value
        elif raw_status >= 1000:
            business_code = raw_status
        else:
            business_code = normalized_status

        message = detail.get("message")
        if not isinstance(message, str) or not message:
            message = str(detail.get("detail") or detail.get("error") or "请求失败")

        payload_data = detail.get("data")
        if payload_data is None:
            extra_fields = {
                key: value
                for key, value in detail.items()
                if key not in {"code", "message", "trace_id"}
            }
            payload_data = extra_fields or None

        return normalized_status, business_code, message, payload_data

    message = str(detail) if detail else "请求失败"
    business_code = raw_status if raw_status >= 1000 else normalized_status
    return normalized_status, business_code, message, None


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    trace_id = getattr(request.state, "trace_id", None)
    normalized_status, business_code, message, payload_data = _extract_error_payload(exc)
    return JSONResponse(
        status_code=normalized_status,
        content=APIResponse.error(
            code=business_code,
            message=message,
            trace_id=trace_id,
            data=payload_data,
        ),
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
