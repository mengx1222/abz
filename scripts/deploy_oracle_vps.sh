#!/usr/bin/env bash
# 安诊保 AI 副驾 — Oracle 免费 VPS 一键部署（便携包 + systemd 常驻）
# 用法:
#   ./scripts/deploy_oracle_vps.sh <实例公网IP> [SSH私钥路径]
# 默认私钥: ~/.ssh/oracle_abz
# 前置条件:
#   - 实例为 Ubuntu 24.04 (aarch64)，已注入 deploy 公钥
#   - VCN 安全列表已放行 TCP 22(默认) 与 80
#   - 包已构建: dist/anzhenbao-ai-linux.tar.gz (package_linux.sh 或手动 staging)
set -euo pipefail

HOST="${1:?用法: $0 <实例公网IP> [SSH私钥路径]}"
KEY="${2:-$HOME/.ssh/oracle_abz}"
TARBALL="$(cd "$(dirname "$0")/../dist" && pwd)/anzhenbao-ai-linux.tar.gz"
REMOTE_DIR="/opt/anzhenbao"

[ -f "$TARBALL" ] || { echo "❌ 找不到 $TARBALL，先构建便携包"; exit 1; }
SSH="ssh -i $KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 ubuntu@$HOST"
SCP="scp -i $KEY -o StrictHostKeyChecking=accept-new"

echo "==> [1/5] 检查 SSH 连通性..."
$SSH 'echo ok && uname -m && lsb_release -ds'

echo "==> [2/5] 安装系统依赖 (python3.12/venv)..."
$SSH 'sudo apt-get update -qq && sudo apt-get install -y -qq python3-venv python3-full curl >/dev/null && python3 --version'

echo "==> [3/5] 上传便携包并解压..."
$SSH "sudo mkdir -p $REMOTE_DIR && sudo chown ubuntu $REMOTE_DIR"
$SCP "$TARBALL" "ubuntu@$HOST:/tmp/abz.tar.gz"
$SSH "tar xzf /tmp/abz.tar.gz -C $REMOTE_DIR --strip-components=1 && rm /tmp/abz.tar.gz && ls $REMOTE_DIR"

echo "==> [4/5] 初始化环境: venv + 依赖 + 建表 + 种子数据..."
$SSH 'bash -s' <<'INIT'
set -euo pipefail
cd /opt/anzhenbao
python3 -m venv .venv
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -q ./backend aiosqlite
export AZB_DEMO_MODE=true AZB_WEB_DIST_DIR=/opt/anzhenbao/web
export AZB_DATABASE_URL="sqlite+aiosqlite:////opt/anzhenbao/data/anzhenbao.db"
mkdir -p data
cd backend
if [ ! -f ../data/.initialized ]; then
  ../.venv/bin/python - <<'PY'
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
  ../.venv/bin/python -m scripts.seed
  touch ../data/.initialized
fi
echo "init done"
INIT

echo "==> [5/5] 写入 systemd 服务并启动 (端口 80)..."
$SSH 'sudo tee /etc/systemd/system/anzhenbao.service >/dev/null' <<'UNIT'
[Unit]
Description=Anzhenbao AI demo (FastAPI + SQLite)
After=network-online.target

[Service]
WorkingDirectory=/opt/anzhenbao/backend
ExecStart=/opt/anzhenbao/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 80 --workers 2
Environment=AZB_DEMO_MODE=true
Environment=AZB_WEB_DIST_DIR=/opt/anzhenbao/web
Environment=AZB_DATABASE_URL=sqlite+aiosqlite:////opt/anzhenbao/data/anzhenbao.db
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT
$SSH 'sudo systemctl daemon-reload && sudo systemctl enable --now anzhenbao && sleep 3 && systemctl is-active anzhenbao'

echo "==> 放行实例内防火墙 80 端口..."
$SSH 'sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null; sudo netfilter-persistent save 2>/dev/null || sudo sh -c "iptables-save > /etc/iptables/rules.v4" || true'

echo "==> 健康检查..."
sleep 2
CODE=$($SSH 'curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/api/v1/ready || true')
echo "本机 /api/v1/ready -> HTTP $CODE"
if [ "$CODE" = "200" ]; then
  echo ""
  echo "🎉 部署完成！浏览器访问: http://$HOST/"
  echo "   演示账号: 13800138000 / 密码 888888"
else
  echo "⚠️ 本机健康检查 HTTP=$CODE，看日志: ssh ubuntu@$HOST 'journalctl -u anzhenbao -n 50 --no-pager'"
fi
