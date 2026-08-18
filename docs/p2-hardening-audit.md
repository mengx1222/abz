# P2 收敛审计 — Security & Engineering Hardening（Task 24）

> 建立时间：2026-08-19
> 基线：main@4ee44fe（Task 23 全绿）→ 完成：main@6ffa82b
> 方法：100% Cloud-only（GitHub API 读码 + GitHub Actions 验证，无本地 clone/测试）
> 范围：P2-1~P2-4 收敛；不开发 AI Sales Agent；不重构 RAG；不改 KB/Document 权限模型；不改既有 API contract

---

## P2-1 CSRF —— 状态：**ACCEPTED LIMITATION（架构无 CSRF 攻击面）+ 防御性回归测试 + 文档修正**

### 现状（源码证据）
- 认证方式：`HTTPBearer(auto_error=False)` + JWT（HS256），`app/core/deps.py:get_current_user` 从 `Authorization: Bearer` 提取 token，无 cookie 会话（deps.py L83-147）。
- 前端：`services/api.ts` axios request interceptor 设 `Authorization` header；token 存 `localStorage`（authStore `abz_token`）；axios **未启用 withCredentials**。
- 状态修改端点：全部经 `get_current_user` 依赖（login/refresh 除外）。
- CORS：`allow_origins` = `FRONTEND_URL` 白名单；仅 DEBUG/DEMO 追加 `localhost:5173` + `*`（`allow_credentials=True` 恒开，Starlette 对 wildcard+credentials 回显 Origin——demo 有意的宽松）。

### 判断
CSRF 攻击依赖浏览器**自动携带**凭据（cookie/session）。本架构凭据仅在 Authorization header（跨站 form/img/script 无法自动附带），且无 cookie 会话、前端不启用 withCredentials —— **不存在可利用的 CSRF 漏洞**。引入 CSRF token/中间件会与 Bearer 架构冲突且无防护收益，故不引入（符合任务约束）。

### 动作
1. **文档修正（Confirmed Bug：文档失真）**：`docs/security.md` §1/§2.1/§6.1/§6.2 原描述"Refresh Token 存 HttpOnly Cookie + CSRF Token 双重验证"与实现（Bearer header + localStorage）矛盾，已按实际架构修正。
2. **防御性回归测试** `backend/tests/api/test_security_posture.py::TestCsrfPosture`（4 用例）：
   - 登录/受保护端点响应**无 Set-Cookie**（无 cookie 会话）
   - 状态修改端点（POST logout）无 Bearer → 401
   - 受保护读端点无 Bearer → 401
   - 无效 token / refresh token 类型错误 → 401 语义码
   —— 未来若引入 cookie 会话或失去 Bearer 强制，CI 立即失败提示重新评估。

### 遗留
- CORS demo 模式 `*` + credentials：demo 有意的宽松（本地 dev/preview），production 白名单不受影响 → Existing Limitation，不改。

---

## P2-2 Demo 401 —— 状态：**RESOLVED**（3 个 Confirmed Bug 修复 + 测试）

### Confirmed Bug #1（前端，真实 bug）
`services/api.ts` 401 interceptor 对**所有** 401（含 `/auth/login` 登录失败）执行 `logout()` + `window.location.href='/login'`。
登录失败时用户已在 /login 页 → **整页刷新，错误 toast 被冲掉**（页面"闪一下"无提示）。
**修复**：`url.startsWith('/auth/')` 的 401 交由调用方处理（LoginPage/authStore 展示后端真实消息）；非 auth 端点 401 才触发登出跳转。

### Confirmed Bug #2（前端，语义吞没）
`authStore.login` catch 抛出固定文案「登录失败，请检查手机号和验证码」，后端真实消息（如"手机号或密码错误"）被吞。
**修复**：新增 `utils/apiError.ts` 按 `error.message`（ErrorResponse）→ `detail.message`（HTTPException）提取后端消息透传。

### Confirmed Bug #3（后端，真实 bug，由 #1 的防御测试暴露）
`core/middleware.py::ErrorHandlerMiddleware` 把 `HTTPException` 当普通异常捕获 → 依赖 `get_current_user` 的端点认证失败返回 **500 而非 401**（CI 日志证据：`HTTPException: 401` + `RuntimeError: generator didn't stop after athrow()`）。
此前无测试触发"无 token 访问受保护端点"路径，故从未暴露；该 bug 使前端 401 登出跳转**静默失效**。
**修复**：`except StarletteHTTPException: raise` —— 401/403/404 交回 FastAPI 标准处理，返回 `{detail:{code,message}}`（前端 getErrorMessage 契约）。

### Demo/Production 边界（验证：无 production silently fallback）
- `get_db`（deps.py L43-52）：DEMO 下 DB 不可用 yield None，**有 `settings.DEMO_MODE` 门控**
- `get_current_user`（L130-133）：仅 DEMO 下从 token 重建演示用户
- `effective_ai_provider`（config.py L68-72）：仅 DEMO 强制 mock
- `_demo_scripts.py`：纯数据模块，仅 demo 分支消费
→ 边界明确，production 路径无 demo/mock fallback。

### 测试
- 前端：`utils/apiError` 提取逻辑（可被 login 流程复用）；401 interceptor 行为在组件/工具测试覆盖
- 后端 `test_security_posture.py::TestAuthErrorSemantics`（3 用例）：login 失败 ErrorResponse 格式、无 token detail 契约、refresh 失败格式
- **根因修复验证**：TestCsrfPosture 的 401 用例（此前 500）现全部通过

---

## P2-3 Admin 页面组件测试 —— 状态：**RESOLVED**（+18 用例，未改生产逻辑）

### 现状
Task 23 后仅 `knowledge.test.tsx`（13 用例）；Dashboard/Compliance/Customers 等页面无组件测试。

### 补充（仅测试文件，不重写现有测试，不为了数字改生产逻辑）
| 文件 | 用例数 | 覆盖 |
|------|-------|------|
| `tests/features/dashboard.test.tsx` | 4 | loading 骨架 / error+重试 / 数据渲染（问候语/快捷/统计/AI 建议）/ 空 AI 建议区块不渲染 |
| `tests/features/compliance.test.tsx` | 8 | rules loading/error/empty/list/toggle mutation（toast+防重复）；reviews list/approve mutation/error |
| `tests/features/customers.test.tsx` | 6 | loading / error / empty / list / delete mutation（confirm+toast）/ pagination |

### 过程排障（日志驱动）
- TS2739/TS2345：`complianceApi` 方法返回 `AxiosResponse`（页面 `res.data.data` 解包）→ mock 值需 `{ data: ... }` 包装（helper `axiosRes`）；`mockRule.patterns=[]` 推断 `never[]` → 类型注解
- `CustomerListResult.items` 为 `Customer[]` → `listResult` 参数类型化 + `assigned_to` 字段补齐

---

## P2-4 E2E seed —— 状态：**RESOLVED**（2 个 Confirmed Bug 修复 + 3 用例）

### Confirmed Bug #1（卫生，硬编码凭据）
`scripts/e2e_seed_knowledge.py` 默认 `DB_URL` 硬编码 `postgresql+asyncpg://abz_user:abz_dev_2026@localhost:5432/anzhenbao`（绕过 settings）。
**修复**：`DB_URL = settings.DATABASE_URL`（AZB_DATABASE_URL 统一入口）。

### Confirmed Bug #2（静默污染）
embedding 失败时 `chunk.embedding=None` 照常入库 → pgvector 检索静默丢弃该 chunk（半成品数据）。
**修复**：embedding 失败/数量不符 → `RuntimeError` fail-fast（配合调用方事务回滚，无半成品残留）。

### 幂等强化（Existing Limitation 处理）
KB 已存在即跳过（不校验完整性）→ 增加计数校验：`document_count/total_chunks` 与预期不符打印 WARN（不静默、不自动重建）。

### 其他审计结论（未改动）
- `scripts/seed.py`：roles/permissions/orgs/users 均存在检查（幂等良好）；组织层级依赖列表顺序（父先于子），半删除状态为边缘情况 → Existing Limitation
- backend-pg 共享 PG：各测试自包含（随机 org 名/随机 phone），`test_ingestion_pg._seed_kb` 清理共享 KB 是**有意隔离**；依赖 pytest 收集顺序但当前各测试不依赖共享 KB → Existing Limitation
- E2E：`workers: 1` 串行 + 每次全新 PG 容器 → 无跨运行污染

### 测试（`tests/knowledge/test_e2e_seed_idempotency.py`，纳入 backend-pg workflow）
1. 首次创建 True / 二次跳过 False / 落库单 KB 计数正确（2 docs / 6 chunks）
2. embedding 失败 → RuntimeError 且无半成品残留（新会话验证）
3. 计数不一致 → 跳过 + WARN（数据不破坏）

---

## 发现但未处理（记录，不扩大范围）
| 项 | 说明 | 建议 |
|----|------|------|
| CompliancePage/CustomersPage 顶部"演示模式"Badge 硬编码 | Task 23 已记录未接入项（KnowledgePage 已按 VITE_APP_ENV） | 后续统一为环境变量驱动 |
| `knowledge_repository._apply_visibility` 在 `user_roles/accessible_org_ids` 为 None 时不过滤 | API 层调用方总是传值；防御性可加断言 | 低优先级加固 |
| 前端 refresh token 未接线 | `authService.refreshToken` 存在但 authStore 未调用（access 过期直接登出） | 后续 UX 优化 |
| P1-3 growth course_detail | 任务约束禁止顺手处理 | 维持 Demo Only |
| production-validation.yml 大量 `continue-on-error` | 门禁宽松，失败不阻断 | 后续收紧 |
| `seed.py` 半删除状态边缘 | 组织重建时 parent 可能为 None | 低风险 |

---

## 最终状态矩阵
| 项 | 状态 | 证据 |
|----|------|------|
| P2-1 CSRF | **ACCEPTED LIMITATION（架构无攻击面）+ 防御测试 4 + 文档修正** | test_security_posture.py + security.md |
| P2-2 Demo 401 | **RESOLVED**（3 bug 修复 + 测试 3 + 前端语义修复） | middleware.py / api.ts / authStore.ts / apiError.ts |
| P2-3 组件测试 | **RESOLVED**（+18 用例） | dashboard/compliance/customers.test.tsx |
| P2-4 seed | **RESOLVED**（2 bug 修复 + 3 用例） | e2e_seed_knowledge.py + test_e2e_seed_idempotency.py |
| 无未解释 P2 | — | 上表全覆盖 |
