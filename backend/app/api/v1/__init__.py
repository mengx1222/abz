from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.ai import router as ai_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.customer import router as customer_router
from app.api.v1.training import router as training_router
from app.api.v1.script import router as script_router
from app.api.v1.community import router as community_router
from app.api.v1.admin import router as admin_router
from app.api.v1.growth import router as growth_router
from app.api.v1.notification import router as notification_router
from app.api.v1.dashboard import router as dashboard_router

router = APIRouter()

router.include_router(health_router, tags=["健康检查"])
router.include_router(auth_router, prefix="/auth", tags=["认证"])
router.include_router(ai_router, prefix="/ai", tags=["AI 助手"])
router.include_router(knowledge_router, prefix="/admin", tags=["知识库管理"])
router.include_router(customer_router, prefix="/customers", tags=["客户360"])
router.include_router(training_router, prefix="/training", tags=["AI 陪练"])
router.include_router(script_router, prefix="/scripts", tags=["AI 话术"])
router.include_router(community_router, prefix="/community", tags=["AI 社区"])
router.include_router(admin_router, prefix="/admin", tags=["管理后台"])
router.include_router(growth_router, prefix="/growth", tags=["成长体系"])
router.include_router(notification_router, prefix="/notifications", tags=["通知中心"])
router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
