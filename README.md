# 安诊保 AI 副驾（Anzhenbao AI Copilot）

> 面向华安保险一线代理人的 **AI 销售赋能工作台**：企业知识库 + RAG + AI Gateway + 合规引擎，
> 为代理人提供产品问答、客户 360、话术生成、AI 陪练、社区沉淀等能力。

| 字段 | 内容 |
|------|------|
| 产品名称 | 安诊保 AI 副驾（Anzhenbao AI Copilot） |
| 所属公司 | 华安保险（Sinosafe Insurance） |
| 项目版本 | `v0.1.0`（`backend/pyproject.toml` / `frontend/package.json` 一致） |
| 发布就绪状态 | **PRODUCTION CANDIDATE**（Task 42 Security Final Review；Accepted Risks 见 [docs/security-final-review.md](docs/security-final-review.md)） |
| 仓库语言 | Python（后端）+ TypeScript/React（前端） |

---

## ⚠️ Known Limitations / Accepted Risks（当前）

| 项 | 说明 |
|----|------|
| 演示凭据 `888888` | demo 账号密码未轮换（生产上线前置，Accepted Risk） |
| token localStorage | 前端 token 存 localStorage（XSS 面；Task 42 记录为 Accepted Risk，不贸然重构） |
| 外部告警平台 | Prometheus/Alertmanager、云日志/Sentry 未接入（Integration Required） |
| 云托管备份 / Redis HA | 生产自动备份、多地域灾备、Redis 高可用为外部依赖（Task 38/40 记录） |
| 滚动发布 / 渗透测试 | 未配置 / 未执行（Accepted Risk） |
| 真实性能基准 | Cloud CI Capacity Baseline（非 SLA）；真实硬件/真实 AI 未测（Task 41 记录） |
| 上传病毒扫描 | 上传 10MB 限制已实现；病毒扫描未实现 |
| 环境 badge | 生产环境无环境标识 badge（P2） |

> 完整 P1/P2 / Accepted Risks 见 [docs/security-final-review.md](docs/security-final-review.md)。

---

## ✅ 已真实验证的能力（Verified Facts）

| 项 | 状态 |
|----|------|
| 真实 PostgreSQL 16 + pgvector | ✅ Production Validation 通过 |
| 真实 Redis | ✅ Production Validation 通过 |
| 真实 AI Provider（OpenAI 兼容端点） | ✅ Real AI Smoke 最近 PASS @ 94ce52f（opt-in workflow，`REAL_AI_SMOKE_TEST` 开关；缺 Key 时明确跳过） |
| Docker Production Validation | ✅ 4 容器（postgres/redis/backend/frontend）全栈通过 |
| Backend 测试 | ✅ CI 全绿（后端单元 + API 集成 + PostgreSQL 集成） |
| Frontend 测试 / 构建 | ✅ Vitest **107 passed** + Vite build ✓ + **tsc -b 0 errors（hard gate 已恢复，Task 19）** |
| Playwright E2E | ✅ **27 passed**：Stage 1/2 + Golden Flow（Task 29） |

> 详细测试数字以 [docs/project-status.md](docs/project-status.md)（唯一事实来源）与最新 CI 为准。

---

## ✨ 功能列表（与当前代码一致）

### 核心功能

| 模块 | 功能 | 实现状态 |
|------|------|----------|
| **AI 产品专家** | 产品问答（RAG + SSE 流式 + 参考来源/拒答） | ✅ 已实现并 E2E 验证 |
| **客户 360** | 客户画像、互动、跟进、AI 分析入口 | ✅ 已实现并 E2E 验证 |
| **AI 话术** | 多风格话术生成（SSE）+ RAG 知识依据（Citation UI）+ 合规徽章 | ✅ 已实现并 E2E 验证 |
| **AI 陪练** | 模拟客户对话，会话 + 评分 | ✅ 已实现（API + 页面） |
| **AI 社区** | 帖子/评论/点赞/收藏 + AI 摘要 | ✅ 已实现（API + 页面） |
| **合规检查** | 话术合规引擎（GREEN/YELLOW/RED + 规则明细） | ✅ 已实现并 E2E 验证 |
| **工作台** | Dashboard 统计概览 | ✅ 已实现并 E2E 验证 |
| **成长体系** | 概览 / 课程 / 排行榜 / 成就 | ✅ 已实现（API + 页面） |
| **通知中心** | 列表 / 已读 / 偏好 | ✅ 已实现（API + 页面） |
| **知识库管理** | 知识库 / 文档 CRUD + 发布 | ✅ 已实现（API + 页面） |

### 管理功能

| 模块 | 功能 | 实现状态 |
|------|------|----------|
| 用户管理 | RBAC（7 角色）+ 禁用/启用 | ✅ 已实现（管理后台） |
| 审计日志 | 管理操作审计 | ✅ 已实现 |
| 合规审核 | 规则管理 + 人工审核流 | ✅ 已实现 |
| 运营分析 | 概览 / AI 用量 / 培训 / 社区 | ✅ 已实现 |
| 设置 | 系统设置 | ✅ 已实现 |

---

## 🛠 技术栈（与真实配置一致）

### 前端（`frontend/package.json`）

| 技术 | 版本 | 用途 |
|------|------|------|
| React | ^19.2 | UI 框架 |
| TypeScript | ~6.0 | 类型安全 |
| Vite | ^8.2 | 构建工具 |
| Tailwind CSS | ^4.3 | 原子化样式 |
| React Router | ^7.18 | 客户端路由 |
| TanStack Query | ^5.101 | 服务端状态管理 |
| Zustand | ^5.0 | 客户端状态管理 |
| Axios | ^1.19 | HTTP 请求 |
| Vitest / Testing Library | ^4.1 / ^7 | 前端测试 |
| Playwright | ^1.49 | E2E 测试 |

### 后端（`backend/pyproject.toml`，hatchling 构建）

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | >=3.12 | 运行时 |
| FastAPI | >=0.115 | Web 框架（SSE 流式） |
| SQLAlchemy 2.0 | >=2.0.30 | ORM（异步） |
| asyncpg | >=0.29 | PostgreSQL 异步驱动 |
| Alembic | >=1.13 | 数据库迁移（7 个迁移，30 张表） |
| pgvector | >=0.3 | 向量检索（1536 维） |
| Redis | >=5.0（服务端 7） | 缓存 / 限流 |
| Pydantic v2 | >=2.7 | 数据校验 |
| python-jose | >=3.3 | JWT 认证 |
| httpx / structlog | — | HTTP 客户端 / 结构化日志 |

### 基础设施

| 技术 | 用途 |
|------|------|
| PostgreSQL 16 + pgvector | 关系型 + 向量检索（HNSW） |
| Redis 7 | 缓存 / 限流 |
| Nginx | 前端静态资源 + `/api` 反向代理（SSE 支持） |
| Docker Compose | 开发（`docker-compose.yml`）与生产（`docker-compose.prod.yml`） |

---

## 📁 项目结构

```
.
├── .github/workflows/        # CI：backend-tests / e2e-playwright / production-validation / real-ai-smoke
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/           # 路由层（health/auth/ai/knowledge/customer/training/script/community/admin/growth/notification/dashboard）
│   │   ├── services/         # 业务逻辑（含 script_service / ai_service / compliance_service）
│   │   ├── repositories/     # 数据访问层
│   │   ├── models/           # SQLAlchemy 模型（30 张表）
│   │   ├── schemas/          # Pydantic 模型
│   │   ├── core/             # 配置（settings/security/deps）
│   │   ├── ai/               # AI Gateway + Providers（mock/openai/deepseek/qwen）
│   │   ├── rag/              # RAG：retriever（向量+BM25+RRF）/ pipeline / safety（拒答+置信度）
│   │   └── utils/
│   ├── alembic/versions/     # 7 个迁移
│   ├── scripts/              # seed.py / e2e_seed_knowledge.py / phase* 验证脚本
│   ├── tests/                # pytest（单元 + API 集成 + PG 集成）
│   ├── Dockerfile
│   └── pyproject.toml        # hatchling 构建（无 requirements.txt/setup.py）
├── frontend/                 # React + Vite + TS 前端
│   ├── src/
│   │   ├── app/              # 路由（21 条）
│   │   ├── features/         # 页面（auth/dashboard/customers/product-qa/scripts/training/community/growth/...）
│   │   ├── components/       # UI 组件
│   │   ├── services/         # API 客户端（含 SSE 流式）
│   │   └── stores/           # Zustand
│   ├── e2e/                  # Playwright（auth/dashboard/customers/product-qa/scripts）
│   ├── Dockerfile
│   └── nginx.conf
├── docs/                     # 项目文档（archive/ 为历史归档）
├── scripts/deploy.sh         # 生产部署引导
├── .env.example              # 环境变量模板（复制参考）
├── docker-compose.yml        # 开发编排
├── docker-compose.prod.yml   # 生产编排
├── Makefile                  # 常用命令
├── README.md
└── worklog.md                # 开发日志（含里程碑摘要）
```

---

## 🚀 快速开始

### 前置要求

| 工具 | 版本要求 |
|------|----------|
| Docker + Docker Compose | Docker 24+ |
| Node.js | 20+（本地前端开发） |
| Python | 3.12+（本地后端开发） |
| Make | 可选 |

### 方式一：Docker 一键启动（推荐）

```bash
git clone <repository-url> anzhenbao-ai
cd anzhenbao-ai

# 开发编排（AZB_DEMO_MODE=true + mock AI，无需外部凭据）
docker compose up -d --build

# 前端：http://localhost:3000
# 后端 API 文档：http://localhost:8000/docs
# 健康检查：http://localhost:8000/api/v1/health
```

### 方式二：本地开发（热重载）

```bash
git clone <repository-url> anzhenbao-ai
cd anzhenbao-ai

# 1. 启动基础服务（PostgreSQL + Redis）
docker compose up -d postgres redis

# 2. 后端
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. 前端（新终端）
cd frontend
npm install
npm run dev                        # http://localhost:3000（/api 代理 → :8000）
```

### Makefile 常用命令

```bash
make help       # 显示所有命令
make init       # 初始化（依赖 + 迁移 + 种子）
make up         # docker compose up -d
make backend    # 本地启动后端
make frontend   # 本地启动前端
make migrate    # alembic upgrade head
make seed       # 种子数据
make test       # pytest
make build      # 前端构建
```

---

## 🧪 测试体系

| 层级 | 工具 | 命令 | 环境 |
|------|------|------|------|
| 后端单元/集成 | pytest + pytest-asyncio | `cd backend && pytest` | 本地/CI |
| PostgreSQL 集成 | pytest（`AZB_TEST_DATABASE_URL`） | CI `backend-pg` job | CI 真实 PG16+pgvector |
| 前端单元 | Vitest | `cd frontend && npm test` | 本地/CI |
| E2E | Playwright | `cd frontend && npm run test:e2e` | CI（真实 PG+Redis+真实 AI） |
| Real AI Smoke | phase9 脚本（opt-in workflow） | `.github/workflows/real-ai-smoke.yml` | CI 手动触发（真实 DashScope/Qwen） |
| Production Validation | docker compose prod 全栈 | `.github/workflows/production-validation.yml` | CI |

> **三类 AI 测试严格区分**：Mock AI（确定性/免费/PR CI）→ Production-like（PG + AI wiring）→ Real AI Smoke（真实 DashScope/Qwen）。详见 [docs/testing.md](docs/testing.md)。

---

## 🔧 环境变量（Demo vs Production）

所有后端变量使用 `AZB_` 前缀，完整清单见 [.env.example](.env.example) 与 `backend/.env.production`（占位模板）。

### Demo 模式（`AZB_DEMO_MODE=true`）

- AI Provider 自动使用 `mock`（无需 API Key）
- 内存/种子数据，可离线运行
- 适合演示与本地开发

### Production-like 模式（`AZB_DEMO_MODE=false`）

- 真实 PostgreSQL + Redis（`docker-compose.prod.yml`）
- 真实 AI Provider（DashScope/Qwen 等 OpenAI 兼容端点），需配置 `AZB_AI_API_KEY` 等
- 缺 Key 时 Gateway **明确报错**，不静默降级 Mock

---

## 👤 Demo 账号（DEMO ONLY / NON-PRODUCTION）

Demo 模式预置测试账号，验证码统一为 `888888`：

| 姓名 | 手机号 | 角色 |
|------|--------|------|
| 林思远 | `13800138000` | 代理人 (AGENT) |
| 张伟 | `13800138001` | 团队长 (TEAM_LEADER) |
| 李芳 | `13800138002` | 分公司管理员 (BRANCH_ADMIN) |
| 王强 | `13800138003` | 系统管理员 (SYSTEM_ADMIN) |

> ⚠️ 以上均为演示数据，**禁止**在生产环境使用。

---

## 📚 文档索引

| 文档 | 说明 |
|------|------|
| [项目状态（唯一事实来源）](docs/project-status.md) | 当前 Phase / HEAD / 验证记录 / P0-P2 |
| [当前状态审计](docs/current-state-audit.md) | 最近一次完整审计 |
| [发布就绪基线](docs/release-readiness.md) | 发布能力检查表 |
| [仓库清理审计](docs/repository-cleanup-audit.md) | 本次清理决策记录 |
| [发布验证快照](docs/release-verification.md) | 本次 Release Baseline 真实验证快照 |
| [系统架构](docs/architecture.md) | 分层架构 / 数据流 |
| [API 文档](docs/api.md) | 端点清单（实际 92 端点）与设计参考 |
| [数据库设计](docs/database.md) | 30 张表 / 10 迁移（head=0010_audit_log_org_scope） |
| [RAG 设计](docs/rag.md) | 向量+BM25+RRF / 置信度门控 / 产品边界（Implemented/Validated/Planned 标注） |
| [AI Agent 设计](docs/ai-agents.md) | Gateway / Product QA / Script / Training / Community（含 Planned 标注） |
| [合规设计](docs/compliance.md) | GREEN/YELLOW/RED / 规则引擎 |
| [安全设计](docs/security.md) | JWT / RBAC / 限流 / Prompt Injection / Secret 管理 |
| [测试体系](docs/testing.md) | 当前实际测试（Mock vs Real AI 区分） |
| [部署方案](docs/deployment.md) | Docker Compose / 生产部署 |
| [信息架构](docs/information-architecture.md) | 22 条前端路由 |
| [用户流程](docs/user-flows.md) | 已实现 vs 未来流程 |
| [产品需求](docs/product-requirements.md) | 需求对齐（Implemented/Partial/Planned） |
| [技术决策](docs/decisions.md) | ADR |
| [开发日志](worklog.md) | 含当前里程碑摘要 |

---

## 📄 License

华安保险内部项目，未经授权不得对外分发。
