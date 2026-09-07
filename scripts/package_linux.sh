#!/usr/bin/env bash
# 打包便携 Linux 版：产出 dist/anzhenbao-ai-linux.tar.gz
# 目标机器只需 Python 3.12+（无需 Docker / PostgreSQL / Redis / Node / AI Key）
#   在线模式（默认）：目标机 pip 从 PyPI 装依赖，需联网
#   离线模式 OFFLINE=1：附带预下载的 manylinux x86_64 wheels，目标机可完全离线安装
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$ROOT/dist"
STAGE_NAME="anzhenbao-ai"
STAGE="$OUT_DIR/$STAGE_NAME"

rm -rf "$STAGE" "$ROOT/dist/anzhenbao-ai-linux.tar.gz"
mkdir -p "$STAGE"

echo "==> [1/4] 构建前端..."
( cd "$ROOT/frontend" && npm ci --silent && npm run build )
cp -r "$ROOT/frontend/dist" "$STAGE/web"

echo "==> [2/4] 拷贝后端源码..."
mkdir -p "$STAGE/backend"
cp -r "$ROOT/backend/app"     "$STAGE/backend/app"
cp -r "$ROOT/backend/scripts" "$STAGE/backend/scripts"
cp    "$ROOT/backend/pyproject.toml" "$STAGE/backend/"
find "$STAGE" -type d \( -name "__pycache__" -o -name ".pytest_cache" \) -exec rm -rf {} + 2>/dev/null || true

if [[ "${OFFLINE:-0}" == "1" ]]; then
  echo "==> [3/4] 预下载 Linux x86_64 wheels（离线安装用）..."
  python -m pip download \
    --dest "$STAGE/wheels" \
    --only-binary=:all: \
    --platform manylinux_2_17_x86_64 --platform manylinux2014_x86_64 \
    --implementation cp --python-version 3.12 \
    "fastapi>=0.115.0" "uvicorn[standard]>=0.30.0" "sqlalchemy[asyncio]>=2.0.30" \
    "asyncpg>=0.29.0" "alembic>=1.13.0" "pydantic>=2.7.0" "pydantic-settings>=2.3.0" \
    "python-jose[cryptography]>=3.3.0" "bcrypt>=4.1.0" "redis>=5.0.0" \
    "python-multipart>=0.0.9" "httpx>=0.27.0" "structlog>=24.2.0" "pgvector>=0.3.0" \
    "aiosqlite>=0.20.0"
else
  echo "==> [3/4] 跳过 wheels 预下载（在线模式）"
fi

echo "==> [4/4] 写入启动脚本与说明..."
cat > "$STAGE/start.sh" <<'EOF'
#!/usr/bin/env bash
# 安诊保 AI 副驾 — 一键启动（demo 模式 + SQLite，无需 Docker/PostgreSQL/Redis）
set -euo pipefail
cd "$(dirname "$0")"

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip --quiet

# 安装依赖：优先离线 wheels，失败则回退 PyPI 在线安装
if [ -d wheels ]; then
  pip install --no-index --find-links wheels fastapi "uvicorn[standard]" "sqlalchemy[asyncio]" \
    asyncpg alembic pydantic pydantic-settings "python-jose[cryptography]" bcrypt redis \
    python-multipart httpx structlog pgvector aiosqlite ||
  pip install ./backend aiosqlite
else
  pip install ./backend aiosqlite
fi

export AZB_DEMO_MODE=true
export AZB_WEB_DIST_DIR="$PWD/web"
export AZB_DATABASE_URL="sqlite+aiosqlite:///$PWD/data/anzhenbao.db"
mkdir -p data

cd backend
# SQLite 便携模式：直接按 ORM 模型建表（Alembic 迁移仅用于 PostgreSQL）
if [ ! -f ../data/.initialized ]; then
  python - <<'PY'
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.core.db_compat import install_sqlite_ddl_compat
from app.models.base import Base
import app.models  # noqa: F401  注册全部模型

async def main():
    install_sqlite_ddl_compat()
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

asyncio.run(main())
print("✅ 数据库表已创建")
PY
  python -m scripts.seed
  touch ../data/.initialized
fi

echo ""
echo "✅ 启动完成，浏览器打开: http://localhost:8000"
echo "   演示账号: 13800138000 / 密码 888888 （Ctrl+C 停止）"
uvicorn app.main:app --host 0.0.0.0 --port 8000
EOF
chmod +x "$STAGE/start.sh"

cat > "$STAGE/README-LINUX.txt" <<'EOF'
安诊保 AI 副驾 — Linux 便携版（Demo 模式）

要求：
  - Linux x86_64
  - Python 3.12+（ubuntu: sudo apt install python3.12 python3.12-venv）

使用：
  1. 解压: tar xzf anzhenbao-ai-linux.tar.gz && cd anzhenbao-ai
  2. 启动: ./start.sh
  3. 浏览器打开 http://localhost:8000
     登录账号: 13800138000 / 密码 888888（演示数据）

说明：
  - 内置 SQLite 数据库 + Mock AI，无需 Docker / PostgreSQL / Redis / AI API Key
  - 若包内不带 wheels/ 目录，首次启动需联网下载 Python 依赖
  - 数据保存在 data/anzhenbao.db，删除该文件并重新运行 start.sh 可重置
EOF

tar -czf "$OUT_DIR/anzhenbao-ai-linux.tar.gz" -C "$OUT_DIR" "$STAGE_NAME"
echo ""
echo "🎉 完成: $OUT_DIR/anzhenbao-ai-linux.tar.gz ($(du -h "$OUT_DIR/anzhenbao-ai-linux.tar.gz" | cut -f1))"
