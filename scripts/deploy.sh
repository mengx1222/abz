#!/bin/bash
# 安诊保 AI 副驾 — 生产部署引导脚本
set -e

echo "🚀 安诊保 AI 副驾 — 部署引导"
echo ""

# 检查 .env.production
if [ ! -f "backend/.env.production" ]; then
    echo "❌ 未找到 .env.production"
    echo "   请复制模板并填写: cp backend/.env.production.template backend/.env.production"
    exit 1
fi

# 检查必要变量
source backend/.env.production
REQUIRED_VARS=("AZB_JWT_SECRET_KEY" "AZB_DATABASE_URL" "AZB_AI_API_KEY")
for var in $REQUIRED_VARS; do
    if eval echo \$$var | grep -q "CHANGE_ME"; then
        echo "❌ 请设置 $var (当前值包含 CHANGE_ME)"
        exit 1
    fi
done

echo "✅ 环境变量检查通过"
echo ""

# 选择部署模式
echo "选择部署模式:"
echo "  1. 生产环境 (docker-compose.prod.yml)"
echo "  2. 开发环境 (docker-compose.yml)"
read -p "请选择 [1/2]: " MODE

if [ "$MODE" = "1" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    echo "🚀 启动生产环境..."
else
    COMPOSE_FILE="docker-compose.yml"
    echo "🔧 启动开发环境..."
fi

docker compose -f $COMPOSE_FILE up -d --build
echo ""
echo "✅ 部署完成!"
echo "   后端: http://localhost:8000"
echo "   前端: http://localhost:3000"
echo "   健康检查: http://localhost:8000/api/v1/health"
