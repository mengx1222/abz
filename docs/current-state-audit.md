# 当前状态审计报告 — 安诊保 AI 副驾

> 审计时间：2026-08-17
> Git HEAD：`575f8f2`（main）
> 项目版本：`0.1.0`（`backend/pyproject.toml`）
> 发布就绪状态：**Internal Pilot Candidate**（见 [docs/release-readiness.md](release-readiness.md)）
> 审计方式：代码实际读取 + 最新 CI 结果（非文档推断）

---

## 1. 项目概览

| 维度 | 实际状态 |
|------|---------|
| 技术栈 | React 19 + TypeScript ~6.0 + Vite 8 + Tailwind 4 + React Router 7 ‖ Python 3.12 + FastAPI + SQLAlchemy 2.0 async + Pydantic v2 + Alembic（hatchling） |
| 数据库 | PostgreSQL 16 + pgvector（1536 维）— 7 个 Alembic 迁移，30 张表 |
| 缓存 | Redis 7（生产代码就绪；Demo 模式不依赖） |
| AI | 自建 AI Gateway（mock / openai / deepseek / qwen）+ 真实阿里云百炼 DashScope（qwen-plus / text-embedding-v3） |
| RAG | pgvector 向量 + BM25 + RRF 融合 + Confidence Gate（ALLOW/REVIEW/REFUSE）+ Citation + 产品边界（Task 13） |
| 部署 | Docker Compose（开发/生产两套），4 容器（postgres/redis/backend/frontend） |
| 前端 | 21 条路由，SSE 流式（Product QA / Script / AI 摘要 / 陪练） |

## 2. 验证状态（Verified Facts）

| 项 | 状态 |
|----|------|
| 真实 PostgreSQL 16 + pgvector | ✅ Production Validation + PG 集成测试 |
| 真实 Redis | ✅ Production Validation |
| 真实 DashScope / Qwen | ✅ Real AI Smoke **8/8 PASS**（run 31866434810，commit 94ce52f） |
| Backend 测试 | ✅ CI 全绿（约 229 个测试函数：单元 + API 集成 + PG 集成） |
| Frontend 测试 / 构建 | ✅ Vitest + Vite build 通过 |
| Playwright E2E | ✅ 11/11 PASS（阶段一 4 + 阶段二 7，含 Product QA / Script / Citation UI / 产品边界） |
| Docker Production Validation | ✅ 全绿 |

## 3. 后端 API 端点（89 个，与 `backend/app/api/v1/` 实际代码一致）

| 模块 | 端点数 | 前缀 |
|------|--------|------|
| 健康检查 | 3 | `/api/v1/health`, `/ready`, `/health/detail` |
| 认证 | 4 | `/api/v1/auth`（login/refresh/logout/me） |
| AI 助手 | 3 | `/api/v1/ai`（product-qa/chat SSE + conversations） |
| 知识库管理 | 9 | `/api/v1/admin/knowledge-bases` |
| 客户 360 | 8 | `/api/v1/customers`（CRUD + interactions + followups + ai-analysis） |
| AI 陪练 | 8 | `/api/v1/training`（scenarios/sessions/SSE messages/complete/stats） |
| AI 话术 | 6 | `/api/v1/scripts`（CRUD + generate SSE + check-compliance + favorite） |
| AI 社区 | 11 | `/api/v1/community`（posts/comments/like/favorite/ai-summary SSE） |
| 管理后台 | 28 | `/api/v1/admin`（users/audit/analytics/compliance/community/scripts/training/settings） |
| 成长体系 | 4 | `/api/v1/growth`（overview/courses/leaderboard/achievements） |
| 通知中心 | 4 | `/api/v1/notifications` |
| Dashboard | 1 | `/api/v1/dashboard` |
| **合计** | **89** | |

## 4. 前端路由（21 条，与 `frontend/src/app/routes.tsx` 一致）

`/login`、`/dashboard`、`/customers`、`/customers/:id`、`/product-qa`、`/scripts`、`/training`、`/training/chat/:scenarioId`、`/community`、`/growth`、`/notifications`、`/knowledge`、`/admin/users`、`/admin/analytics`、`/admin/audit`、`/admin/community`、`/admin/compliance`、`/admin/scripts`、`/admin/training`、`/admin/settings`、`/`（重定向）

## 5. 数据库（30 张表，7 个迁移）

| 迁移 | 内容 |
|------|------|
| 0001_initial | 基础（用户/角色/组织/权限/客户/会话） |
| 0002_knowledge_ai | 知识库/文档/分块（pgvector）+ AI 日志 |
| 0003_scripts | 话术 + 收藏 |
| 0004_community | 社区（帖子/评论/点赞） |
| 0005_remaining | 培训/成长/通知 |
| 0006_notification_growth_audit | 通知偏好/成长/审计日志 |
| 0007_kb_versioning_audit_enhance | 知识库版本化 + 审计增强 |

核心表：`users` / `roles` / `organizations` / `customers` / `documents` / `document_chunks`（embedding 1536 维）/ `knowledge_bases` / `scripts` / `training_*` / `community_*` / `growth_*` / `notifications` / `audit_logs` / `ai_logs`

## 6. RAG（生产链路已真实验证）

- 检索：pgvector 向量 + PostgreSQL BM25 + RRF 融合（K=60，分数 ×100 对齐阈值）
- Confidence Gate：HIGH/MEDIUM/LOW/NONE → ALLOW/REVIEW/REFUSE
- 拒答：知识库无充分依据 → 明确拒答，不编造产品事实（E2E 验证）
- Citation：Product QA 参考来源区 + Script 生成结果「产品知识依据」区（文档标题/章节/相关度/来源）
- **产品边界**（Task 13）：`product_type` 元数据精确匹配（缺失回退文档标题），错误产品不得作为有效依据

## 7. 已知问题（详见 project-status.md）

| 级别 | 项 | 状态 |
|------|-----|------|
| P1-3 | growth_service.course_detail 生产路径仍 Demo Only（DB 无课程表） | 未解决（不影响主链路） |
| P1-6 | 前端既有 TypeScript 类型错误，CI 暂用 `vite build` 绕过 tsc 硬门禁 | 未解决（本任务明确不处理） |
| P2-1 | 无 CSRF 显式防护 | 低风险（JWT Bearer） |
| P2-2 | Demo 模式无 Token 返回 200 | 低风险（仅 Demo） |
| P2-3 | 前端页面组件无测试 | 仅 utils 有 vitest |
| P2-4 | Seed 未集成到迁移 | 需手动执行 |

## 8. 仓库卫生（Task 14 清理后）

- 已删除：`download/`、`upload/`（Codex Prompt）、`tool-results/`、`skills/`（1479 文件，无引用）、根 `.env`（移出 Git 跟踪）
- 已归档：`docs/project-audit.md` → `docs/archive/project-audit-initial.md`
- 无真实 Secret 进入仓库（历史 `.env` 仅含本地 sqlite 路径）
- 详见 [docs/repository-cleanup-audit.md](repository-cleanup-audit.md)
