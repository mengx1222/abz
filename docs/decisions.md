# 技术决策记录 — 安诊保 AI 副驾

> 版本：v1.0 ｜ 最后更新：2025-07-10 ｜ 负责人：技术团队
>
> 本文档记录安诊保 AI 副驾项目所有关键技术决策、选择理由及待确认项。
> 所有已确定决策均为最终决策，如需变更需经技术评审会议通过。

---

## 1. 决策概述

安诊保 AI 副驾是一个面向保险代理人（华安保险）的 AI 赋能平台，涵盖 AI 产品专家、客户 360 画像、AI 话术生成、AI 陪练等核心功能。技术决策需在以下维度之间取得平衡：

- **开发效率**：小团队（2-3 人）快速交付 MVP
- **可维护性**：代码结构清晰、技术栈主流、文档齐全
- **可扩展性**：AI Provider 可替换、功能模块可独立演进
- **企业适配**：满足华安 IT 部门的合规和安全要求
- **Demo 效果**：Demo 演示时系统完整、数据丰富、体验流畅

---

## 2. 已确定技术决策

### 2.1 决策总览

| # | 决策领域 | 候选方案 | 最终选择 | 选择理由 | 状态 |
|---|---------|---------|---------|---------|------|
| D-01 | 前端框架 | React / Vue / Svelte | React 18 + TypeScript 5 | 生态最成熟，shadcn/ui 原生支持，社区资源丰富 | ✅ 确定 |
| D-02 | 前端构建 | Vite / Webpack / Turbopack | Vite 6 | HMR 极快，配置简洁，TypeScript 原生支持 | ✅ 确定 |
| D-03 | CSS 方案 | Tailwind / CSS Modules / Styled Components | Tailwind CSS 4 + shadcn/ui | 企业级组件体系，高度可定制，开发效率高 | ✅ 确定 |
| D-04 | 后端框架 | FastAPI / Django / Flask | FastAPI | 原生 async，Pydantic 类型安全，自动 OpenAPI 文档 | ✅ 确定 |
| D-05 | ORM | SQLAlchemy / Prisma / Tortoise | SQLAlchemy 2.0 | Python 标准 ORM，成熟稳定，pgvector 支持好 | ✅ 确定 |
| D-06 | 数据库 | PostgreSQL / MySQL | PostgreSQL 16 + pgvector | 向量搜索原生支持，减少组件数，JSON 能力强 | ✅ 确定 |
| D-07 | 缓存 | Redis / Memcached | Redis 7 | 多功能（缓存/Session/Rate Limit/队列），性能优秀 | ✅ 确定 |
| D-08 | 向量搜索 | pgvector / Milvus / Weaviate | pgvector | 与 PostgreSQL 一体化，不额外部署组件，MVP 足够 | ✅ 确定 |
| D-09 | AI Gateway | 自建 / Dify / LangChain | 自建轻量 Gateway | 完全可控，不绑死第三方，Provider 可替换 | ✅ 确定 |
| D-10 | 状态管理 | Zustand / Redux / Jotai | Zustand | 轻量（~1KB），TypeScript 友好，API 简洁 | ✅ 确定 |
| D-11 | 服务端状态 | React Query / SWR | TanStack React Query | 缓存 + 重新验证 + 乐观更新能力强 | ✅ 确定 |
| D-12 | RAG 方案 | 自建 / LlamaIndex / LangChain | 自建 Pipeline | 完全可控，与 AI Gateway 统一架构 | ✅ 确定 |
| D-13 | 数据库迁移 | Alembic / Flyway | Alembic | SQLAlchemy 原生迁移工具 | ✅ 确定 |
| D-14 | 部署方案 | Docker Compose | Docker Compose | MVP 阶段简单可靠，一条命令启动 | ✅ 确定 |
| D-15 | 文档解析 | PyPDF2 / pdfplumber / unstructured | pdfplumber + python-docx + python-pptx | 各格式专用库，解析精度高 | ✅ 确定 |
| D-16 | 前端路由 | React Router v6 | React Router v7 | React 生态标准路由方案 | ✅ 确定 |

### 2.2 决策详情

#### D-01：前端框架 — React 18 + TypeScript 5

**候选方案**：
- **React 18**：生态最大，社区资源最多，shadcn/ui 原生支持
- **Vue 3**：上手快，但企业级组件库（如 shadcn）支持不如 React
- **Svelte**：性能好但生态小，企业级组件支持不足

**选择理由**：
1. shadcn/ui 是目前最优秀的 React 企业级组件库，不引入运行时依赖
2. TypeScript 5 提供了完整的类型系统，与后端 Pydantic 模型可做到类型对齐
3. 团队对 React 生态最熟悉
4. 招聘市场 React 人才最多，便于后续团队扩展

**风险**：React 的 bundle 体积相对较大，但 Vite 的 tree-shaking 和 code-splitting 可有效缓解。

---

#### D-02：前端构建工具 — Vite 6

**候选方案**：
- **Vite 6**：基于 ESM 的极速构建，HMR < 50ms
- **Webpack 5**：功能强大但配置复杂
- **Turbopack**：Next.js 专属，不适合独立 Vite 项目

**选择理由**：
1. HMR 速度极快，开发体验显著优于 Webpack
2. 零配置支持 TypeScript、JSX、CSS Modules
3. 配置简洁，`vite.config.ts` 通常不超过 50 行
4. 插件生态成熟，兼容 Rollup 插件

---

#### D-03：CSS 方案 — Tailwind CSS 4 + shadcn/ui

**候选方案**：
- **Tailwind CSS 4 + shadcn/ui**：原子化 CSS + 预制组件
- **CSS Modules**：样式隔离好但开发效率低
- **Styled Components**：运行时 CSS-in-JS，性能有损耗

**选择理由**：
1. shadcn/ui 提供了完整的企业级组件（Table、Form、Dialog、Toast 等），直接复制到项目中，完全可控
2. Tailwind CSS 4 原子化 CSS 高效且一致性强
3. 不引入运行时 CSS-in-JS 开销
4. 设计系统可通过 `tailwind.config` 统一管理

---

#### D-04：后端框架 — FastAPI

**候选方案**：
- **FastAPI**：异步原生，自动 OpenAPI 文档
- **Django**：全栈框架，但对于纯 API 项目偏重
- **Flask**：轻量但异步支持需额外配置

**选择理由**：
1. 原生 async/await 支持，对 SSE 流式响应友好
2. Pydantic 提供强类型校验和 JSON Schema 生成
3. 自动生成 OpenAPI/Swagger 文档，前端可自动生成 API 类型
4. 依赖注入系统优雅，权限中间件集成简洁
5. 性能优秀（基于 Starlette + Uvicorn）

---

#### D-05：ORM — SQLAlchemy 2.0

**候选方案**：
- **SQLAlchemy 2.0**：Python 事实标准 ORM
- **Prisma**：TypeScript 生态为主，Python 支持不成熟
- **Tortoise ORM**：异步 ORM 但生态较小

**选择理由**：
1. SQLAlchemy 2.0 引入了现代声明式 API（`Mapped[]` 类型注解），与 Pydantic 模型对齐
2. pgvector 的 Python SDK（`pgvector` 库）原生支持 SQLAlchemy
3. Alembic 数据库迁移工具与 SQLAlchemy 无缝集成
4. 社区最大，问题排查资源丰富

---

#### D-06：数据库 — PostgreSQL 16 + pgvector

**候选方案**：
- **PostgreSQL 16 + pgvector**：关系型 + 向量一体化
- **MySQL 8**：关系型数据库，但向量搜索需额外组件

**选择理由**：
1. pgvector 扩展原生支持 HNSW 和 IVFFlat 索引，RAG 检索性能优秀
2. 不需要额外部署 Milvus/Weaviate 等独立向量数据库，减少运维复杂度
3. PostgreSQL 的 JSONB 类型适合存储结构化/半结构化 AI 输出
4. 行级安全策略（RLS）可用于数据权限控制
5. MVP 阶段数据量（< 100 万向量）pgvector 完全足够

---

#### D-07：缓存 — Redis 7

**候选方案**：
- **Redis 7**：多功能内存数据库
- **Memcached**：纯缓存，功能单一

**选择理由**：
1. 除缓存外还支持：Session 存储、Rate Limiting、消息队列、Pub/Sub
2. 数据结构丰富（String/Hash/List/Set/Sorted Set）
3. 持久化（RDB/AOF）防止数据丢失
4. 性能优秀，单机 10 万+ QPS

---

#### D-08：向量搜索 — pgvector

**候选方案**：
- **pgvector**：PostgreSQL 扩展
- **Milvus**：独立向量数据库
- **Weaviate**：独立向量数据库

**选择理由**：
1. 与 PostgreSQL 一体化，不增加运维组件数量
2. MVP 阶段数据量（知识文档 Chunk < 10 万）pgvector 性能足够
3. 查询可与关系数据 JOIN，实现权限过滤更自然
4. 部署简单，Docker 一键启动

**后果**：如果未来数据量超过千万级别（如扩展到全公司产品线），需要评估迁移到 Milvus 等专用向量库。

---

#### D-09：AI Gateway — 自建轻量 Gateway

**候选方案**：
- **自建轻量 Gateway**：统一接口 + Provider 适配器模式
- **Dify**：开源 AI 编排平台
- **LangChain**：AI 应用开发框架

**选择理由**：
1. 不绑死任何第三方平台，Provider 可随时替换（DeepSeek ↔ Qwen ↔ GPT-4o）
2. Mock 模式更灵活，Demo 演示不依赖任何外部 AI 服务
3. 完全可控，可针对保险场景定制（合规审查、引用注入等）
4. 代码量少（< 500 行），维护成本低
5. 预留 Dify 接口，未来可无缝切换

**后果**：需要自行维护 Prompt 管理和模型调用逻辑，无法直接使用 Dify 的可视化编排能力。

---

#### D-10：状态管理 — Zustand

**候选方案**：
- **Zustand**：极简状态管理（~1KB）
- **Redux Toolkit**：功能强大但样板代码多
- **Jotai**：原子化状态管理

**选择理由**：
1. API 极简：`create()` 创建 store，`useStore()` 使用
2. TypeScript 原生支持，类型推导完整
3. 无 Provider 包裹，不增加组件层级
4. 中间件支持（persist、devtools、immer）
5. 包体积 ~1KB，对性能无影响

---

#### D-11：服务端状态管理 — TanStack React Query

**候选方案**：
- **TanStack React Query（React Query v5）**：服务端状态缓存+同步
- **SWR**：Vercel 出品，功能类似但略简单

**选择理由**：
1. 缓存 + 自动重新验证 + 乐观更新 + 分页支持一应俱全
2. 与 SSE 流式数据可良好配合
3. DevTools 调试工具强大
4. 社区活跃，文档完善

---

#### D-12：RAG 方案 — 自建 Pipeline

**候选方案**：
- **自建 Pipeline**：文档解析 → Chunk 切分 → Embedding → 向量存储 → 检索
- **LlamaIndex**：RAG 框架
- **LangChain**：通用 AI 框架

**选择理由**：
1. RAG 流程明确且不复杂（文档量有限），自建可控性更高
2. 与自建 AI Gateway 统一架构，Embedding 调用复用
3. 权限过滤可在 SQL 层面实现（pgvector + WHERE 条件）
4. 避免引入重型框架的隐式依赖

---

#### D-14：部署方案 — Docker Compose

**选择理由**：
1. MVP 阶段 4 个服务（前端/后端/数据库/缓存），Compose 完全足够
2. 一条命令启动，Demo 演示极其方便
3. 配置文件即基础设施即代码
4. 未来可平滑迁移到 Kubernetes

---

#### D-15：文档解析 — pdfplumber + python-docx + python-pptx

**选择理由**：
1. 各格式使用专用库，解析精度高于通用方案
2. pdfplumber 对表格提取支持优秀（保险产品条款含大量表格）
3. python-docx / python-pptx 是各格式的标准解析库
4. 轻量级，无外部服务依赖

---

## 3. 待确认技术决策

### 3.1 决策总览

| # | 决策领域 | 候选方案 | 当前占位方案 | 阻塞程度 | 确认方 | 备注 |
|---|---------|---------|------------|---------|-------|------|
| D-17 | 大模型供应商 | DeepSeek / Qwen / GPT-4o / GLM | MockProvider | 🔴 高 | 华安 IT 部门 | 影响所有 AI 功能 |
| D-18 | Embedding 模型 | text-embedding-3-small / bge-large-zh | MockProvider | 🔴 高 | 华安 IT 部门 | 影响 RAG 检索质量 |
| D-19 | Rerank 模型 | Cohere / bge-reranker / 自研 | 基于 BM25 排序 | 🟡 中 | 技术团队 | 影响 RAG 检索排序 |
| D-20 | 企业 SSO | 企业微信 / 钉钉 / 自建 | Demo 手机号登录 | 🟡 中 | 华安 IT 部门 | 影响登录体验 |
| D-21 | CRM 对接 | 华安 CRM API / 手动导入 | Demo 客户数据 | 🟡 中 | 华安业务部门 | 影响客户数据来源 |
| D-22 | Dify 集成 | Dify Workflow / 自建编排 | 自建 Gateway（预留接口） | 🟢 低 | 技术团队 | 影响 AI 编排复杂度 |
| D-23 | OCR 能力 | Tesseract / PaddleOCR / 云服务 | Mock（表格/图片暂不解析） | 🟢 低 | 技术团队 | 影响文档解析完整性 |
| D-24 | 消息推送 | 企业微信 / 钉钉 / 站内信 | 站内信 | 🟢 低 | 华安 IT 部门 | 影响通知触达 |
| D-25 | 监控方案 | Prometheus+Grafana / 自建 | 结构化日志 | 🟢 低 | 运维团队 | 影响运维能力 |

### 3.2 高优先级待确认项

#### D-17：大模型供应商

**阻塞原因**：所有 AI 功能（产品专家、客户分析、话术生成、陪练评分）均依赖大模型。MockProvider 仅用于开发测试，无法在 Demo 演示中展示真实 AI 效果。

**评估维度**：
- 中文理解能力（保险术语准确度）
- 结构化输出能力（JSON 格式稳定性）
- 流式响应支持（SSE 体验）
- 价格和 Token 限制
- 数据安全（是否支持私有部署）
- 响应延迟

**当前占位**：MockProvider 返回预设的固定响应，支持 `thinking`、`content`、`reference`、`done`、`error` 事件类型。

#### D-18：Embedding 模型

**阻塞原因**：RAG 检索质量直接取决于 Embedding 模型对中文保险领域文本的向量化质量。

**评估维度**：
- 中文语义理解能力
- 向量维度和检索精度
- 批量处理性能
- 部署方式（API / 私有化）

---

## 4. 架构决策记录（ADR）

### ADR-001：为什么选择 pgvector 而非独立向量数据库

- **状态**：已接受
- **日期**：2025-07-10
- **决策者**：技术团队

**背景**：
安诊保 AI 副驾需要向量检索能力以支持 RAG（检索增强生成）功能。知识库文档需要被切分为 Chunk 并向量化存储，用户查询时通过向量相似度检索相关知识。

**候选方案**：
1. **pgvector**（PostgreSQL 扩展）
2. **Milvus**（独立向量数据库）
3. **Weaviate**（独立向量数据库）

**决策**：使用 PostgreSQL 的 pgvector 扩展。

**理由**：
1. **减少运维组件**：MVP 阶段只需 4 个 Docker 容器，如果引入 Milvus 需要额外容器和运维成本
2. **统一数据管理**：向量数据与业务数据在同一数据库中，JOIN 查询和权限过滤更自然
3. **性能足够**：预估知识库 Chunk 数量在 5-10 万级别，pgvector + HNSW 索引检索延迟 < 200ms，完全满足需求
4. **部署简单**：pgvector 作为 PostgreSQL 扩展，无需额外安装和配置
5. **事务一致性**：向量数据与业务数据在同一事务中更新，保证一致性

**后果**：
- ✅ 正面：部署简单、运维成本低、数据一致性好
- ⚠️ 注意：如果数据量增长到千万级别，需要评估迁移到 Milvus 等专用向量库
- ⚠️ 注意：pgvector 不支持分布式部署，水平扩展受限

---

### ADR-002：为什么自建 AI Gateway 而非使用 Dify

- **状态**：已接受
- **日期**：2025-07-10
- **决策者**：技术团队

**背景**：
项目 PPT 提到 Dify 作为 AI 编排的候选方案。需要决定是使用 Dify 的可视化编排能力，还是自建轻量 AI Gateway。

**候选方案**：
1. **自建轻量 AI Gateway**：抽象 Provider 接口 + 各厂商适配器
2. **Dify**：开源 AI 编排平台，提供可视化 Workflow 编排

**决策**：自建轻量 AI Gateway，同时预留 Dify 集成接口。

**理由**：
1. **不绑死第三方**：Dify 是独立平台，引入后替换成本高。自建 Gateway 只需实现 `AIProviderBase` 接口
2. **完全可控**：保险场景需要特殊的合规审查（输出前检查）、引用注入（强制引用知识库来源）、结构化输出校验等，自建更灵活
3. **Mock 模式灵活**：Demo 演示时需要不依赖外部 AI 服务的 Mock 模式，自建 Gateway 可以完美支持
4. **代码量小**：AI Gateway 核心代码 < 500 行，维护成本低
5. **预留扩展**：Gateway 架构设计时预留了 `DifyProvider` 接口，未来如需使用 Dify 可无缝接入

**后果**：
- ✅ 正面：完全可控、Mock 灵活、Provider 可替换、代码量小
- ⚠️ 注意：需要自行维护 Prompt 管理和模型调用逻辑
- ⚠️ 注意：无法使用 Dify 的可视化 Workflow 编排和日志追踪能力
- ⚠️ 注意：如需复杂的 AI 编排（多步骤 Chain、Agent 自动决策），自建成本会显著增加

---

### ADR-003：为什么选择自建 RAG Pipeline 而非 LlamaIndex/LangChain

- **状态**：已接受
- **日期**：2025-07-10
- **决策者**：技术团队

**背景**：
RAG（检索增强生成）是系统核心能力，需要处理保险产品文档的解析、切分、向量化、存储和检索。

**候选方案**：
1. **自建 Pipeline**：文档解析 → Chunk 切分 → Embedding → pgvector 存储 → 检索
2. **LlamaIndex**：专注 RAG 的框架
3. **LangChain**：通用 AI 应用框架

**决策**：自建 RAG Pipeline。

**理由**：
1. **流程明确**：RAG 流程（解析 → 切分 → Embedding → 检索 → 融合）非常标准化，不需要框架的抽象
2. **权限过滤**：保险知识库有严格的权限控制（按角色/产品/机构），自建可在 SQL 层面自然实现
3. **与 AI Gateway 统一**：Embedding 调用通过 AI Gateway 统一管理，复用 Provider 适配器
4. **避免隐式依赖**：LlamaIndex/LangChain 引入大量传递依赖，可能与其他库冲突
5. **调试透明**：自建 Pipeline 每个环节都可独立测试和调试

---

## 5. 决策变更记录

> 初始版本 v1.0，暂无决策变更。
>
> 如需变更已确定的技术决策，需提交技术评审：
> 1. 提出变更申请（包含变更原因、影响范围、替代方案）
> 2. 技术团队评审讨论
> 3. 评审通过后更新本文档，记录变更原因

| 日期 | 决策编号 | 变更内容 | 变更原因 | 评审人 |
|------|---------|---------|---------|--------|
| — | — | — | — | — |

---

## 6. 数据枚举值权威定义

以下枚举值为本项目的权威定义，所有文档和代码必须保持一致。

### 6.1 客户阶段（Customer Stage）

| 枚举值 | 中文名称 | 说明 |
|--------|---------|------|
| `new_lead` | 新线索 | 初始获取的潜在客户 |
| `initial_contact` | 初次接触 | 首次联系，了解基本信息 |
| `needs_discovery` | 需求了解 | 深入了解客户需求和痛点 |
| `proposal` | 方案报价 | 提供保险方案和报价 |
| `objection_handling` | 异议处理 | 处理客户价格/产品等异议 |
| `closing` | 促成阶段 | 推动成交决策 |
| `closed_won` | 成交 | 成功签单 |
| `closed_lost` | 流失 | 客户明确拒绝或失联 |
| `follow_up` | 跟进中 | 需要后续持续跟进 |

### 6.2 违规类型（Compliance Violation Types）

| 枚举值 | 中文名称 | 风险等级 | 检查方式 |
|--------|---------|---------|---------|
| `return_promise` | 收益承诺 | RED | 关键词 |
| `absolute_expression` | 绝对化表达 | RED | 关键词（肯定/一定/绝对/保证） |
| `false_comparison` | 虚假比较 | RED | 关键词+AI判断 |
| `exaggerated_coverage` | 夸大保障 | YELLOW | 关键词 |
| `improper_underwriting` | 不当核保结论 | RED | 规则匹配 |
| `improper_claim` | 不当理赔承诺 | RED | 关键词 |
| `misleading_sales` | 诱导销售 | RED/YELLOW | 关键词+AI判断 |
| `sensitive_medical` | 敏感医疗结论 | RED | 规则匹配 |

### 6.3 Demo 验证码

Demo 模式下的统一验证码为 `888888`（对应手机号 `13800138000`）。
