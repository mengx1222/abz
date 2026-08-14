import uuid

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from structlog import get_logger

from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware
from app.core.audit import AuditMiddleware
from app.core.security_headers import SecurityHeadersMiddleware

logger = get_logger()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """为每个请求注入唯一的 request_id，并写入响应头。"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """全局异常捕获中间件，返回统一格式的错误响应。"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.error(
                "unhandled_error",
                request_id=request_id,
                path=request.url.path,
                error=str(exc),
                exc_info=True,
            )
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "服务器内部错误，请稍后重试" if not settings.DEBUG else str(exc),
                    },
                    "request_id": request_id,
                },
            )


def register_middleware(app: FastAPI) -> None:
    """注册所有自定义中间件。

    注册顺序（从外到内，即最先添加的最外层）:
    1. SecurityHeadersMiddleware  — 确保所有响应都有安全头
    2. RateLimitMiddleware        — 限流在安全头之后、业务逻辑之前
    3. AuditMiddleware            — 在限流之后，需要记录限流事件
    4. RequestIDMiddleware        — 已有
    5. ErrorHandlerMiddleware     — 最内层
    """
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)
