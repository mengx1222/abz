#!/bin/bash
# Phase 5 部署检查脚本
# 检查生产部署前的关键项目

set -e
echo "=== Phase 5 部署前检查 ==="

# 1. 检查必要文件
echo ""
echo "--- 文件检查 ---"
check_file() {
    if [ -f "$1" ]; then
        echo "  ✅ $1"
    else
        echo "  ❌ $1 (缺失)"
        MISSING=1
    fi
}

check_file "backend/.env.production"
check_file "docker-compose.prod.yml"
check_file "backend/Dockerfile"
check_file "frontend/Dockerfile"
check_file "backend/alembic.ini"
check_file "backend/alembic/env.py"
check_file "backend/scripts/seed.py"

# 2. 检查迁移
echo ""
echo "--- Alembic 迁移检查 ---"
ALEMBIC_HEAD=$(cd /home/z/my-project/backend && source .venv/bin/activate && python -c "
from alembic.config import Config
from alembic.script import ScriptDirectory
config = Config('alembic.ini')
script = ScriptDirectory.from_config(config)
print(script.get_current_head())
" 2>/dev/null)
echo "  Head: $ALEMBIC_HEAD"

# 3. 检查 backend 导入
echo ""
echo "--- Backend 导入检查 ---"
cd /home/z/my-project/backend && source .venv/bin/activate
python -c "
from app.main import app
print(f'  App: {app.title} v{app.version}')
print(f'  ✅ 导入成功')
" 2>&1 | head -5

# 4. 检查前端构建
echo ""
echo "--- Frontend 构建检查 ---"
cd /home/z/my-project/frontend
BUILD_SIZE=$(ls -la dist/assets/index-*.js 2>/dev/null | awk '{print $5}')
if [ -n "$BUILD_SIZE" ]; then
    echo "  ✅ 前端已构建 (entry: ${BUILD_SIZE} bytes)"
else
    echo "  ⚠️ 前端未构建 (运行: cd frontend && npm run build)"
fi

echo ""
echo "=== 检查完成 ==="