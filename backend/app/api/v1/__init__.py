from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.ai import router as ai_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.customer import router as customer_router
from app.api.v1.training import router as training_router
from app.api.v1.script import router as script_router

router = APIRouter()

router.include_router(health_router, tags=["健康检查"])
router.include_router(auth_router, prefix="/auth", tags=["认证"])
router.include_router(ai_router, prefix="/ai", tags=["AI 助手"])
router.include_router(knowledge_router, prefix="/admin", tags=["知识库管理"])
router.include_router(customer_router, prefix="/customers", tags=["客户360"])
router.include_router(training_router, prefix="/training", tags=["AI 陪练"])
router.include_router(script_router, prefix="/scripts", tags=["AI 话术"])
