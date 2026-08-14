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

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        # CSP
        if settings.DEMO_MODE or settings.DEBUG:
            response.headers["Content-Security-Policy"] = self.CSP_DEMO
        else:
            response.headers["Content-Security-Policy"] = self.CSP_PRODUCTION

        # HSTS 仅 production
        if not settings.DEBUG and not settings.DEMO_MODE:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response
