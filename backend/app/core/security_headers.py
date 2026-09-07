"""安全头中间件 —— CSP、X-Frame-Options 等安全响应头。"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """为所有响应添加安全头。"""

    CSP_DEMO = (
        "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "connect-src 'self' http://localhost:* https://preview-*.space-z.ai; "
        "img-src 'self' data: blob:; "
        "style-src 'self' 'unsafe-inline'"
    )

    CSP_PRODUCTION = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'"
    )

    # 仅文档端点（Swagger UI / ReDoc）使用：UI 框架与样式需从国内 CDN 加载，
    # 但 default-src 仍锁 'self'，不对其它接口放松限制
    CSP_DOCS = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.bootcdn.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.bootcdn.net; "
        "img-src 'self' data: blob: https://fastapi.tiangolo.com; "
        "font-src 'self' https://cdn.bootcdn.net; "
        "connect-src 'self'"
    )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        # CSP：文档端点（/docs /redoc）需加载 CDN 资源，单独放宽；其余接口保持严格策略
        if request.url.path in {"/docs", "/redoc"}:
            response.headers["Content-Security-Policy"] = self.CSP_DOCS
        elif settings.DEMO_MODE or settings.DEBUG:
            response.headers["Content-Security-Policy"] = self.CSP_DEMO
        else:
            response.headers["Content-Security-Policy"] = self.CSP_PRODUCTION

        # HSTS 仅 production
        if not settings.DEBUG and not settings.DEMO_MODE:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response
