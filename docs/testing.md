# 测试体系 — 安诊保 AI 副驾

> 最后校准：2026-08-20（以当前代码 + 最新 CI 为准）
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
- 覆盖（当前 16 files / **107 用例**，Task 33 全绿）：
  - utils：`authStore.test.ts` / `cn.test.ts` / `roleRoutes.test.ts`
  - 组件：`components/ErrorBoundary.test.tsx`（4，Task 33）
  - features：knowledge（13）/ salesAgent（11）/ compliance（8）/ communityManage（7）/ scriptManage（6）/ trainingManage（6）/ customers（6）/ users（5）/ analytics（4）/ auditLog（4）/ dashboard（4）/ settings（3）—— Admin 8/8 页面全覆盖（Task 24/25/28/32，P2-3）
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

### 8.1 安全态势回归（`backend/tests/api/test_security_posture.py`，12 用例）

- **CSRF posture（P2-1，4 用例）**：登录/受保护端点响应无 Set-Cookie（无 cookie 会话 → CSRF 攻击面不存在）；状态修改端点（POST/PUT/DELETE）无 Bearer → 401；无效 token / refresh 类型错误 → 401 语义码。防御性回归：未来若引入 cookie 会话，CI 立即失败提示重新评估。
- **CSRF 回归（Task 34，5 用例，TestCsrfSecurityRegression）**：GET/POST + Bearer 无 CSRF token 正常（JWT Header 模式无攻击面证明）/ demo 登录兼容（token 下发 + 无 Set-Cookie）/ 安全头不回归（nosniff/X-Frame-Options DENY/Referrer-Policy）/ 上传大小限制 demo 分支 413。
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


---

## 12. Golden Business Flow E2E（Task 29）

### 12.1 GF-1 浏览器级完整黄金链（e2e/golden-flow/golden-flow.spec.ts）

- 登录(storageState=AGENT 13800138000) → /dashboard → /customers（确定性客户 E2E-黄金链客户/13900002222/医疗险，幂等创建+更新）→ 客户详情 → /sales-agent/{同一 customerId}（URL 断言一致）→ 客户上下文 → 输入销售问题 → tool_planned 安全状态 → 结果非空 → Citation（产品知识来源≥1）→ Compliance（合规检查 GREEN/YELLOW/RED）→ /training（确定性场景 2 轮 SSE + 结束训练 + 评分非空）→ /growth（能力评估 4 项出现 = ability_scores 仅来自训练评分）+ API 断言 total_exp ≥ 训练前+10
- 稳定事实断言（不依赖 AI 文案）；console/pageerror/API 4xx 监控；300s 超时

### 12.2 Real AI Golden Flow Smoke（backend/scripts/phase11_golden_flow_smoke.py）

- 真实 Provider + DEMO_MODE=false + 真实 PG/Redis：登录 → 客户 → Agent SSE（agent_start/tool_planned/rag_context/citation/agent_complete/compliance）→ Training（2 轮+评分）→ Growth（ability_scores 非空 + total_exp≥10）；opt-in（workflow_dispatch / REAL_AI_SMOKE_TEST），无 key NOT RUN

---

## 13. 前端稳定性加固（Task 33）

### 13.1 全局 ErrorBoundary（`components/ErrorBoundary.tsx` + 4 用例）

- 现状：Task 31 审计记录 P2「无 ErrorBoundary」——仓库此前无任何错误边界，任意页面渲染错误 → 整页白屏无恢复路径。
- 实现（仅防御性 UI 基建，不改业务逻辑/API contract）：类组件 ErrorBoundary（getDerivedStateFromError + componentDidCatch），fallback = 「页面出现异常」+ 重新加载按钮 + 返回首页链接；`app/App.tsx` 全局包裹（ErrorBoundary → QueryClientProvider → RouterProvider）。
- 测试（`tests/components/ErrorBoundary.test.tsx`，4 用例）：无错误正常渲染 / 子组件抛错 fallback（不白屏）/ 抛错后不渲染 children / 自定义 onError 回调（error + errorInfo）。
- 验证（045f87d 全矩阵）：Vitest **107 passed（16 files）**、tsc -b 0、build ✓、Backend 291/44、backend-pg 44、E2E 27、Prod ✅。

---

## 14. 安全收敛（Task 34）

### 14.1 CSRF 复核（P2-1 already resolved）

- 审计（docs/csrf-security-audit.md）：认证 = JWT Bearer header（HTTPBearer），无 cookie 会话（登录响应无 Set-Cookie、前端 axios 无 withCredentials、token 存 localStorage）→ **无 CSRF 攻击面**；不引入 CSRF token/中间件（与 Bearer 架构冲突，避免无效 CSRF）。
- 新增回归（`TestCsrfSecurityRegression`，5 用例）：GET+JWT 200 / POST+JWT 200（无需 CSRF token）/ demo 登录兼容 / 安全头不回归 / 上传大小限制 demo 分支 413。

### 14.2 KB 文档上传大小限制（P2 收敛）

- `config.py::MAX_UPLOAD_SIZE_MB`（默认 10MB）；`knowledge.py::upload_document` Content-Length 预检（超限立即 413，不读 body）+ 读取后权威校验（防伪造 Content-Length）；demo/production 分支同享。
- 测试：`test_kb_crud.py::test_upload_document_size_limit`（backend-pg，PG 45 passed：超限 413 / 正常 200）。

### 14.3 验证（9dea567 全矩阵）

- Backend pytest **296 passed / 45 skipped**；backend-pg **45 passed**；Frontend Vitest **107（16 files）**、tsc 0、build ✓；Production Validation ✅（E2E 未触发：无 frontend/src 变更）。

---

## 15. Seed & Deployment Consistency（Task 35）

### 15.1 seed.py 幂等回归（`backend/tests/knowledge/test_seed_idempotency.py`，3 用例，backend-pg）

- 首次运行成功（7 角色 / 21 权限 / 6 组织 / 4 用户全部落库，每 code/name/phone 恰好 1 条）
- 二次运行成功且不产生重复数据（数量仍为 1）
- 权限关系正确（角色-权限绑定与 ROLE_PERMISSIONS 一致；用户角色/组织映射正确）

### 15.2 实测发现的真实 bug（CI 驱动）

- `scripts/seed.py` 绑定插入缺 `await` → `role_permissions` 绑定**静默不落库**（seed 输出「✅ xxx: N 权限」仅为打印）。权限关系测试首跑失败暴露（15bba45 CI FAILED）→ 补 `await` 修复（df00d11）。

### 15.3 环境一致性修复

- `config.py::APP_VERSION` 1.0.0-rc.1 → **0.1.0**（对齐 pyproject/package.json/README，health 端点对外版本号正确）
- `frontend/Dockerfile`：`npx vite build` → **`npm run build`**（生产镜像构建对齐 CI tsc 硬门禁）
- backend-pg workflow：纳入 `test_seed_idempotency.py`

### 15.4 验证（df00d11 全矩阵）

- Backend pytest **296 passed / 48 skipped**；backend-pg **48 passed**（+3 seed 幂等）；Frontend Vitest **107（16 files）**、tsc 0、build ✓；Production Validation ✅；E2E 未触发（无 frontend/src 变更）。

---

## 16. Release Candidate Final Audit（Task 36）

- 只读审计（docs/release-candidate-audit.md）：199 个源码文件全文扫描（TODO/FIXME 4 处已知限制、NotImplemented 0、bare except 全部复核无害、console.log 0、@ts-ignore 0、`any` 5 处低优先级）；六域全部 PASS，**无新增修复/测试**（前序任务已收敛）。
- 测试数字维持（df00d11/783cb61）：Backend **296 passed / 48 skipped**、backend-pg **48 passed**、Vitest **107（16 files）**、tsc 0、build ✓、E2E **27 passed**、Prod ✅。

---

## 17. Audit Log 持久化测试（Task 37）

### 17.1 backend-pg（`tests/knowledge/test_audit_log_pg.py`，11 用例）

Task 37b 增补 5 用例（`TestAuditLogPermission`）：角色越权 AGENT→403 / 组织越权 BRANCH_ADMIN 不见他组织行 / 同组织可见 / SYSTEM_ADMIN 全库可见 / 敏感字段不落库（中间件行 detail 仅 status_code，description 无 password/jwt/token/secret）。

- Repository：create_log + list_logs 字段正确（user_id/resource_id/detail JSONB）/ 过滤分页 / query_by_user / query_by_resource
- API：KB create（生产）→ audit 落库（user_id/resource_id/description 正确）/ 删除 KB 后 audit 仍存在 / `GET /admin/audit-logs` 生产分支返回真实审计行（同 schema，含 user_name）

### 17.2 Demo 回归（`tests/api/test_audit_log.py`，4 用例）

- login 成功/失败 / logout / audit-logs demo 分支照常（审计 helper demo 路径仅 structlog，不触碰 DB）

### 17.3 排障记录（CI 驱动）

- 误建 0010 迁移（request_id 已由 0007 提供）→ `DuplicateColumnError` 暴露 → 删除迁移，head 保持 0009
- `get_current_user` 加 `Request` 参数：先遇 FastAPI 不支持 `Request | None`（FastAPIError），后遇「无默认值参数跟在默认参数后」（SyntaxError）→ 改为 `request: Request` 置于默认参数之前

### 17.4 验证（6fc74db 全矩阵）

- Backend pytest **300 passed / 59 skipped**；backend-pg **59 passed**（audit 11 全过）；Vitest **107（107）**、tsc 0、build ✓；Prod ✅。

---

## 18. Database Backup & Restore 演练（Task 38）

### 18.1 云端演练（`.github/workflows/database-backup-restore.yml`，PG16 + pgvector）

- 步骤链：alembic upgrade → seed → 合成业务数据 fixture（KB/Document/3 chunks/AuditLog，embedding 1536）→
  baseline 快照 → `backup_database.sh`（pg_dump custom）→ 完整性（size>0 + sha256）→ 干净目标库 →
  `restore_database.sh`（pg_restore --clean --if-exists）→ `verify_restored_db.py` 对比 → 应用 /ready → 错误凭据非 0 → 无备份文件入 Git。
- 结果（24cc2b1，run 32344482596 全绿）：`FIXTURE_OK / SNAPSHOT_OK / BACKUP_OK(size=131217) / INTEGRITY_OK /
  RESTORE_OK / VERIFY_OK（restored==baseline，mismatches={}）/ APP_READY / NONZERO_OK / NO_BACKUP_IN_GIT_OK`。
- 关键数据：users 4 / roles 7 / organizations 6 / knowledge_bases 1 / documents 1 / document_chunks 3 /
  audit_logs 1 / training_scenarios 23 / alembic 0010 / chunks_with_embedding 3 / embedding_dims 1536。

### 18.2 排障记录（CI 驱动）

1. `pg_restore "$URL" ... -d "$DUMP"`：`-d` 期望 dbname，把 dump 路径当 dbname → pg_restore 从空 stdin 读取 exit 0 未恢复 → 改为 `-d "$LIBPQ_URL"` + dump 位置参数。
2. `bash script | tee log` 管道掩蔽退出码（tee 返回 0）→ workflow 步骤加 `set -o pipefail`。
3. 中间件/显式 audit 已由 Task 37/37b 覆盖，本 Task 无 backend/frontend 源码变更，无回归面。

---

## 19. Observability & Redaction（Task 39）

### 19.1 云端验证（0425d67 全矩阵）

- Backend pytest **307 passed / 59 skipped**（+7 `tests/api/test_observability.py`）；backend-pg **59 passed**；Vitest **107**；tsc 0；build ✓；Prod ✅。

### 19.2 `test_observability.py` 覆盖（7 用例）

1. `test_request_id_propagates`：X-Request-ID 响应头回显
2. `test_health_detail_masks_secret`：masked URL 无明文密码（含无用户名 redis URL 的 mask 修复）
3. `test_ready_503_on_db_failure`：DB 不可达 → 503 + `READINESS_FAILED` + checks.database=unreachable
4. `test_ready_200_when_dependencies_ok`：依赖正常 → 200 ready（不回归）
5. `test_request_log_contains_user_id`：request 结构化日志含 user_id（capsys 捕获 stdout）
6. `test_ai_error_code_auth_logged`：AI 401 → `OPENAI_CHAT_AUTH`，body 不回显（redaction）
7. `test_ai_error_code_rate_limit_logged`：AI 429 → `OPENAI_CHAT_RATE_LIMIT`

### 19.3 排障记录

- `_mask_url` 原正则 `(://[^:]+:)([^@]+)(@)` 不匹配无用户名 URL（`redis://:pass@host`）→ 放宽为 `(://[^:@]*:)([^@]+)(@)`。

---

## 20. Redis Multi-instance（Task 40）

### 20.1 云端验证（c2a6eae 全矩阵 + 专用 workflow）

- CI：Backend pytest **307 passed / 68 skipped**；backend-pg **59 passed**（production 限流在真实 Redis 上正常）；
  Vitest **107**；Prod ✅。
- `redis-multiinstance.yml`（真实 Redis）：**9/9 PASSED**。

### 20.2 `test_redis_multiinstance.py` 覆盖（9 用例，AZB_TEST_REDIS_URL 跳过逻辑）

1. `test_ping`：Redis connectivity
2. `test_concurrent_incr_exact_count_and_ttl`：20 并发 INCR → 精确 1..20（原子无竞态）+ TTL>0
3. `test_ttl_reapplied_on_same_key`：同 key 后续 INCR 不重置 TTL（递减）
4. `test_counter_shared_across_clients`：实例 A/B（独立 client）共享同一计数
5. `test_set_get_delete_and_ttl`：session store CRUD + TTL
6. `test_instance_a_writes_instance_b_reads`：实例 A 写 → 实例 B 读一致
7. `test_incr_returns_none_when_redis_down`：Redis 不可用 → incr None（fail-closed 信号，不静默）
8. `test_session_store_get_none_set_false_when_down`：session down → get None/set False（不静默内存）
9. `test_session_continuity_across_instances`：Agent session 跨实例连续性（customer/product/stage/history 一致）

### 20.3 排障记录（CI 驱动）

1. backend-pg 无 Redis → production 限流 fail-closed 503 破坏 audit/kb 测试 → backend-tests 两 job 起 Redis 容器。
2. `service._sessions[sid]` 在 Redis 分支不填充 → test_session_continuity 改经 `_get_or_create_session` 取回。
3. **全局 Redis client 单例绑定 pytest event loop → "Event loop is closed"** → 改为每操作短生命周期 client（`redis_store.py`）。
4. 并发 gather 返回值乱序 → 集合断言。

---

## 21. Performance Benchmark（Task 41）

### 21.1 Harness 与触发

- `scripts/benchmark_run.py`：`--mode deterministic`（ASGI，AI=mock：API/DB/Redis/RAG-SSE/容量 10 并发）、
  `--mode http`（真实 uvicorn：HTTP/SSE/容量 1/5/10）、`--mode ai`（真实 AI opt-in，需 API key）。
- `performance-benchmark.yml`：workflow_dispatch（profile/run_ai 参数）或 push 限 benchmark 相关路径；
  PG16+pgvector+Redis 容器 + alembic + seed + fixture；Layer A/B 默认跑，Layer C 仅 `run_ai=true` 且 secret 存在。

### 21.2 结果（0d47da0 run 32358977127，全部 err=0）

- API：health 1.65/2.45ms（p50/p95）、ready 31.5/32.9、kb-list 20.8/74.5；http_health 2.14/3.22（427tps）
- DB/Redis：org count 0.30/1.22ms（2908tps）、redis incr 2.32/2.63（424tps）、session 4.69/5.19（210tps）
- SSE（mock）：Product QA p50 3.2-3.5s（TTFE 19.5ms；含 mock 流延迟 ~2.8s + RAG 0.36-0.8s 真实）、Sales Agent 28.8/83.4ms（TTFE 20.4ms）
- 容量：health c1/c5/c10 p50 2.4/8.0/12.5ms，0 err（线性）
- AI 层：**NOT RUN**（无 AZB_AI_API_KEY secret；配置后手动触发）

### 21.3 排障记录

1. workflow 静态校验：step `if` 引用 `inputs`/`secrets` 在 push 触发时 Unrecognized named-value → 移到 env 运行时求值。
2. `/ready` 将默认 `redis://localhost:6379/0` 视为 not_configured → benchmark 用 `/1`。
3. `/api/v1/ai/product-qa` 404 → 实际路由 `/api/v1/ai/product-qa/chat`。
4. Sales Agent 422：`customer_id` 必填 → benchmark body 补齐。

---

## 22. Security Final Review Gate（Task 42）

- 复用安全回归（全部云端全绿）：security posture 12 / RBAC / IDOR（Task 27）/ RAG permission（Task 17B，35+PG 5）/
  citation leak / prompt injection / provider failure（test_ai_gateway）/ redaction 7（Task 39）/ audit scope 11（Task 37b）/
  backup-restore 演练（Task 38）。
- Task 42 复核未发现真正缺失的安全回归项，不造无谓测试；仓库卫生扫描 0 真实 secret。
- 判定：**PRODUCTION CANDIDATE**（Accepted Risks 见 security-final-review.md）。


---

## 23. ULTIMATE Production Close（Task 43-Hotfix / PRODUCTION-CLOSE）

### 23.1 云端验证（9dec25d 全矩阵，ULTIMATE Phase 1）

- CI `backend-tests` @ 9dec25d：**Backend 330 passed / 81 skipped**；Vitest **107**；tsc 0；build ✓；Prod ✅。

### 23.2 新增生产路径测试（+23 passed）

| 测试文件 | 覆盖 |
|----------|------|
| `tests/unit/test_customer_access_production.py`（7 单元 + PG 集成 8） | P0-1 生产 AGENT assigned_to 归属：本人可见/他人拒绝/列表详情同源/HQ-TEAM 不回归/demo 不回归；P0-5 AI 分析越权"客户不存在" |
| `tests/unit/test_conversation_persistence_production.py`（PG 集成 5） | P0-2 会话持久化：消息落库 finish_reason/sources、历史注入、user 隔离、KB 拒答 refused 落库、message_count 递增 |
| `tests/unit/test_ip_source.py`（4） | P0-3 TRUST_PROXY：伪造 XFF/X-Real-IP 不生效、可信头生效、unknown 兜底 |
| `tests/unit/test_jwt_secret_hard_gate.py`（4） | P0-4 production 默认/空密钥启动 RuntimeError、强密钥 OK、development 不拦截 |
| `tests/unit/test_security_hardening.py`（8） | P1-1 uuid→401；P1-2 路由模板聚合；P1-3 rerank 401/403 不回退（5xx 回退）；P1-5 DEBUG 不泄露；P1-6 认证统一提示 |

> 说明：P0-2/P0-1/P0-5 的 PG 集成用例在 `backend-pg` job（真实 PG16+pgvector）运行；
> unit job 中因无 AZB_TEST_DATABASE_URL 自动跳过（计入 skipped）。
