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
- 覆盖：`authStore.test.ts` / `cn.test.ts` / `roleRoutes.test.ts`
- 运行：`cd frontend && npm test`（`vitest run`）
- 构建：`npm run build`（`tsc -b && vite build`；注：tsc 硬门禁存在既有类型错误，CI 暂用 `vite build`，见 project-status P1-6）

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
