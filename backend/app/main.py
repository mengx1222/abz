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
    print(f"🚀 {settings.APP_NAME} 启动中... (env={settings.APP_ENV}, demo={settings.DEMO_MODE})")
    yield
    # Shutdown
    print(f"👋 {settings.APP_NAME} 已停止")


app = FastAPI(
    title=settings.APP_NAME,
    description="华安保险 AI 销售赋能工作台 API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — 开发模式允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 自定义中间件
register_middleware(app)

# 路由
app.include_router(v1_router, prefix="/api/v1")
