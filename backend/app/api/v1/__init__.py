from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.ai import router as ai_router
from app.api.v1.knowledge import router as knowledge_router

router = APIRouter()

router.include_router(health_router, tags=["健康检查"])
router.include_router(auth_router, prefix="/auth", tags=["认证"])
router.include_router(ai_router, prefix="/ai", tags=["AI 助手"])
router.include_router(knowledge_router, prefix="/admin", tags=["知识库管理"])
