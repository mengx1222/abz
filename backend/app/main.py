from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.middleware import register_middleware
from app.api.v1 import router as v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    # Startup
    # ULTIMATE P0-4：生产环境禁止默认/空 JWT 密钥（弱密钥可被伪造令牌）
    if settings.APP_ENV.lower() == "production":
        _weak_secret = (
            not settings.JWT_SECRET_KEY
            or settings.JWT_SECRET_KEY
            in {"change-me-to-a-random-secret-key-in-production", "change-me"}
        )
        if _weak_secret:
            raise RuntimeError(
                "JWT_SECRET_KEY 未配置强随机密钥（production 禁止启动）。"
                "生成命令: python -c \"import secrets;print(secrets.token_urlsafe(48))\""
            )
    print(f"🚀 {settings.APP_NAME} 启动中... (env={settings.APP_ENV}, demo={settings.DEMO_MODE})")
    yield
    # Shutdown
    print(f"👋 {settings.APP_NAME} 已停止")


app = FastAPI(
    title=settings.APP_NAME,
    description="华安保险 AI 销售赋能工作台 API",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS 配置
cors_origins = settings.FRONTEND_URL.split(",") if settings.FRONTEND_URL else ["http://localhost:3000"]
if settings.DEBUG or settings.DEMO_MODE:
    cors_origins.append("http://localhost:5173")  # Vite dev server
    cors_origins.append("*")  # Demo模式允许所有来源

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Forwarded-For"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
)

# 自定义中间件
register_middleware(app)

# 路由
app.include_router(v1_router, prefix="/api/v1")
