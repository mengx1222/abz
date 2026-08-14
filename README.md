# 安诊保 AI 副驾

> 面向华安保险一线代理人的 **AI 销售赋能工作台**，以大语言模型（LLM）为核心驱动，通过 RAG 检索增强生成技术确保产品知识的准确性和合规性。

| 字段 | 内容 |
|------|------|
| 产品名称 | 安诊保 AI 副驾（Anzhenbao AI Copilot） |
| 所属公司 | 华安保险（Sinosafe Insurance） |
| 当前版本 | v1.0.0 MVP |
| 文档状态 | 开发中 |

---

## ✨ 功能列表

### 核心功能（MVP）

| 模块 | 功能 | 说明 |
|------|------|------|
| **AI 产品专家** | 产品问答 | 自然语言对话，精准获取产品信息，每条回答附带官方文档出处 |
| **客户 360°** | 客户画像 | 客户基本信息、健康状况、购买记录、互动历史全景视图 |
| **AI 话术** | 话术生成 | 根据客户特征和销售场景，自动生成多种风格的销售话术 |
| **AI 陪练** | 模拟演练 | 模拟真实客户对话场景，三维评分（专业度、合规性、亲和力） |
| **AI 社区** | 经验沉淀 | 优秀话术分享、理赔案例、销售心得等社区互动 |
| **合规检查** | 话术合规 | 内置合规引擎，8 大违规类型自动检测 |
| **工作台** | 数据看板 | 销售漏斗、待办事项、关键指标一览 |
| **成长体系** | 技能提升 | 学习路径、培训任务、能力评估 |

### 管理功能

| 模块 | 功能 | 说明 |
|------|------|------|
| **用户管理** | RBAC 权限 | 7 种角色，行级数据权限控制 |
| **知识库管理** | 文档维护 | 产品条款、理赔案例、健康知识等知识文档管理 |
| **管理后台** | 运营配置 | 机构/团队管理、数据统计、审计日志 |
| **消息中心** | 通知推送 | 系统通知、互动提醒 |

---

## 🛠 技术栈

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 19 | UI 框架 |
| TypeScript | 6 | 类型安全 |
| Vite | 8 | 构建工具 |
| Tailwind CSS | 4 | 原子化样式 |
| React Router | 7 | 客户端路由 |
| React Query (TanStack Query) | 5 | 服务端状态管理 |
| Zustand | 5 | 客户端状态管理 |
| Axios | 1 | HTTP 请求 |

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.12+ | 运行时 |
| FastAPI | 0.115+ | Web 框架 |
| Uvicorn | — | ASGI 服务器 |
| SQLAlchemy | 2.0+ | ORM（异步） |
| Alembic | — | 数据库迁移 |
| asyncpg | — | PostgreSQL 异步驱动 |
| pgvector | 0.7+ | 向量检索扩展 |
| Redis | 7.0+ | 缓存 / 限流 |
| Pydantic | 2.0+ | 数据校验 |
| python-jose | — | JWT 认证 |
| bcrypt | — | 密码哈希 |

### 基础设施

| 技术 | 用途 |
|------|------|
| PostgreSQL 16 + pgvector | 关系型数据库 + 向量检索 |
| Redis 7 | 缓存 / 限流 / 会话存储 |
| Nginx | 反向代理 / 静态资源服务 |
| Docker + Docker Compose | 容器化部署 |

---

## 📁 项目结构

```
anzhenbao-ai/
├── frontend/                    # 前端项目（React + Vite + TypeScript）
│   ├── public/                  # 静态资源
│   ├── src/
│   │   ├── App.tsx              # 应用入口
│   │   ├── main.tsx             # 渲染入口
│   │   ├── index.css            # 全局样式
│   │   └── assets/              # 图片等资源
│   ├── Dockerfile               # 前端多阶段构建
│   ├── nginx.conf               # Nginx 配置（SPA + API 代理 + SSE）
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── backend/                     # 后端项目（Python + FastAPI）
│   ├── app/
│   │   ├── main.py              # FastAPI 应用入口
│   │   ├── api/                 # API 路由层（api/v1/）
│   │   ├── services/            # 业务逻辑层
│   │   ├── repositories/        # 数据访问层
│   │   ├── models/              # SQLAlchemy 模型
│   │   ├── schemas/             # Pydantic 数据模型
│   │   ├── core/                # 核心配置（settings、security、deps）
│   │   ├── ai/                  # AI 模块（Gateway、RAG、Providers）
│   │   └── utils/               # 工具函数
│   ├── alembic/                 # 数据库迁移
│   │   ├── env.py               # Alembic 异步环境配置
│   │   ├── script.py.mako       # 迁移模板
│   │   └── versions/            # 迁移版本文件
│   ├── alembic.ini              # Alembic 配置
│   ├── scripts/
│   │   └── seed.py              # 种子数据脚本
│   ├── Dockerfile               # 后端多阶段构建
│   ├── requirements.txt         # Python 依赖
│   └── setup.py                 # 包安装配置
│
├── docs/                        # 项目文档
│   ├── architecture.md          # 系统架构
│   ├── api.md                   # API 接口设计
│   ├── database.md              # 数据库设计
│   ├── security.md              # 安全设计
│   ├── deployment.md            # 部署方案
│   ├── testing.md               # 测试策略
│   ├── product-requirements.md  # 产品需求文档
│   ├── ai-agents.md             # AI Agent 设计
│   ├── compliance.md            # 合规设计
│   ├── information-architecture.md # 信息架构
│   ├── user-flows.md            # 用户流程
│   ├── decisions.md             # 技术决策记录
│   ├── rag.md                   # RAG 检索设计
│   └── project-audit.md         # 项目审计
│
├── docker-compose.yml           # Docker Compose 编排
├── .env.example                 # 环境变量模板
├── Makefile                     # 命令快捷方式
└── README.md                    # 本文件
```

---

## 🚀 快速开始

### 前置要求

| 工具 | 版本要求 | 说明 |
|------|---------|------|
| Docker + Docker Compose | Docker 24+ | 容器运行环境 |
| Node.js | 20+ | 前端构建 |
| Python | 3.12+ | 后端运行 |
| Git | 2.30+ | 版本管理 |
| Make | 任意 | 命令快捷方式（可选） |

### 方式一：Docker 一键启动（推荐）

```bash
# 1. 克隆代码
git clone <repository-url> anzhenbao-ai
cd anzhenbao-ai

# 2. 配置环境变量
cp .env.example .env
# 根据需要修改 .env 中的配置

# 3. 启动所有服务
docker compose up -d

# 4. 访问系统
# 前端界面：http://localhost:3000
# API 文档：http://localhost:8000/docs
# 默认账号：admin / admin123
```

### 方式二：本地开发模式

适用于需要前后端热重载的开发场景：

```bash
# 1. 克隆代码并配置环境变量
git clone <repository-url> anzhenbao-ai
cd anzhenbao-ai
cp .env.example .env

# 2. 启动基础服务（PostgreSQL + Redis）
docker compose up -d postgres redis

# 3. 后端启动
cd backend
python -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate          # Windows
pip install -e ".[dev]"
alembic upgrade head               # 运行数据库迁移
python scripts/seed.py             # 导入种子数据
uvicorn app.main:app --reload --port 8000

# 4. 前端启动（新终端）
cd frontend
npm install
npm run dev                       # 访问 http://localhost:5173
```

### 使用 Makefile 快捷命令

```bash
make help       # 显示所有可用命令
make init       # 一键初始化（依赖安装 + 迁移 + 种子数据）
make up         # 启动所有 Docker 服务
make down       # 停止所有服务
make logs       # 查看实时日志
make backend    # 本地启动后端
make frontend   # 本地启动前端
make migrate    # 运行数据库迁移
make seed       # 导入种子数据
make test       # 运行全部测试
make clean      # 清理所有数据（包括数据库卷）
```

---

## 🔧 环境变量说明

所有环境变量详见 [.env.example](.env.example)，以下为核心变量说明：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `APP_ENV` | 运行环境 | `development` |
| `DEMO_MODE` | 是否启用 Demo 模式 | `true` |
| `DATABASE_URL` | PostgreSQL 异步连接串 | — |
| `REDIS_URL` | Redis 连接地址 | — |
| `JWT_SECRET_KEY` | JWT 签名密钥 | — |
| `AI_PROVIDER` | AI 服务商（mock/openai/deepseek/qwen/zhipu） | `mock` |
| `AI_API_KEY` | AI API 密钥 | — |
| `AI_MODEL` | 对话模型名称 | `gpt-4o` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

> ⚠️ **生产环境安全提醒**：
> - 必须将 `DEMO_MODE` 设为 `false`
> - 必须修改 `SECRET_KEY`、`JWT_SECRET_KEY`、`DATA_ENCRYPTION_KEY` 为强随机密钥
> - 必须修改所有默认密码

---

## 👤 Demo 账号

Demo 模式下预置以下测试账号（密码统一为 `demo123`）：

| 角色 | 账号 | 所属机构 | 所属团队 |
|------|------|---------|---------|
| 系统管理员 | `admin` | 总部 | — |
| 总部管理员 | `hq_admin` | 总部 | — |
| 分公司管理员 | `branch_admin` | 华东分公司 | — |
| 团队主管 | `supervisor_1` | 华东分公司 | 销售一组 |
| 团队主管 | `supervisor_2` | 华东分公司 | 销售二组 |
| 代理人 | `agent_01` ~ `agent_10` | 华东分公司 | 销售一/二组 |

---

## 📖 开发指南

### 代码规范

- **后端**：遵循 PEP 8，使用 Ruff 进行代码检查和格式化
- **前端**：遵循 ESLint + Prettier 规则
- **Git 提交**：遵循 Conventional Commits 规范

### 分层架构

后端采用严格的分层架构：

```
Router（API 路由）→ Service（业务逻辑）→ Repository（数据访问）→ Model（数据模型）
```

- **Router 层**（`app/api/v1/`）：接收请求、参数校验、调用 Service、返回响应
- **Service 层**（`app/services/`）：核心业务逻辑，不直接操作数据库
- **Repository 层**（`app/repositories/`）：数据库查询封装
- **Model 层**（`app/models/`）：SQLAlchemy ORM 模型定义

### 数据库迁移

```bash
# 创建新迁移
cd backend
alembic revision --autogenerate -m "描述迁移内容"

# 运行迁移
alembic upgrade head

# 回滚上一次迁移
alembic downgrade -1
```

---

## 🧪 测试

| 层级 | 工具 | 命令 |
|------|------|------|
| 后端单元/集成 | pytest + pytest-asyncio | `cd backend && pytest --cov=app` |
| 前端单元 | Vitest | `cd frontend && npx vitest` |
| E2E 端到端 | Playwright | `npx playwright test` |

AI 功能测试均通过 MockProvider 提供确定性响应，确保测试可重复。

---

## 🚢 部署

### Docker 部署（推荐）

```bash
# 构建并启动
docker compose up -d --build

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f
```

### 数据初始化

```bash
# Docker 环境
docker compose exec backend python -m app.scripts.init_demo

# 本地环境
cd backend && python scripts/seed.py
```

### 数据清理与重置

```bash
# 停止服务并删除所有数据卷
docker compose down -v

# 重新启动
docker compose up -d
```

---

## 📚 文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| 系统架构 | [docs/architecture.md](docs/architecture.md) | 整体架构设计、模块划分 |
| 产品需求 | [docs/product-requirements.md](docs/product-requirements.md) | PRD、用户角色、功能需求 |
| API 接口 | [docs/api.md](docs/api.md) | RESTful API 设计、错误码、SSE 规范 |
| 数据库设计 | [docs/database.md](docs/database.md) | ER 图、表结构、索引策略 |
| 安全设计 | [docs/security.md](docs/security.md) | 认证、授权、加密、审计 |
| 部署方案 | [docs/deployment.md](docs/deployment.md) | Docker、环境变量、初始化流程 |
| 测试策略 | [docs/testing.md](docs/testing.md) | 测试金字塔、工具、用例规划 |
| AI Agent | [docs/ai-agents.md](docs/ai-agents.md) | AI 能力设计、Prompt 策略 |
| 合规设计 | [docs/compliance.md](docs/compliance.md) | 保险合规规则、话术检查 |
| 信息架构 | [docs/information-architecture.md](docs/information-architecture.md) | 导航结构、页面层级 |
| 用户流程 | [docs/user-flows.md](docs/user-flows.md) | 核心操作流程设计 |
| 技术决策 | [docs/decisions.md](docs/decisions.md) | ADR 技术决策记录 |
| RAG 设计 | [docs/rag.md](docs/rag.md) | 检索增强生成技术方案 |
| 项目审计 | [docs/project-audit.md](docs/project-audit.md) | 项目整体审计 |

---

## 📄 License

本项目为华安保险内部项目，未经授权不得对外分发。
