from fastapi import APIRouter, Request

from app.core.config import settings
from app.schemas.common import SuccessResponse

router = APIRouter()


@router.get("/health", summary="健康检查（Liveness）")
async def health_check(request: Request) -> SuccessResponse:
    """Liveness probe：服务进程是否存活。"""
    request_id = getattr(request.state, "request_id", None)
    return SuccessResponse(
        data={
            "status": "healthy",
            "demo_mode": settings.DEMO_MODE,
            "version": "0.2.0",
        },
        request_id=request_id,
    )


@router.get("/ready", summary="就绪检查（Readiness）")
async def readiness_check(request: Request) -> SuccessResponse:
    """Readiness probe：服务是否准备好接收流量。

    检查项：
    - 应用配置已加载
    - Demo 模式无需数据库
    - 生产模式需数据库连接（后续 Phase 实现）
    """
    request_id = getattr(request.state, "request_id", None)
    checks = {
        "config_loaded": True,
        "demo_mode": settings.DEMO_MODE,
    }
    # 生产模式数据库检查将在 Phase 3 实现
    if not settings.DEMO_MODE:
        checks["database"] = "not_checked_yet"

    all_ok = all(v is True or v == "not_checked_yet" for v in checks.values())

    return SuccessResponse(
        data={
            "status": "ready" if all_ok else "not_ready",
            "checks": checks,
            "version": "0.2.0",
        },
        request_id=request_id,
    )
