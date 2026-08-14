from fastapi import APIRouter, Request

from app.core.config import settings
from app.schemas.common import SuccessResponse

router = APIRouter()


@router.get("/health", summary="健康检查")
async def health_check(request: Request) -> SuccessResponse:
    """返回服务健康状态和演示模式标识。"""
    request_id = getattr(request.state, "request_id", None)
    return SuccessResponse(
        data={
            "status": "healthy",
            "demo_mode": settings.DEMO_MODE,
            "version": "0.1.0",
        },
        request_id=request_id,
    )
