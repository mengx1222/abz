from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router

router = APIRouter()

router.include_router(health_router, tags=["健康检查"])
router.include_router(auth_router, prefix="/auth", tags=["认证"])
