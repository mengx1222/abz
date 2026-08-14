# 项目审计报告 — 安诊保 AI 副驾

> ⚠️ **本文档已过时** — 这是项目初始状态（Phase 0）的基线审计。
> 
> **最新审计报告请查看**: [`current-state-audit.md`](./current-state-audit.md)（2026-08-14）

> **审计日期**：2025年7月（过时）  
> **项目阶段**：0→1 绿地新建（Greenfield）→ 已完成MVP全部功能开发  
> **所属企业**：华安保险（Sinosafe Insurance）

---

## 1. 审计概述

### 1.1 审计目的

对「安诊保 AI 副驾」项目仓库进行启动前基线审计，明确当前项目状态与目标产品之间的差距，为后续 10 个 Phase 的分批实施提供客观依据和风险提示。

### 1.2 审计范围

- 仓库文件结构与已有代码
- 运行环境与工具链
- 技术栈就绪情况
- 与产品总控文档中 62 条要求的逐项比对

### 1.3 审计时间

2025年7月 — 项目正式启动前（Phase 0）。

---

## 2. 仓库现状

### 2.1 当前文件结构

```
/home/z/my-project/
├── upload/
│   └── 安诊保 AI 副驾｜Codex 0→1 产品研发总控 Prompt.md   ← 唯一实质文件
├── download/
│   └── README.md                                                ← 空占位文件
└── docs/
    └── project-audit.md                                        ← 本文档
```

### 2.2 现状结论

| 检查项 | 状态 |
|--------|------|
| 业务代码（前端/后端） | ❌ 不存在 |
| 配置文件（.env / tsconfig / pyproject 等） | ❌ 不存在 |
| 依赖管理（package.json / requirements.txt） | ❌ 不存在 |
| 数据库 Schema / Migration | ❌ 不存在 |
| Docker 配置 | ❌ 不存在 |
| 测试文件 | ❌ 不存在 |
| CI/CD 配置 | ❌ 不存在 |
| .gitignore | ❌ 不存在 |
| README.md | ❌ 不存在（根目录） |
| 产品文档（docs/） | ❌ 仅本审计文档 |

**仓库当前为完全空白状态，仅包含一份产品总控规格说明。**

---

## 3. 技术栈现状

### 3.1 当前状态：无任何技术栈

仓库中不存在任何框架、库或工具链的配置与代码。项目处于纯规划阶段。

### 3.2 规划技术栈

| 层级 | 规划技术选型 | 当前就绪 | 备注 |
|------|------------|----------|------|
| **前端框架** | React + TypeScript | ⚠️ 环境有 Node.js，但未初始化项目 | 需 `npm create vite@latest` |
| **前端构建** | Vite | ⚠️ 同上 | 随 Vite 项目初始化 |
| **前端样式** | Tailwind CSS | ❌ 未安装 | 需配置 PostCSS 插件 |
| **前端组件库** | shadcn/ui | ❌ 未安装 | 基于 Radix UI + Tailwind |
| **前端数据请求** | React Query (TanStack Query) | ❌ 未安装 | — |
| **前端路由** | React Router | ❌ 未安装 | — |
| **前端状态管理** | Zustand | ❌ 未安装 | — |
| **后端语言** | Python | ✅ Python 3.12.13 已安装 | — |
| **后端框架** | FastAPI | ❌ 未安装 | 需 `pip install fastapi uvicorn` |
| **后端 ORM** | SQLAlchemy (async) | ❌ 未安装 | — |
| **后端校验** | Pydantic v2 | ❌ 未安装 | FastAPI 依赖项 |
| **关系数据库** | PostgreSQL | ❌ 未安装 | 当前机器无 psql，无 Docker |
| **缓存** | Redis | ❌ 未安装 | 当前机器无 redis-cli，无 Docker |
| **向量数据库** | pgvector (PostgreSQL 扩展) | ❌ 未安装 | 依赖 PostgreSQL |
| **对象存储** | 本地 / S3-compatible | ❌ 未配置 | — |
| **AI 模型** | DeepSeek / Qwen / OpenAI-compatible | ❌ 无配置、无 Gateway | 需构建 AI Gateway 抽象层 |
| **任务队列** | Celery / FastAPI BackgroundTasks | ❌ 未安装 | — |
| **容器化** | Docker + Docker Compose | ❌ Docker 未安装 | 当前环境不支持 |
| **包管理器** | pnpm（前端推荐） | ❌ 未安装 | 可回退使用 npm |

---

## 4. 环境现状

### 4.1 已就绪

| 工具 | 版本 | 状态 |
|------|------|------|
| Node.js | v24.18.0 | ✅ 可用 |
| Python | 3.12.13 | ✅ 可用 |
| npm | 11.16.0 | ✅ 可用 |

### 4.2 缺失

| 工具 | 用途 | 状态 | 影响 |
|------|------|------|------|
| Docker + Docker Compose | 容器化部署、PostgreSQL/Redis 本地运行 | ❌ 未安装 | **高影响** — 数据库、Redis、向量库均无法本地启动 |
| pnpm | 前端包管理（推荐） | ❌ 未安装 | 低影响 — 可使用 npm 替代 |
| PostgreSQL + psql | 主数据库 | ❌ 未安装 | **高影响** — 无法存储业务数据 |
| Redis + redis-cli | 缓存 / Session / 队列 | ❌ 未安装 | **中影响** — 影响性能与实时功能 |
| pgvector | 向量检索（RAG 核心） | ❌ 未安装 | **高影响** — RAG 系统依赖 |
| Embedding 模型服务 | 文本向量化 | ❌ 无 | **高影响** — RAG 管道必需 |
| LLM API 访问 | DeepSeek / Qwen 等 | ❌ 无配置 | 可用 MockProvider 临时替代 |

### 4.3 环境建议

1. **优先安装 Docker + Docker Compose**，解决 PostgreSQL、Redis、pgvector 一站式部署问题
2. 在 Docker 就绪前，可先用 SQLite + 内存存储进行本地开发调试
3. 前端直接使用 npm（v11.16.0），暂不强制要求 pnpm

---

## 5. 与目标产品的差距分析

> 基于《安诊保 AI 副驾｜Codex 0→1 产品研发总控 Prompt.md》62 条要求逐项比对。

| # | 模块 | 目标要求 | 当前状态 | 差距 | Phase |
|---|------|---------|---------|------|-------|
| 1 | **前端应用** | React + TS + Vite + Tailwind + shadcn/ui + React Query + Router + Zustand，完整工作台 UI、8个一级导航、管理后台、响应式、深色模式预留 | ❌ 无任何前端代码 | 100% | 1–2 |
| 2 | **后端服务** | Python + FastAPI + SQLAlchemy + Pydantic，分层架构（routers/services/repositories/models/schemas），REST API | ❌ 无任何后端代码 | 100% | 1 |
| 3 | **数据库** | PostgreSQL + Redis + pgvector，30+ 张核心表，规范化设计，Alembic 迁移 | ❌ 无数据库、无 Schema、无迁移 | 100% | 1 |
| 4 | **认证与权限** | 手机号登录 Demo、RBAC（7种角色）、服务端鉴权、JWT/Session、组织架构 | ❌ 无认证系统 | 100% | 1 |
| 5 | **AI Gateway** | 统一 AIProvider 抽象层，支持 DeepSeek/Qwen/OpenAI-compatible/Mock，环境变量配置 | ❌ 无 AI 调用层 | 100% | 1 + 4 |
| 6 | **RAG 系统** | 文档上传→解析→Chunk→Embedding→向量存储→BM25→Hybrid Search→Rerank→权限过滤→引用 | ❌ 无 RAG 管道 | 100% | 3 |
| 7 | **知识库管理** | 文档版本管理、生命周期（上传→解析→审核→发布→失效）、Chunk 管理、Metadata、召回统计 | ❌ 无知识库 | 100% | 3 + 9 |
| 8 | **AI 产品专家** | RAG 强制问答、带出处引用、结构化输出（结论/依据/条款/页码/风险提示）、反馈闭环 | ❌ 无 AI 问答功能 | 100% | 4 |
| 9 | **客户 360** | 客户列表/详情/标签/画像/沟通记录/购买记录/AI 分析/AI 建议，数据权限隔离 | ❌ 无客户管理 | 100% | 5 |
| 10 | **AI 话术助手** | 基于客户上下文生成多风格话术（亲和/专业/数据/简洁）、合规检查、可编辑/复制 | ❌ 无话术功能 | 100% | 6 |
| 11 | **AI 陪练** | 互动式角色扮演训练，20+ 场景，AI 扮演客户追问，三维评分（准确性/共情/促单），成长记录 | ❌ 无陪练功能 | 100% | 7 |
| 12 | **AI 社区** | 企业知识中枢，问答/案例/话术/培训，AI 自动提炼，审核流程，经验沉淀闭环 | ❌ 无社区功能 | 100% | 8 |
| 13 | **管理后台** | 用户管理、客户管理、知识库、陪练场景、话术库、社区管理、系统设置 | ❌ 无后台管理 | 100% | 9 |
| 14 | **合规中心** | 合规规则引擎（GREEN/YELLOW/RED）、"对客先审后发"、风险拦截、审计日志 | ❌ 无合规系统 | 100% | 6 + 9 |
| 15 | **数据看板** | DAU/WAU、AI 问答量、采纳率、陪练次数、合规拦截率等，Mock 数据明确标注 | ❌ 无数据看板 | 100% | 9 |
| 16 | **消息中心** | 多类型通知（客户/AI/系统/审核/社区），未读/已读/跳转 | ❌ 无消息系统 | 100% | 2 |
| 17 | **Mock/Demo 模式** | `DEMO_MODE=true` 一键切换，MockProvider，Seed 数据，完整业务流程可演示 | ❌ 无 Mock 层 | 100% | 1 + 10 |
| 18 | **Docker 部署** | docker-compose.yml（frontend/backend/postgres/redis/vector-db）、.env.example、`make init` | ❌ Docker 未安装，无配置 | 100% | 10 |
| 19 | **测试** | 单元测试（auth/RBAC/RAG/compliance）、API 测试、前端测试、E2E 测试 | ❌ 无任何测试 | 100% | 10 |
| 20 | **文档** | 13 份 docs/ 文档（产品/架构/信息架构/流程/数据库/API/RAG/Agent/合规/安全/测试/部署/决策） | ⚠️ 仅本审计文档 1 份 | ~92% | 持续 |

**综合差距：100%**（项目为从零开始的绿地新建）

---

## 6. 风险评估

### 6.1 技术风险

| 风险项 | 等级 | 描述 | 缓解措施 |
|--------|------|------|----------|
| **从零构建** | 🔴 高 | 仓库完全空白，需搭建全部基础设施（前端/后端/DB/AI），工程量大 | 严格按 Phase 1–10 分批交付，每 Phase 产出可运行产物 |
| **Docker 缺失** | 🔴 高 | 当前环境无 Docker，PostgreSQL/Redis/pgvector 无法本地运行 | 优先安装 Docker；Docker 就绪前用 SQLite + 内存模式开发 |
| **RAG 复杂度** | 🟡 中 | 完整 RAG 管道（解析→Chunk→Embedding→Hybrid Search→Rerank→权限）技术复杂度高 | Phase 3 专注 RAG，先用简单 Chunk + Cosine Similarity 验证，再逐步增强 |
| **AI 模型依赖** | 🟡 中 | 真实 LLM/Embedding API 暂不可用，需要 MockProvider 完整模拟 | MockProvider 接口与真实 Provider 完全一致，确保零成本切换 |
| **前后端联调** | 🟡 中 | 前端 React + 后端 FastAPI 异构技术栈，SSE 流式输出需特别注意 | 统一 API Contract 文档，早期定义 OpenAPI Spec |

### 6.2 业务风险

| 风险项 | 等级 | 描述 | 缓解措施 |
|--------|------|------|----------|
| **保险业务规则未确认** | 🔴 高 | 真实产品条款、健康告知规则、核保逻辑、合规红线均未提供 | **所有真实保险业务规则使用 Demo/Mock 数据**，标注为占位，待业务方确认后替换 |
| **合规要求不明确** | 🟡 中 | "对客先审后发"、合规规则（收益承诺/绝对化表达等）需法务确认 | 先建合规引擎框架，规则以可配置方式实现，具体规则后续填充 |
| **数据安全合规** | 🟡 中 | 客户健康信息、隐私数据的脱敏/权限/审计要求 | 架构层面预留字段级权限和审计日志，Demo 模式使用虚构数据 |

### 6.3 时间风险

| 风险项 | 等级 | 描述 | 缓解措施 |
|--------|------|------|----------|
| **3 个月 MVP 目标紧张** | 🔴 高 | 10 个 Phase、20+ 模块、30+ 数据库表、完整 RAG + AI + 合规 + 权限体系 | ①严格 Phase 分批，每 Phase 2–4 天 ②AI 能力优先 Mock ③MVP 聚焦：工作台 + AI 产品专家 + 客户 360 + AI 话术 + AI 陪练 + AI 社区（总控文档明确的第一阶段优先） |
| **需求范围庞大** | 🟡 中 | 总控文档 62 条要求覆盖面极广 | 区分 MVP 必须 vs 后续迭代，Demo 模式兜底 |

---

## 7. 审计结论

### 7.1 总体判定

**「安诊保 AI 副驾」项目当前为 0→1 绿地新建状态，与目标产品的综合差距为 100%。**

仓库中除一份产品总控规格文档外，不存在任何可运行的代码、配置或基础设施。这是一个从第一行代码开始构建的全新企业级项目。

### 7.2 核心结论

1. **差距 100%**：前端、后端、数据库、AI、RAG、合规、测试、部署 — 所有模块均需从零构建
2. **环境瓶颈**：Docker 未安装是当前最大环境阻塞项，直接影响数据库和中间件的本地部署
3. **业务空白**：真实保险产品条款、合规规则、客户数据均未就绪，全部需要 Mock

### 7.3 实施建议

1. **严格按 Phase 分批实施**，每 Phase 交付可验证的运行产物，不要试图一次性生成全部代码
2. **所有真实保险业务规则标记为 Demo/Mock**：产品条款、健康告知、核保逻辑、合规红线均使用占位数据，架构层面通过 Service/Repository/Adapter 隔离，确保未来可无痛切换到真实数据
3. **优先安装 Docker**，解决 PostgreSQL + Redis + pgvector 一站式部署
4. **AI 能力 Mock 优先**：MockProvider 接口与真实 Provider 完全一致，确保模型接入时零改动业务层
5. **MVP 聚焦第一阶段优先**：代理人 AI 副驾 + AI 社区（总控文档明确），其余功能按 Phase 逐步补充

### 7.4 下一步行动

| 优先级 | 行动项 | 对应 Phase |
|--------|--------|-----------|
| P0 | 安装 Docker + Docker Compose | Phase 1 前置 |
| P0 | 初始化前端项目（Vite + React + TypeScript） | Phase 1 |
| P0 | 初始化后端项目（FastAPI + SQLAlchemy） | Phase 1 |
| P0 | 搭建数据库 Schema + Alembic 迁移 | Phase 1 |
| P0 | 实现认证 + RBAC | Phase 1 |
| P1 | 构建 AI Gateway + MockProvider | Phase 1 + 4 |
| P1 | 生成项目文档体系（13 份 docs/） | 持续 |
| P2 | 实现 RAG 管道 | Phase 3 |
| P2 | 实现 AI 产品专家（第一优先功能） | Phase 4 |

---

> **审计人**：项目审计工具  
> **文档版本**：v1.0  
> **下次审计建议**：Phase 1 完成后