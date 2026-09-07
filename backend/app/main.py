from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html

from app.core.config import settings
from app.core.db_compat import install_sqlite_ddl_compat
from app.core.middleware import register_middleware
from app.api.v1 import router as v1_router

# 便携 Demo 构建：SQLite 时将 JSONB/Vector 列类型降级渲染
install_sqlite_ddl_compat()


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
    docs_url=None,  # 禁用默认 /docs（其静态资源走 cdn.jsdelivr.net，国内易白屏），改用下方自定义路由
    redoc_url=None,  # 生产收口：接口文档仅开发环境（DEBUG=true）暴露
    openapi_url="/openapi.json" if settings.DEBUG else None,
)


if settings.DEBUG:
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        """Swagger UI 文档：静态资源改用国内可达 CDN（bootcdn），避免 jsdelivr 被墙导致白屏。

        仅 DEBUG 环境挂载；生产（APP_ENV=production / DEBUG=false）访问 /docs 与
        /openapi.json 均为 404，不向外暴露 89 个接口的完整规格。
        """
        return get_swagger_ui_html(
            openapi_url=app.openapi_url or "/openapi.json",
            title=f"{settings.APP_NAME} - API 文档",
            swagger_js_url="https://cdn.bootcdn.net/ajax/libs/swagger-ui/5.17.14/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.bootcdn.net/ajax/libs/swagger-ui/5.17.14/swagger-ui.css",
        )

# CORS 配置
cors_origins = settings.FRONTEND_URL.split(",") if settings.FRONTEND_URL else ["http://localhost:3000"]
if settings.DEBUG:
    cors_origins.append("http://localhost:5173")  # Vite dev server
    cors_origins.append("*")  # 仅 DEBUG 允许所有来源（demo 部署为同源托管，无需通配）

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


def _mount_frontend(app: FastAPI) -> None:
    """若存在前端构建产物（dist），由后端直接托管（便携模式，替代 Nginx）。

    目录来源：AZB_WEB_DIST_DIR 环境变量优先，其次 backend/../frontend/dist。
    """
    import os

    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    candidates = [
        os.environ.get("AZB_WEB_DIST_DIR"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "web")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")),
    ]
    web_dir = next((c for c in candidates if c and os.path.isfile(os.path.join(c, "index.html"))), None)
    if not web_dir:
        return

    assets_dir = os.path.join(web_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # API 未匹配到的路径仍返回 404 JSON，避免被 SPA 兜底吞掉
        if full_path.startswith("api"):
            from fastapi import HTTPException

            raise HTTPException(status_code=404)
        file_path = os.path.normpath(os.path.join(web_dir, full_path))
        if full_path and file_path.startswith(os.path.abspath(web_dir)) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(web_dir, "index.html"))

    print(f"🌐 前端静态资源已托管: {web_dir} → http://localhost:8000")


_mount_frontend(app)
