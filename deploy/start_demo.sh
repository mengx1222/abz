#!/usr/bin/env bash
# 便携 Demo 启动脚本：SQLite 建表 + 播种（仅首次）+ uvicorn 监听 $PORT
set -euo pipefail
cd /opt/anzhenbao/backend

export AZB_DEMO_MODE=true
export AZB_WEB_DIST_DIR=/opt/anzhenbao/web
export AZB_DATABASE_URL="sqlite+aiosqlite:////opt/anzhenbao/data/anzhenbao.db"

if [ ! -f /opt/anzhenbao/data/.initialized ]; then
  echo "==> 初始化 SQLite 数据库并播种演示数据..."
  python - <<'PY'
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.core.db_compat import install_sqlite_ddl_compat
from app.models.base import Base
import app.models  # noqa: F401

async def main():
    install_sqlite_ddl_compat()
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

asyncio.run(main())
print("db created")
PY
  python -m scripts.seed
  touch /opt/anzhenbao/data/.initialized
fi

exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
