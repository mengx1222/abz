# 部署方案文档 — 安诊保 AI 副驾

> **文档状态**：当前有效 · 已校准为 hatchling/pyproject 构建（无 requirements.txt/setup.py），与 Dockerfile/compose 一致
> 最后校准：2026-08-17


> 版本：v1.0 ｜ 最后更新：2025-07-10 ｜ 负责人：技术团队

---

## 1. 部署概述

### 1.1 设计目标

安诊保 AI 副驾的部署方案以**开发体验优先**为原则，确保任何开发者（包括华安 IT 部门）可以最快速地将系统运行起来：

- **零配置启动**：克隆代码 → 配置 `.env` → 一条命令启动
- **Docker Compose 一体化**：前端、后端、数据库、缓存全部容器化
- **Demo 数据预置**：首次启动自动创建完整的演示环境（用户、产品、知识库、客户等）
- **环境一致性**：开发、测试、演示环境使用相同的 Docker Compose 配置

### 1.2 部署架构图

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Host                           │
│                                                         │
│  ┌──────────────┐   ┌──────────────┐                    │
│  │   Frontend   │   │   Backend    │                    │
│  │  (Nginx)     │──▶│  (Uvicorn)   │                    │
│  │  Port: 3000  │   │  Port: 8000  │                    │
│  └──────────────┘   └──────┬───────┘                    │
│                            │                            │
│                   ┌────────┴────────┐                   │
│                   │                 │                    │
│            ┌──────▼──────┐  ┌──────▼──────┐            │
│            │  PostgreSQL  │  │    Redis     │            │
│            │  + pgvector  │  │              │            │
│            │  Port: 5432  │  │  Port: 6379  │            │
│            └─────────────┘  └─────────────┘            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Docker 架构

### 2.1 服务清单

| 服务 | 镜像/构建方式 | 端口 | 依赖 | 说明 |
|------|-------------|------|------|------|
| frontend | Dockerfile（多阶段构建） | 3000 | backend | React/Vite 构建 → Nginx 静态服务 |
| backend | Dockerfile | 8000 | postgres, redis | FastAPI → Uvicorn ASGI 服务 |
| postgres | `pgvector/pgvector:pg16` | 5432 | 无 | PostgreSQL 16 + pgvector 扩展 |
| redis | `redis:7-alpine` | 6379 | 无 | Redis 7 内存数据库 |

### 2.2 docker-compose.yml

```yaml
version: "3.8"

services:
  # ==================== 前端 ====================
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    depends_on:
      backend:
        condition: service_healthy
    environment:
      - VITE_API_BASE_URL=/api
    restart: unless-stopped

  # ==================== 后端 ====================
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    env_file:
      - .env
    volumes:
      - ./backend/app:/app/app          # 开发时热重载
      - ./data/uploads:/app/uploads      # 上传文件持久化
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # ==================== 数据库 ====================
  postgres:
    image: pgvector/pgvector:pg16
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-anlingbao}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-anlingbao_dev_2025}
      POSTGRES_DB: ${POSTGRES_DB:-anlingbao}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-anlingbao} -d ${POSTGRES_DB:-anlingbao}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # ==================== 缓存 ====================
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  pgdata:
    driver: local
  redisdata:
    driver: local
```

### 2.3 前端 Dockerfile

```dockerfile
# === 构建阶段 ===
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# === 运行阶段 ===
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 2.4 后端 Dockerfile

> 以下为简化示意；仓库内真实文件为 `backend/Dockerfile`（多阶段构建，hatchling/pyproject）：

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
# 项目使用 pyproject.toml（hatchling）而非 requirements.txt
COPY pyproject.toml .
COPY app ./app
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim AS runtime
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local
COPY . .
RUN mkdir -p /app/uploads
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2.5 Nginx 配置

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # SPA 路由回退
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
    }

    # 静态资源缓存
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## 3. 环境变量配置

### 3.1 .env.example

```bash
# ============================================================
# 安诊保 AI 副驾 — 环境变量配置
# 复制本文件为 .env 并修改对应值
# ============================================================

# -------------------- 应用配置 --------------------
APP_NAME=安诊保AI副驾
APP_ENV=development          # development | staging | production
DEMO_MODE=true               # true 启用 Demo 模式（预置数据）
SECRET_KEY=change-me-to-a-random-secret-key-at-least-32-chars

# -------------------- 数据库配置 --------------------
DATABASE_URL=postgresql+asyncpg://anlingbao:anlingbao_dev_2025@postgres:5432/anlingbao
POSTGRES_USER=anlingbao
POSTGRES_PASSWORD=anlingbao_dev_2025
POSTGRES_DB=anlingbao

# -------------------- Redis 配置 --------------------
REDIS_URL=redis://redis:6379/0

# -------------------- AI 配置 --------------------
# Provider: mock | openai | deepseek | qwen | zhipu
# 生产模式（AZB_DEMO_MODE=false）下选择真实 Provider 时：
#   - 必须同时配置 AZB_AI_API_KEY 与 AZB_AI_BASE_URL
#   - 缺少任一凭据 → Gateway 抛出明确错误（绝不静默降级 Mock）
# 真实 AI Smoke Test：backend/scripts/phase9_real_ai_smoke.py（opt-in，见 .github/workflows/real-ai-smoke.yml）
AI_PROVIDER=mock
AI_API_KEY=sk-xxx
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o
AI_EMBEDDING_MODEL=text-embedding-3-small
AI_MAX_TOKENS=4096
AI_TEMPERATURE=0.7
AI_TIMEOUT=30                # 真实 Provider 请求超时（秒，connect 10s + 总 30s）

# -------------------- JWT 配置 --------------------
JWT_SECRET=change-me-to-another-random-secret-key
JWT_EXPIRE_HOURS=24
REFRESH_EXPIRE_DAYS=7

# -------------------- 日志配置 --------------------
LOG_LEVEL=INFO               # DEBUG | INFO | WARNING | ERROR

# -------------------- 上传配置 --------------------
UPLOAD_DIR=/app/uploads
MAX_UPLOAD_SIZE=50MB
```

---

## 4. 数据初始化流程

### 4.1 初始化命令

```bash
# Docker 环境下初始化
make init

# 或直接运行
docker compose exec backend python -m app.scripts.init_demo
```

### 4.2 初始化步骤详解

`make init` 执行以下 10 步初始化流程：

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1 | 创建数据库扩展 | 启用 `pgvector`、`uuid-ossp` 扩展 |
| 2 | 运行 Alembic 迁移 | 创建所有数据库表、索引、约束 |
| 3 | 创建默认管理员 | 账号 `admin` / 密码 `admin123`，角色：系统管理员 |
| 4 | 创建 Demo 用户 | 10 名代理人 + 2 名主管 + 1 名分公司管理员 + 1 名总部管理员，分布在 2 个机构、3 个团队 |
| 5 | 导入 Demo 产品 | 2 款产品（如：安诊保·尊享版、安诊保·基础版），含完整保障明细 |
| 6 | 导入 Demo 知识文档 | 30 篇文档（产品条款、理赔案例、健康知识、销售技巧等），自动切分 Chunk 并生成 Embedding |
| 7 | 导入陪练场景 | 20+ 个陪练场景（产品介绍、异议处理、需求挖掘、促成签单等），每个含多轮对话模板 |
| 8 | 导入话术库 | 30 条预置话术（覆盖不同产品、不同客户场景、不同风格） |
| 9 | 导入社区内容 | 30 条社区帖子（优秀话术分享、理赔案例、销售心得等） |
| 10 | 导入 Demo 客户 | 20 名客户（含基本信息、健康状况、购买记录、互动历史） |

### 4.3 Demo 账号清单

| 角色 | 账号 | 密码 | 所属机构 | 所属团队 |
|------|------|------|---------|---------|
| 系统管理员 | admin | admin123 | 总部 | — |
| 总部管理员 | hq_admin | demo123 | 总部 | — |
| 分公司管理员 | branch_admin | demo123 | 华东分公司 | — |
| 团队主管 | supervisor_1 | demo123 | 华东分公司 | 销售一组 |
| 团队主管 | supervisor_2 | demo123 | 华东分公司 | 销售二组 |
| 代理人 | agent_01 ~ agent_10 | demo123 | 华东分公司 | 销售一/二组 |

### 4.4 重新初始化

如需清空数据并重新初始化：

```bash
# 清除所有数据（包括数据库卷）
docker compose down -v

# 重新启动并初始化
docker compose up -d
make init
```

---

## 5. 本地开发环境

### 5.1 前置要求

| 工具 | 版本要求 | 说明 |
|------|---------|------|
| Docker + Docker Compose | Docker 24+ | 容器运行环境 |
| Node.js | 20+ | 前端构建 |
| Python | 3.12+ | 后端运行 |
| Git | 2.30+ | 版本管理 |
| Make | 任意 | 命令快捷方式（可选） |

### 5.2 完整启动流程

```bash
# 1. 克隆代码
git clone <repository-url> anlingbao-ai
cd anlingbao-ai

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，修改 SECRET_KEY 等敏感配置

# 3. 一键启动（Docker）
docker compose up -d

# 4. 初始化 Demo 数据
docker compose exec backend python -m app.scripts.init_demo

# 5. 访问系统
# 前端：http://localhost:3000
# API 文档：http://localhost:8000/docs
# 默认账号：admin / admin123
```

### 5.3 本地开发模式（非 Docker）

如需在本地直接运行前后端（便于调试和热重载）：

```bash
# === 1. 启动基础服务 ===
docker compose up -d postgres redis

# === 2. 后端 ===
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate        # Windows

# 安装依赖（含开发依赖）
pip install -e ".[dev]"

# 配置环境变量
cp ../.env.example ../.env

# 初始化数据库
alembic upgrade head

# 初始化 Demo 数据
python -m app.scripts.init_demo

# 启动开发服务器（热重载）
uvicorn app.main:app --reload --port 8000

# === 3. 前端 ===
cd frontend

# 安装依赖
npm install

# 启动开发服务器（热重载）
npm run dev
# 访问 http://localhost:5173
```

---

## 6. Docker 一键启动

### 6.1 常用命令

```bash
# === 完整启动 ===
# 后台启动所有服务
docker compose up -d

# 前台启动（查看实时日志）
docker compose up

# === 查看状态 ===
# 查看所有服务状态
docker compose ps

# 查看实时日志（所有服务）
docker compose logs -f

# 查看指定服务日志
docker compose logs -f backend
docker compose logs -f frontend

# === 服务管理 ===
# 重启单个服务
docker compose restart backend

# 重启所有服务
docker compose restart

# 停止所有服务（保留数据）
docker compose down

# 停止所有服务并清除数据卷
docker compose down -v

# === 构建与更新 ===
# 重新构建镜像
docker compose build

# 重新构建并启动
docker compose up -d --build

# === 进入容器 ===
# 进入后端容器
docker compose exec backend bash

# 进入数据库
docker compose exec postgres psql -U anlingbao -d anlingbao

# 进入 Redis
docker compose exec redis redis-cli
```

### 6.2 数据持久化

Docker Compose 使用命名卷（Named Volumes）持久化数据：

| 卷名 | 对应路径 | 内容 |
|------|---------|------|
| `anlingbao_pgdata` | `/var/lib/postgresql/data` | PostgreSQL 数据文件 |
| `anlingbao_redisdata` | `/data` | Redis 持久化文件 |
| `./data/uploads` (bind mount) | `/app/uploads` | 用户上传的文件 |

执行 `docker compose down -v` 会删除所有命名卷数据，请谨慎操作。

---

## 7. Makefile

项目根目录提供 Makefile，封装常用操作命令：

```makefile
.PHONY: help init dev up down restart logs build test clean

help:           ## 显示帮助信息
	@sed -n 's/^\(.*\):.*##\(.*\)/\1:\2/p' Makefile | column -t -s ':'

# ==================== 初始化 ====================

init:           ## 初始化 Demo 数据
docker compose exec backend python -m app.scripts.init_demo

# ==================== 开发模式 ====================

dev:            ## 启动本地开发环境（前后端热重载）
docker compose up -d postgres redis
	@echo "Starting backend..."
	cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000 &
	@echo "Starting frontend..."
	cd frontend && npm run dev &

# ==================== Docker 模式 ====================

up:             ## Docker 一键启动（后台）
docker compose up -d

up-init: up     ## 启动并初始化 Demo 数据
	@sleep 5
	make init

down:           ## 停止所有服务
docker compose down

down-clean:     ## 停止并清除所有数据
docker compose down -v

restart:        ## 重启所有服务
docker compose restart

logs:           ## 查看实时日志
docker compose logs -f

logs-backend:   ## 查看后端日志
docker compose logs -f backend

# ==================== 构建 ====================

build:          ## 重新构建所有镜像
docker compose build

build-no-cache: ## 重新构建（不使用缓存）
docker compose build --no-cache

# ==================== 测试 ====================

test:           ## 运行全部测试（单元 + 集成）
cd backend && pytest --cov=app
cd frontend && npm run test -- --run

test-e2e:       ## 运行 E2E 测试
npx playwright test

# ==================== 代码质量 ====================

lint:           ## 代码检查
cd backend && ruff check . && ruff format --check .
cd frontend && npm run lint

format:         ## 代码格式化
cd backend && ruff format .
cd frontend && npm run format

# ==================== 数据库 ====================

migrate:        ## 运行数据库迁移
docker compose exec backend alembic upgrade head

migrate-new:    ## 创建新迁移
	@read -p "Migration name: " name; \
	docker compose exec backend alembic revision --autogenerate -m "$$name"

migrate-rollback: ## 回滚上一次迁移
docker compose exec backend alembic downgrade -1

# ==================== 清理 ====================

clean:          ## 清理临时文件
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
find . -type d -name .vite -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
```

---

## 8. 生产环境预留

> 以下为生产环境部署预留方案，MVP 阶段暂不实施，但架构设计已考虑扩展性。

### 8.1 Nginx 反向代理

生产环境使用独立 Nginx 作为入口，处理 SSL 终止、负载均衡和静态资源缓存：

```nginx
# /etc/nginx/conf.d/anlingbao.conf
upstream backend {
    server backend:8000;
    # 水平扩展时添加更多 server
    # server backend-2:8000;
    # server backend-3:8000;
}

server {
    listen 443 ssl http2;
    server_name anlingbao.example.com;

    ssl_certificate     /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    client_max_body_size 50M;

    location /api/ {
        proxy_pass http://backend/api/;
        proxy_buffering off;          # SSE 支持
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
}

# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name anlingbao.example.com;
    return 301 https://$server_name$request_uri;
}
```

### 8.2 SSL/TLS 证书

- **证书来源**：Let's Encrypt（免费）或企业内部 CA
- **自动续期**：certbot + cron 定时任务
- **证书路径**：`/etc/nginx/ssl/cert.pem`、`/etc/nginx/ssl/key.pem`

### 8.3 数据库备份策略（Task 38 校准：Pilot 实现 + 外部依赖）

> 历史版本曾规划「每日 02:00 全量 + WAL 增量 + 云快照」但**无对应实现**（审计确认 0 命中 pg_dump）。
> Task 38 已落地可执行、可验证的 Pilot 级方案；正式生产自动备份/对象存储为外部依赖。

| 能力 | 状态 | 说明 |
|------|------|------|
| 逻辑备份（pg_dump custom） | ✅ **IMPLEMENTED + CLOUD VERIFIED** | `scripts/backup_database.sh`，时间戳 + size/sha256 摘要，失败非 0 |
| 恢复（pg_restore 干净目标） | ✅ **IMPLEMENTED + CLOUD VERIFIED** | `scripts/restore_database.sh`，演练 restored==baseline（含 pgvector） |
| 云端演练 | ✅ `database-backup-restore.yml` | PG16+pgvector：migration→seed→backup→restore→verify→app health；push 仅备份路径 / workflow_dispatch |
| 自动调度（每日/每小时） | ⬜ **外部依赖** | 需外部 scheduler / 云 DB 托管备份策略（如 cron + 独立对象存储） |
| 增量/WAL/PITR、云快照、跨地域灾备 | ⬜ **外部依赖** | 正式生产加固项，见 database-backup-audit.md |

```bash
# 手动备份（凭据环境变量注入，勿硬编码）
AZB_DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db \
  AZB_BACKUP_DIR=/tmp/backups bash scripts/backup_database.sh
# 手动恢复（目标库）
AZB_DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db \
  bash scripts/restore_database.sh /tmp/backups/anzhenbao_*.dump
```

### 8.4 日志轮转

```bash
# /etc/logrotate.d/anlingbao
/var/log/anlingbao/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

### 8.5 监控预留

| 监控项 | 工具 | 说明 |
|--------|------|------|
| 指标采集 | OpenTelemetry SDK（后端集成） | 应用指标标准化采集 |
| 时序存储 | Prometheus | 存储和查询监控指标 |
| 可视化 | Grafana | 仪表盘展示 |
| 日志聚合 | 结构化 JSON 日志 + ELK（可选） | 集中式日志管理 |
| 告警 | Prometheus AlertManager | 异常告警通知 |

关键监控指标：
- API 请求量、响应时间、错误率
- AI 调用延迟、Token 消耗、失败率
- RAG 检索延迟、命中率
- 数据库连接池使用率、慢查询
- Redis 缓存命中率、内存使用
- SSE 连接数、并发用户数

### 8.6 水平扩展预留

- **后端无状态化**：所有会话状态存储在 Redis，后端可随意水平扩展
- **数据库读写分离**：预留 PostgreSQL 只读副本配置
- **前端 CDN**：静态资源可推送至 CDN
- **AI Gateway 独立部署**：AI 网关可独立为微服务

---

## 9. CI/CD 预留

### 9.1 GitHub Actions 工作流

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  # ==================== 代码质量检查 ====================
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Backend Lint
        run: |
          cd backend
          pip install ruff
          ruff check .
          ruff format --check .
      - name: Frontend Lint
        run: |
          cd frontend
          npm ci
          npm run lint

  # ==================== 后端测试 ====================
  backend-test:
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - name: Run Tests
        run: |
          cd backend
          pip install -e ".[dev]"
          pytest --cov=app --cov-report=xml
      - name: Upload Coverage
        uses: codecov/codecov-action@v4

  # ==================== 前端测试 ====================
  frontend-test:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - name: Run Tests
        run: |
          cd frontend
          npm ci
          npm run test -- --run

  # ==================== E2E 测试 ====================
  e2e-test:
    runs-on: ubuntu-latest
    needs: [backend-test, frontend-test]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Start Services
        run: docker compose up -d
      - name: Init Demo Data
        run: | 
          sleep 10
          docker compose exec backend python -m app.scripts.init_demo
      - name: Run E2E Tests
        run: npx playwright test
      - uses: actions/upload-artifact@v4
n        if: failure()
        with:
          name: playwright-report
          path: playwright-report/

  # ==================== 构建与部署 ====================
  deploy:
    runs-on: ubuntu-latest
    needs: e2e-test
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Build and Deploy
        run: |
          echo "Deploy to staging/production server"
          # ssh deploy@server "cd /opt/anlingbao && git pull && docker compose up -d --build"
```

---

## 10. 故障排查

### 10.1 常见问题

| 问题 | 现象 | 解决方案 |
|------|------|---------|
| 后端启动失败 | `docker compose logs backend` 显示数据库连接错误 | 检查 `.env` 中 `DATABASE_URL` 是否正确；确认 postgres 容器已启动且健康 |
| 前端 502 Bad Gateway | 浏览器访问 3000 端口返回 502 | 确认 backend 容器已启动且 healthcheck 通过；检查 Nginx 配置中 `proxy_pass` 地址 |
| AI 功能无响应 | 聊天/分析/陪练功能无返回 | 确认 `.env` 中 `AI_PROVIDER` 配置正确；如使用 mock，确认 MockProvider 正常工作 |
| Demo 数据未加载 | 登录后数据为空 | 运行 `make init` 重新初始化；检查后端日志是否有报错 |
| SSE 连接断开 | AI 对话中途停止 | 检查 Nginx `proxy_buffering off` 配置；检查网络超时设置 |
| pgvector 扩展未启用 | 迁移失败或 RAG 报错 | 手动执行 `CREATE EXTENSION IF NOT EXISTS vector;` |
| 端口冲突 | 启动时报 `port already in use` | 修改 `docker-compose.yml` 中的端口映射，或停止占用端口的进程 |
| 权限错误 | Docker 挂载目录权限问题 | 确保 `data/uploads` 目录有正确读写权限 |

### 10.2 诊断命令

```bash
# 查看所有容器状态
docker compose ps

# 查看后端日志（最近 100 行）
docker compose logs --tail 100 backend

# 进入后端容器检查
 docker compose exec backend bash

# 检查数据库连接
docker compose exec postgres psql -U anlingbao -d anlingbao -c "SELECT 1;"

# 检查 Redis 连接
docker compose exec redis redis-cli ping

# 检查磁盘空间
df -h

# 检查 Docker 资源使用
docker stats

# 查看端口占用
ss -tlnp | grep -E '(3000|8000|5432|6379)'
```

### 10.3 日志级别调整

在 `.env` 中调整日志级别获取更详细的调试信息：

```bash
# 开发调试时使用 DEBUG 级别
LOG_LEVEL=DEBUG

# 正常运行使用 INFO 级别
LOG_LEVEL=INFO

# 生产环境使用 WARNING 级别
LOG_LEVEL=WARNING
```



---

## Task 30 Deployment Gate 复核（Production Readiness Review）

- docker-compose.prod.yml（PG16+pgvector / Redis7 / Backend / Frontend）：**PASS** —— healthcheck + depends_on healthy + 持久卷 + 资源限制 + `restart: always`
- Production Validation（compose 全栈 build/up/ready/alembic/seed/phase7/phase8/pytest-on-PG/vitest/build/tsc）：**PASS**（Task 29 最终代码 2f183e3 ✅）
- **滚动/零停机部署：NOT IMPLEMENTED**（PILOT 可接受；正式生产需蓝绿/滚动 + 迁移窗口）
- **多实例水平扩展：PARTIAL（P2）**（uvicorn --workers 4 单容器；多容器需 Redis 化 rate limit/session）
- **数据库备份：IMPLEMENTED / CLOUD VERIFIED（Task 38，Pilot 级）**——backup+restore 云端演练全绿；正式生产自动调度/对象存储为外部依赖
- 结论：内部试点级部署就绪；正式生产上线前需补备份、滚动部署、监控告警（详见 production-readiness-review.md）

---

## 11. 部署一致性校准（Task 35）

### 11.1 版本号统一

- `config.py::APP_VERSION` 由 `1.0.0-rc.1` 对齐为 `0.1.0`（与 pyproject.toml / frontend package.json / README 一致）；`/api/v1/health` `/ready` `/health/detail` 对外版本号同步正确。

### 11.2 前端镜像构建对齐 CI 门禁

- `frontend/Dockerfile` 由 `npx vite build`（绕过 tsc）改为 `RUN npm run build`（= tsc -b && vite build）——P1-6 已于 Task 19 修复，生产镜像构建与 CI 硬门禁一致，删除过时注释。

### 11.3 seed.py 角色-权限绑定修复（Task 35 实测发现）

- `scripts/seed.py` 绑定插入缺少 `await` → 协程从未执行，`role_permissions` 绑定静默不落库（seed 打印仅为打印）。修复后权限关系真正写入；backend-pg 幂等回归测试（test_seed_idempotency.py 3 用例）覆盖：首次/二次运行成功、无重复、绑定正确。

### 11.4 部署须知（记录，不改变行为）

- **demo 用户默认凭据**：`scripts/seed.py` 无条件创建 4 个演示用户（密码 `888888`、`demo_mode=True`），与 DEMO_MODE 无关。内部试点可接受；**正式生产执行 seed 后必须轮换/停用这些账号**（PRODUCTION READY 前置项，与 B1/B2 并列）。
- **`.env.production` 路径**：compose.prod `env_file: .env.production` 指向**仓库根目录**（未提交，部署时创建）；模板位于 `backend/.env.production`（CHANGE_ME 占位），部署时复制到根目录并填真实值；CI（production-validation）内联生成根 `.env.production`。
- seed 幂等 ✅（exists-check-skip，重复执行安全）；`alembic upgrade head && python -m scripts.seed` 由 compose.prod 启动命令自动执行。

> **Task 36 RC Final Audit 复核**（docs/release-candidate-audit.md）：Deployment 六项检查（Docker/compose/env/healthcheck/migration 启动/CI pipeline）全部 PASS（PILOT 级）；多实例/滚动部署未实现（P2 A1/A5）为 PRODUCTION CANDIDATE 差距之一。

## 12. Observability 与告警（Task 39）

- **Signals Ready（已实现）**：/ready 依赖异常返回 **503 + READINESS_FAILED**（编排可据此摘流）；request 结构化日志含
  request_id/user_id/organization_id/duration_ms/error_code；AI Provider 错误日志统一 `error_code`
  （401/403/429/5xx/连接）+ 不记录 HTTP body；RAG 检索日志含 retrieval_count/latency_ms。
- **健康检查语义**：`/health` = liveness（进程存活）；`/ready` = PostgreSQL + Redis + AI provider（demo 模式依赖豁免）；
  `/health/detail` = masked URL + middleware 栈 + metrics。
- **外部告警平台 = Integration Required**：Prometheus/Alertmanager 抓取与告警规则、云日志/Sentry、日志采集管道需在正式生产接入
  （本阶段以结构化事件与 error_code 提供稳定可消费信号，不假装已接入）。
