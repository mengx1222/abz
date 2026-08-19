# 测试体系 — 安诊保 AI 副驾

> 最后校准：2026-08-17（以当前代码 + 最新 CI 为准）
> 本文档描述**当前实际存在的测试体系**，不包含规划中的测试。

---

## 1. 测试分层总览

| 层级 | 工具 | 运行位置 | 覆盖内容 |
|------|------|----------|----------|
| 后端单元测试 | pytest + pytest-asyncio | 本地 / CI `backend-tests` | Service 逻辑、合规引擎、安全模块、AI Gateway |
| 后端 API 集成测试 | pytest + httpx | CI `backend-tests` | 各 Router 端点、认证、RBAC、SSE |
| PostgreSQL 集成测试 | pytest（`AZB_TEST_DATABASE_URL`） | CI `backend-pg` | 真实 PG16+pgvector 上的生产路径（RAG 检索器、事务、聚合） |
| 前端单元测试 | Vitest + Testing Library | 本地 / CI `backend-tests`（frontend job） | utils（authStore / cn / roleRoutes） |
| Playwright E2E | @playwright/test | CI `e2e-playwright` | 浏览器级黄金路径（Login/Dashboard/Customer/Product QA/Script/Citation/Compliance/产品边界） |
| Real AI Smoke | phase9 脚本（opt-in workflow） | CI `real-ai-smoke`（手动触发） | 真实 DashScope/Qwen 端到端 |
| Production Validation | Docker Compose 全栈 | CI `production-validation` | 真实容器（PG+Redis+backend+frontend）构建与启动 |

---

## 2. 三类 AI 测试（严格区分）

| 类型 | Provider | 确定性 | 成本 | 触发 |
|------|----------|--------|------|------|
| **Mock AI Test** | `mock`（伪向量/固定响应） | ✅ 确定性 | 免费 | PR / 本地 / CI 常规 |
| **Production-like AI Integration** | `mock` 或已配置 Provider，真实 PG + Redis wiring | 部分 | 低 | CI `backend-pg` + E2E |
| **Real AI Smoke** | 真实阿里云百炼 DashScope（qwen-plus / text-embedding-v3） | ❌ 非确定 | 真实计费（每次调用量小） | CI `real-ai-smoke`（配 Secret 后手动触发） |

> 原则：Mock 测试结果**不得**写成 Real AI 结果；Real AI 结果以 `real-ai-smoke` 运行日志为准（8/8 PASS，见 [project-status.md](project-status.md) G 记录）。

---

## 3. 后端测试（pytest）

### 3.1 目录结构（`backend/tests/`）

```
tests/
├── conftest.py / api/conftest.py
├── api/            # API 集成：auth/customer/script/training/community/dashboard/growth/notification/admin/health
└── unit/           # 单元 + 生产路径：auth/authorization/compliance/sanitize/rate_limit/rag_safety
                    #   + Service production（community/dashboard/growth/notification/script/training）
                    #   + ai_gateway_production + pg_integration（真实 PG）
```

### 3.2 关键覆盖

- **RAG / 安全**：`test_rag_safety.py`（拒答阈值、置信度门控、Prompt Injection）、`test_script_rag_production.py`（产品边界、RAG 命中→Citation、未命中→拒答、AI 失败→不伪造）
- **PG 集成**：`test_pg_integration.py`（`AZB_TEST_DATABASE_URL` 未设置时自动跳过；CI 的 PG 服务容器提供真实 PG16+pgvector，含 `TestPgRagProductBoundary` 产品边界测试）
- **Compliance**：`test_compliance.py`（GREEN/YELLOW/RED 规则）
- **Auth / 权限**：`test_auth.py`、`test_authorization.py`（RBAC、IDOR 防护）

运行：

```bash
cd backend
pytest                              # 全部
pytest -m integration               # 集成（SQLite 兼容路径）
pytest tests/unit/test_pg_integration.py  # 需 AZB_TEST_DATABASE_URL
```

---

## 4. 前端测试（Vitest）

- 位置：`frontend/src/tests/`
- 覆盖：
  - utils：`authStore.test.ts` / `cn.test.ts` / `roleRoutes.test.ts`
  - 组件：`features/knowledge.test.tsx`（13，Task 23）、`features/dashboard.test.tsx`（4）、`features/compliance.test.tsx`（8）、`features/customers.test.tsx`（6）（Task 24，P2-3）
- 运行：`cd frontend && npm test`（`vitest run`）
- 构建：`npm run build`（`tsc -b && vite build`；Task 19 已恢复 tsc 硬门禁）

---

## 5. Playwright E2E（浏览器级）

### 5.1 配置（`frontend/playwright.config.ts`）

- 双项目：`login-flow`（真实表单登录，空白 session）+ `chromium`（storageState 预登录）
- `workers: 1` 串行（确定性数据）
- 失败自动：screenshot / trace / video（retain-on-failure）
- 错误监控：`page.on('console')`（error 级）+ `page.on('pageerror')` + `/api/v1/*` 4xx/5xx → 失败
- 确定性等待（locator/expect/waitForURL），**无 `sleep(5000)`**

### 5.2 Global Setup（`frontend/e2e/global-setup.ts`）

- 确定性 AGENT 账号 `13800138000/888888` 登录 → storageState（`abz_token`/`abz_user`）
- 幂等创建确定性测试客户 `E2E-张先生 / 13900001111`
- 确定性知识库 seed（`backend/scripts/e2e_seed_knowledge.py`：2 文档 × 3 chunk，含 `product_type` 元数据）

### 5.3 用例清单（13 项）

| Spec | 覆盖 |
|------|------|
| `e2e/auth/login.spec.ts` | 真实表单登录 → /dashboard |
| `e2e/dashboard/dashboard.spec.ts` | 统计卡片渲染、无 JS error |
| `e2e/customers/customers.spec.ts` | 列表 + 确定性客户 + 搜索 |
| `e2e/customers/customer-detail.spec.ts` | 详情 + 基本信息 + AI 入口 |
| `e2e/product-qa/product-qa.spec.ts` | 页面/真实问答/Citation（参考来源+文档名）/RAG Refusal |
| `e2e/scripts/script-generation.spec.ts` | 页面/真实生成+Compliance+**Citation UI**/错误产品拒答（**产品边界**） |
| `e2e/training/training.spec.ts` | 页面加载 + **完整训练**（确定性场景→开始→SSE≥2轮→完成→评分/反馈） |

### 5.4 E2E 环境

- 真实 PostgreSQL + Redis + **真实 AI Provider（DashScope/Qwen，GitHub Secrets 注入，无 Key 回退 mock）**
- CI：`.github/workflows/e2e-playwright.yml`（独立 job，不影响 backend/frontend/production-validation）
- E2E 阶段三（Task 17A）：**Training（AI 陪练）浏览器级验证**——确定性场景（seed 内置「太贵了—重疾险价格犹豫」等）→ 开始训练 → SSE 消息（message_start/token/coaching/turn_complete）≥2 轮 → 结束训练 → 评分/反馈（scoring_start/token/score_data/scoring_complete）可见；断言不依赖固定 AI 文案

---

## 6. Real AI Smoke（真实 Provider 端到端）

- 脚本：`backend/scripts/phase9_real_ai_smoke.py`
- Workflow：`.github/workflows/real-ai-smoke.yml`（opt-in，需 GitHub Secrets：`AZB_AI_API_KEY` / `AZB_AI_BASE_URL` / `AZB_AI_MODEL` / `AZB_AI_PROVIDER`）
- 覆盖 8 项：真实 Chat / 真实 SSE / 登录 / Product QA（真实 RAG→LLM→SSE）/ Script 生成（Citation+Compliance）/ RAG 拒答 / 社区摘要 / 培训场景
- 最近结果：**8/8 PASS**（run 31866434810，commit `94ce52f`，Provider=阿里云百炼 DashScope，Model=qwen-plus）

---

## 7. Production Validation（Docker 全栈）

- Workflow：`.github/workflows/production-validation.yml`
- 内容：`docker compose -f docker-compose.prod.yml` 构建并启动 postgres/redis/backend/frontend → 健康检查 → 后端 ready → 关键 API 冒烟
- 状态：✅ 全绿（最近 HEAD `575f8f2`）

---

## 8. 测试数据确定性

- 固定测试账号：AGENT `13800138000/888888`（DEMO ONLY）
- 固定测试客户：`E2E-张先生 / 13900001111`
- 固定知识库：`E2E产品知识库`（幂等 seed，含产品边界元数据）
- 不使用随机手机号/UUID/客户/AI 文案断言

---

## 6. TypeScript 门禁（Task 19 恢复）

- **`npx tsc -b` = 0 errors**（cloud runner 验证，Frontend Typecheck workflow @ `acebb0e`）
- CI frontend job 含显式 **TypeScript typecheck** 步骤（`npx tsc -b`，exit code != 0 → job failed）+ Build 使用 `npm run build`（`tsc -b && vite build`）
- 独立 `frontend-typecheck.yml` 快速验证 workflow（frontend/** 变更触发）
- 基线 32 errors → 0 errors 的完整分类与修复见 [typescript-cleanup-audit.md](typescript-cleanup-audit.md)


---

## 7. Admin 前端 Production 测试（Task 23）

- **组件测试**：`frontend/src/tests/features/knowledge.test.tsx`（vitest + testing-library，mock knowledgeService，13 用例）——
  KB list/empty/error/403、Document list/empty/detail/404、publish/unpublish、delete（confirm/403）、KB delete
- **E2E**：`frontend/e2e/knowledge/knowledge.spec.ts`（K-1 KB 列表 / K-2 文档列表 / K-3 文档详情，production 后端 + e2e_seed_knowledge 数据）
- **根因修复**：service 原返回 SuccessResponse 包装对象 → 页面 `knowledgeBases.map` 崩溃白屏
  （既有 bug，E2E K-1 暴露）→ 全部 `res.data.data` 解包

---

## 8. Security & Engineering Hardening（Task 24）

### 8.1 安全态势回归（`backend/tests/api/test_security_posture.py`，7 用例）

- **CSRF posture（P2-1，4 用例）**：登录/受保护端点响应无 Set-Cookie（无 cookie 会话 → CSRF 攻击面不存在）；状态修改端点（POST/PUT/DELETE）无 Bearer → 401；无效 token / refresh 类型错误 → 401 语义码。防御性回归：未来若引入 cookie 会话，CI 立即失败提示重新评估。
- **Auth 错误语义契约（P2-2，3 用例）**：login 失败 → 统一 `ErrorResponse{success:false,error:{code,message}}`；get_current_user 拒绝 → `{detail:{code,message}}`；refresh 失败格式。
- **根因修复验证**：`ErrorHandlerMiddleware` 曾吞 HTTPException → 受保护端点认证失败返回 500（前端 401 登出静默失效）——修复后 401 用例全绿。

### 8.2 E2E seed 幂等（`backend/tests/knowledge/test_e2e_seed_idempotency.py`，3 用例，backend-pg）

- 首次创建 True / 二次调用跳过 False（幂等，不重复插入）
- embedding 失败 → RuntimeError 且无半成品残留（rollback 验证）
- 计数不一致 → 跳过 + WARN（不静默、不破坏数据）

### 8.3 组件测试扩展（P2-3，+18 用例）

| 文件 | 用例 | 覆盖状态 |
|------|------|----------|
| `features/dashboard.test.tsx` | 4 | loading / error+重试 / 数据渲染 / 空 AI 建议区块 |
| `features/compliance.test.tsx` | 8 | rules loading/error/empty/list/toggle；reviews list/approve/error |
| `features/customers.test.tsx` | 6 | loading / error / empty / list / delete mutation / pagination |


---

## 9. Test Infrastructure Hardening（Task 26）

### 9.1 Production 组织树递归实测（`tests/rag/test_org_tree_pg.py`，3 用例，backend-pg）

- **背景**：DataPermissionChecker._collect_child_org_ids 依赖 Organization.children（lazy=selectin）；真实 async + PG + DEMO_MODE=false 下访问抛 MissingGreenlet 被静默吞掉 → HQ_ADMIN/BRANCH_ADMIN 范围退化为仅本组织（真实 bug，本任务修复）。
- **修复**：deps.py get_current_user 嵌套 selectinload 组织树（HQ→Branch→Team）；权限模型不变。
- **用例**：HQ 全子树 / BRANCH 子树不含兄弟 / TEAM 仅本团队。
- **验证**：backend-pg 38 passed（35 + 3）。

### 9.2 Workflow 测试基础设施审计（docs/test-infrastructure-audit.md）

- 各 workflow 独立 PG 容器（backend-pg docker run / E2E services / Prod compose）→ 无跨 workflow 污染
- 干净 PG 每轮 alembic upgrade head（0001→0009）→ migration chain 有效
- seed 幂等：scripts.seed get-or-create；e2e_seed_knowledge 存在即跳过（Task 24）
- RAG 权限测试随机 suffix 隔离 + 防御性清理 org=NULL KB（N8 已消除）


---

## 10. AI Sales Agent 测试（Task 27）

### 10.1 Unit（tests/unit/test_agent_orchestrator.py，12 用例）

- Tool Registry 白名单/未知工具/超时、黄金链 SSE 事件顺序、无产品类型跳 RAG、客户不存在/越权 IDOR、Prompt Injection 拒答、RAG REFUSE 跳话术、Compliance RED 透传、Provider 失败不 fallback、循环/预算防护、Session 连续性、Script REFUSE 透传
- 模式：SQLite + DEMO_MODE=false + mock provider + 最底层 FakePipeline（保持 Agent→Service→Pipeline→Compliance 真实 wiring）

### 10.2 PG + pgvector（tests/rag/test_agent_pg.py，5 用例）

- RAG 工具角色+组织双权限过滤（citation 不泄漏）、无权 KB 内容不泄漏、完整黄金链、跨组织客户 IDOR、注入全链拒答

### 10.3 真实 AI Smoke（backend/scripts/phase10_ai_sales_agent_smoke.py）

- 真实登录 → 客户 → RAG → Script → Compliance → SSE 事件流 → agent_complete；opt-in（workflow_dispatch / Secrets），无 key NOT RUN


## 11. AI Sales Agent 前端测试（Task 28）

### 11.1 组件测试（tests/features/salesAgent.test.tsx，11 用例）

- initial/正常 SSE/Citation/Compliance GREEN-YELLOW-RED/RAG REFUSE/404/Provider error/stream error/retry/防重复/客户 404
- mock salesAgentService（保留 AgentHttpError 语义）+ customerService；不依赖真实 AI

### 11.2 E2E（e2e/sales-agent/sales-agent.spec.ts，2 用例）

- G-1 黄金路径：登录 → /sales-agent/{customerId} → 客户上下文 → 输入销售问题 → tool_planned 安全状态 → 非空结果 → 无浏览器/API 错误
- G-2 安全场景：知识库无匹配产品 → RAG REFUSE → 明确「当前知识库没有足够的产品依据」
- 不依赖固定 AI 文案，只断言稳定事实
