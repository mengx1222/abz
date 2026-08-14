"""Phase 6 — Enhanced Health Check Endpoints.

- GET /health        → Liveness probe (lightweight)
- GET /ready        → Readiness probe (checks DB, Redis, AI provider)
- GET /health/detail → Detailed info (masked URLs, middleware stack, etc.)
"""

import asyncio
import re
import time

from fastapi import APIRouter, Request
from structlog import get_logger

from app.core.config import settings
from app.schemas.common import SuccessResponse

logger = get_logger()
router = APIRouter()

# --- Module-level startup timestamp ---
_start_time: float = time.time()

# --- Helpers -------------------------------------------------------------------

# Regex that matches a password inside a URL, e.g.
#   postgresql://user:secret@host  or  redis://:password@host
_URL_PASSWORD_RE = re.compile(r"(://[^:]+:)([^@]+)(@)")


def _mask_url(url: str) -> str:
    """Return *url* with the password portion replaced by '****'."""
    if not url:
        return ""
    return _URL_PASSWORD_RE.sub(r"\1****\3", url)


async def _check_database() -> str:
    """Lightweight database connectivity check.

    Returns one of: "connected", "unreachable", "not_required", "not_configured".
    """
    if settings.DEMO_MODE:
        return "not_required"

    url = settings.DATABASE_URL
    if not url:
        return "not_configured"

    try:
        import asyncpg
    except ImportError:
        logger.warning("health.db_check", reason="asyncpg_not_installed")
        return "unreachable"

    try:
        # Build a minimal connection string for a quick SELECT 1
        # asyncpg expects postgresql://user:pass@host:port/db
        conn = await asyncio.wait_for(
            asyncpg.connect(url),
            timeout=2.0,
        )
        try:
            await asyncio.wait_for(conn.fetchval("SELECT 1"), timeout=2.0)
        finally:
            await conn.close()
        return "connected"
    except Exception as exc:
        logger.warning("health.db_check", error=str(exc))
        return "unreachable"


async def _check_redis() -> str:
    """Lightweight Redis connectivity check.

    Returns one of: "connected", "unreachable", "not_required", "not_configured".
    """
    if settings.DEMO_MODE:
        return "not_required"

    url = settings.REDIS_URL
    if not url or url == "redis://localhost:6379/0":
        return "not_configured"

    try:
        from redis.asyncio import Redis as AsyncRedis
    except ImportError:
        logger.warning("health.redis_check", reason="redis_not_installed")
        return "unreachable"

    try:
        client = AsyncRedis.from_url(url)
        await asyncio.wait_for(client.ping(), timeout=2.0)
        await client.aclose()
        return "connected"
    except Exception as exc:
        logger.warning("health.redis_check", error=str(exc))
        return "unreachable"


def _check_ai_provider() -> str:
    """Return AI provider readiness status."""
    provider = settings.effective_ai_provider
    if provider == "mock":
        return "mock_ready"
    return "configured"


def _readiness_ok(checks: dict) -> bool:
    """A check value is considered "passing" when it is one of:
    True, "not_required", "connected", "configured", "mock_ready".
    """
    _PASSING = {True, "not_required", "connected", "configured", "mock_ready"}
    return all(v in _PASSING for v in checks.values())


def _middleware_stack(app) -> list[str]:
    """Extract middleware class names from the Starlette app's middleware stack."""
    names: list[str] = []
    try:
        # Starlette stores middleware as a linked list of Middleware objects
        # accessed via app.user_middleware (list) and app.middleware_stack (ASGI)
        for mw in getattr(app, "user_middleware", []):
            cls = getattr(mw, "cls", None)
            if cls is not None:
                names.append(cls.__name__)
    except Exception:
        pass
    return names


# --- Endpoints -----------------------------------------------------------------


@router.get("/health", summary="健康检查（Liveness）")
async def health_check(request: Request) -> SuccessResponse:
    """Liveness probe — is the service process alive?"""
    request_id = getattr(request.state, "request_id", None)
    uptime = round(time.time() - _start_time, 2)
    return SuccessResponse(
        data={
            "status": "healthy",
            "version": settings.APP_VERSION,
            "demo_mode": settings.DEMO_MODE,
            "uptime_seconds": uptime,
        },
        request_id=request_id,
    )


@router.get("/ready", summary="就绪检查（Readiness）")
async def readiness_check(request: Request) -> SuccessResponse:
    """Readiness probe — is the service ready to serve traffic?

    Checks:
    - config_loaded: always True (if this handler runs, config is loaded)
    - database: in demo → "not_required"; in prod → "connected" / "unreachable"
    - redis:    same pattern as database
    - ai_provider: "mock_ready" or "configured"
    """
    request_id = getattr(request.state, "request_id", None)

    checks = {
        "config_loaded": True,
        "database": await _check_database(),
        "redis": await _check_redis(),
        "ai_provider": _check_ai_provider(),
    }

    all_ok = _readiness_ok(checks)

    return SuccessResponse(
        data={
            "status": "ready" if all_ok else "not_ready",
            "checks": checks,
            "version": settings.APP_VERSION,
        },
        request_id=request_id,
    )


@router.get("/health/detail", summary="详细健康信息")
async def health_detail(request: Request) -> SuccessResponse:
    """Detailed health information including masked URLs, middleware stack, etc."""
    request_id = getattr(request.state, "request_id", None)
    uptime = round(time.time() - _start_time, 2)

    # Import here to avoid circular import at module level
    from app.main import app as fastapi_app

    return SuccessResponse(
        data={
            "status": "healthy",
            "version": settings.APP_VERSION,
            "app_env": settings.APP_ENV,
            "demo_mode": settings.DEMO_MODE,
            "uptime_seconds": uptime,
            "ai_provider": settings.effective_ai_provider,
            "database_url_masked": _mask_url(settings.DATABASE_URL),
            "redis_url_masked": _mask_url(settings.REDIS_URL),
            "middleware_stack": _middleware_stack(fastapi_app),
        },
        request_id=request_id,
    )
