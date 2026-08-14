# 安诊保 AI 副驾 — 项目状态（唯一事实来源）

> **本文件是项目状态的唯一事实来源。每完成一个 Phase 必须更新。**
> 最后更新: 2026-08-14
> Git HEAD: `1843649`
> 后端版本: `1.0.0-rc.1`

---

## A. 当前 Phase

**当前: Phase 6 — 内部试点发布准备（部分完成）**

---

## B. Phase 完成记录

### Legacy MVP Phases（旧编号体系 — 功能开发）

| Phase | 内容 | Git Commit | 状态 |
|-------|------|-----------|------|
| MVP-1 | 基础工程搭建 (FastAPI + React + Docker) | 初始 commit | ✅ 完成 |
| MVP-2 | 用户认证 + RBAC + JWT | 早期 commit | ✅ 完成 |
| MVP-3 | 知识库 + RAG Pipeline (Demo) | 早期 commit | ✅ 完成 |
| MVP-4 | AI 话术模块 + SSE 流式 + 合规引擎 | `e4d225c` Phase 6(旧) | ✅ 完成 |
| MVP-5 | 客户 360° (CRUD + AI 分析) | `e4d225c` Phase 5(旧) | ✅ 完成 |
| MVP-6 | AI 陪练 (场景 + SSE 对话 + 评分) | `b42da9a` Phase 7(旧) | ✅ 完成 |
| MVP-7 | AI 社区 (帖子/评论/点赞/收藏/AI 摘要) | `bdd7389` Phase 8(旧) | ✅ 完成 |
| MVP-8 | 管理后台 (用户/看板/审计/合规/设置) | `146afa2` Phase 9(旧) | ✅ 完成 |
| MVP-9 | 成长体系 + 通知中心 + Dashboard | `72c367f` Phase 10(旧) | ✅ 完成 |

### Productionization Phases（新编号体系 — 生产化）

| Phase | 内容 | Git Commit | 状态 |
|-------|------|-----------|------|
| Prod-1 | 当前状态审计 + 文档校准 | `4441b38` + 本次更新 | ✅ 完成 |
| Prod-2 | Demo/Production 架构分层 (Repository + Service bifurcation) | `79c31b6` | ✅ 完成 |
| Prod-3 | 数据库持久化 (迁移链修复 + 30 表 + Seed) | `1dbf948` | ✅ 完成 |
| Prod-4 | RAG 生产化 (拒答 + 置信度 + Prompt Injection + 版本管理 + 组织隔离) | `a68511c` | ✅ 完成 |
| Prod-5 | 权限安全强化 (IDOR + Rate Limit + 审计 + 脱敏 + 安全头 + 前端 RoleGuard) | `a68511c` | ✅ 完成 |
| Prod-6 | 全链路测试与生产加固 (133 pytest + 27 vitest + Docker 生产配置) | `f2db21f` | ✅ 完成 |
| Prod-7 | 内部试点发布准备 (监控 + 健康检查 + UAT) | Phase 6 本次 + 未提交 | 🔄 进行中 |

---

## C. Production Ready 模块

以下模块代码已就绪，Demo/Production 双路径均已实现：

| 模块 | Demo | Production | 说明 |
|------|------|-----------|------|
| 基础工程 (FastAPI + React) | ✅ | ✅ | |
| JWT 认证 | ✅ | ✅ | |
| RBAC 7 角色 | ✅ | ✅ | |
| 数据库 30 表 | N/A | ✅ | 7 迁移链完整 |
| Repository 7 个 | N/A | ✅ | BaseRepository + 6 业务 Repo |
| Service Bifurcation 8 个 | ✅ | ✅ | |
| RAG Pipeline | ✅ Mock | ✅ pgvector+BM25+RRF | |
| RAG Safety (拒答/置信度/注入检测) | ✅ | ✅ | |
| IDOR 防护 | ✅ | ✅ | 7 角色行级权限 |
| Rate Limiting | ✅ | ✅ | |
| 审计日志 | ✅ (DB pending) | ✅ | |
| 数据脱敏 | ✅ | ✅ | |
| 安全头 (CSP/HSTS/X-Frame) | ✅ (宽松) | ✅ (严格) | |
| 前端角色路由守卫 | ✅ | ✅ | |
| 前端代码分割 | ✅ | ✅ | 入口 ↓34% |
| 健康检查 3 端点 | ✅ | ✅ | Liveness + Readiness + Detail |
| 请求监控日志 | ✅ | ✅ | structlog |

---

## D. Demo Only 模块

以下模块在 Demo 模式使用内存数据，Production 模式需真实 DB/AI：

| 模块 | 说明 |
|------|------|
| AI Gateway | Demo 使用 MockProvider，Prod 需配置真实 AI API Key |
| AI Embedding | pgvector 向量嵌入需真实 OpenAI/DeepSeek Embedding API |
| 所有 Service Demo 数据 | 8 个 Service 的 Demo 数据为内存硬编码，Prod 模式走 Repository→DB |

---

## E. P0 / P1 / P2

### P0 — 无

### P1

| # | 风险 | 说明 |
|---|------|------|
| P1-1 | PostgreSQL + pgvector 真实环境未验证 | 代码就绪，需实际运行 `alembic upgrade head` + 全链路 |
| P1-2 | AI Provider 未接入真实模型 | 需配置 API Key 并验证 SSE 流式 |
| P1-3 | ScriptService 生产路径复用 demo 逻辑 | `generate_scripts()` 的 else 分支调用了 `_demo_generate_scripts` |
| P1-4 | 无 Playwright E2E 测试 | 仅有 API 级 UAT，无浏览器级 E2E |

### P2

| # | 风险 | 说明 |
|---|------|------|
| P2-1 | 无 CSRF 显式防护 | JWT Bearer 下风险较低 |
| P2-2 | Demo 模式无 Token 返回 200 | Prod 模式应正常返回 401 |
| P2-3 | 前端页面组件无测试 | 仅 3 个工具文件有 vitest |
| P2-4 | Seed 脚本未集成到迁移 | 需手动执行 |

---

## F. 下一阶段建议

**用户提出的三个方向，按优先级排序：**

### 方向 1: PostgreSQL + pgvector 真实环境验收 (优先级: 最高)

**原因**: 当前所有 Production 代码路径已就绪，但从未在真实 PostgreSQL + pgvector 环境验证。这是从 "代码就绪" 到 "真正 Production Ready" 的关键一步。

**建议范围**:
1. 启动 PostgreSQL + pgvector Docker 容器
2. 执行 `alembic upgrade head`（全部 7 个迁移）
3. 执行 seed.py 种子数据
4. 以 `AZB_DEMO_MODE=false` 启动后端
5. 验证所有 API 端点在真实 DB 下正常工作
6. 验证 RAG Pipeline 在真实 pgvector 下工作（需 AI Embedding API）

### 方向 2: Web E2E (Playwright) (优先级: 中)

**原因**: 当前有 API 级 UAT (23/23) 但无浏览器级 E2E 测试。Playwright 可覆盖真实用户操作路径。

### 方向 3: AI Sales Agent (优先级: 中低)

**原因**: 需要先完成方向 1（真实 AI 环境），才能有效串联 AI 销售助手全链路。

---

## G. 最后验证记录

| 项目 | 结果 | 时间 |
|------|------|------|
| 后端 pytest | **133 passed** (23.32s) | 2026-08-14 |
| 前端 vitest | **27 passed** (2.52s) | 2026-08-14 |
| 前端 TSC | **0 errors** | 2026-08-14 |
| 前端 Vite Build | **OK** (374KB entry / 120KB gzip) | 2026-08-14 |
| UAT 冒烟测试 | **23/23 passed** (7.83s) | 2026-08-14 |
| 后端 App Import | **OK** (v1.0.0-rc.1) | 2026-08-14 |
| RAG Safety 拒答 | **OK** (空结果→refuse=True) | 2026-08-14 |
| RAG Safety 注入检测 | **OK** (malicious 检测正常) | 2026-08-14 |
| Rate Limiter | **OK** (10 granted, 5 rejected on 15 requests) | 2026-08-14 |
| 数据脱敏 | **OK** (手机/身份证/姓名/邮箱) | 2026-08-14 |
| Bifurcation | **38/38 methods** 全部正确 | 2026-08-14 (Phase 6 Task 6-1) |
| 模型注册 | **30 tables** 全部可导入 | 2026-08-14 |
| 迁移链 | **7 migrations** (0001→0007) | 2026-08-14 |
