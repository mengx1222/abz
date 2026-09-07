# 便携 Demo 单容器镜像（安诊保 AI 副驾）
# 用途：Render / 任意支持 Docker 的免费托管平台，一条容器跑全栈
# 形态：FastAPI 后端 + SQLite（便携 DDL 兼容）+ 直接托管前端 dist + 种子数据
# 注意：免费托管平台磁盘均易失，容器重启后 start_demo.sh 会自动重建并播种
# ======= 阶段1：构建前端 =======
FROM node:20-alpine AS web
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ======= 阶段2：后端运行时 =======
FROM python:3.12-slim
WORKDIR /opt/anzhenbao
COPY backend/pyproject.toml backend/
COPY backend/app backend/app
COPY backend/scripts backend/scripts
RUN pip install --no-cache-dir ./backend aiosqlite
COPY --from=web /app/dist web
COPY deploy/start_demo.sh /opt/anzhenbao/start_demo.sh
RUN chmod +x /opt/anzhenbao/start_demo.sh && mkdir -p /opt/anzhenbao/data

ENV AZB_DEMO_MODE=true \
    AZB_WEB_DIST_DIR=/opt/anzhenbao/web \
    AZB_DATABASE_URL=sqlite+aiosqlite:////opt/anzhenbao/data/anzhenbao.db

# Render 免费档通过 PORT 环境变量指定监听端口（默认 10000）
EXPOSE 10000
CMD ["/opt/anzhenbao/start_demo.sh"]
