# CSRF 安全审计（Task 34 — P2-1 复核）

> 审计日期：2026-08-20
> 基线：main@`6be6244`（Task 33 全绿：Vitest 107、Backend 291/44、PG 44、E2E 27、Prod ✅）
> 方法：100% Cloud-only —— GitHub API 读取后端认证/中间件/上传端点与前端 API client 源码，无本地 clone/测试
> 结论：**P2-1 already resolved**（架构无 CSRF 攻击面 + 防御性回归测试已存在）→ 不重复实现，转入下一个未完成安全 P2（上传大小限制）

---

## 1. Current State

### 1.1 认证方式（无 Cookie）
- `app/core/deps.py:94` — `security_scheme = HTTPBearer(auto_error=False)`：全部受保护端点仅接受 `Authorization: Bearer <JWT>`。
- `app/api/v1/auth.py` — `POST /login` 在 **JSON body** 返回 access/refresh token；`POST /refresh` 在 **JSON body** 接收 refresh_token；`POST /logout` 仅作 Bearer 校验后返回成功。
- **全仓库无 `Set-Cookie` / cookie 解析**（对全部 router + audit/health/admin 模块扫描确认）——凭据不落入浏览器 cookie。
- JWT：HS256（`JWT_SECRET_KEY`），access 120min / refresh 7d（`config.py`）。

### 1.2 CSRF 中间件
- **无 CSRF middleware，且无需引入**：CSRF 攻击依赖浏览器对跨站请求**自动附带**凭据（cookie/session）。
  本架构凭据仅在 `Authorization` header —— 跨站 `<form>`/`<img>`/`<script>` 无法自动附带该 header，**攻击面不存在**。

### 1.3 Middleware 链（`app/core/middleware.py:64-80`）
| 中间件 | 状态 |
|--------|------|
| SecurityHeadersMiddleware | ✅ nosniff / X-Frame-Options DENY / X-XSS-Protection 0 / Referrer-Policy / Permissions-Policy / CSP（生产严格，demo 放宽）/ HSTS（仅生产） |
| RateLimitMiddleware | ✅ 内存令牌桶（login 2/s、/ai/ 5/s、默认 30/s） |
| AuditMiddleware | ✅ structlog 审计事件（DB 落库未做 = P1 B2，Task 30 记录） |
| RequestIDMiddleware | ✅ X-Request-ID 注入 |
| RequestLoggingMiddleware | ✅ 结构化请求日志 |
| ErrorHandlerMiddleware | ✅ HTTPException 放行（401/403/404 语义，Task 24 P2-2 修复） |
| CORSMiddleware（main.py） | ✅ 生产 `FRONTEND_URL` 白名单 + credentials；demo 追加 `localhost:5173` + `*`（已记录 ACCEPTED RISK，仅演示环境） |
| TrustedHostMiddleware | ⚠️ **未启用**（纵深防御建议项，不阻塞；部署在反代后由反代校验 Host） |

### 1.4 前端 API Client（`frontend/src/services/api.ts`）
- axios request interceptor：`config.headers.Authorization = Bearer ${token}`（token 存 localStorage `abz_token`）。
- **未启用 `withCredentials`** → 浏览器不发送任何 cookie。
- 全部状态修改（POST/PUT/DELETE）经同一 axios client，凭据仅 header。
- 401 处理：非 `/auth/` 端点 → logout + 跳转 /login；`/auth/` 端点 401 交由调用方（Task 24）。

### 1.5 既有测试（`backend/tests/api/test_security_posture.py`）
- `TestCsrfPosture`（5 用例，Task 24）：登录响应无 Set-Cookie / 受保护写端点（POST logout）无 Bearer → 401 / 受保护读端点无 Bearer → 401 / 无效 token → 401 INVALID_TOKEN / refresh token 类型错误 → 401 INVALID_TOKEN_TYPE。
- `TestAuthErrorSemantics`（3 用例）：login 失败 ErrorResponse 契约 / 无 token detail 契约 / refresh 失败契约。

## 2. Risk

- **CSRF：不适用（无风险）**。无 cookie 会话 + Bearer-only + 前端不启用 withCredentials → 跨站请求无法携带凭据。
- 若未来引入 cookie 会话（如 refresh token 改 HttpOnly Cookie）→ 必须同步引入 CSRF Token 中间件；既有 `TestCsrfPosture` 会立即失败提示重新评估（防御性回归护栏）。
- 次要风险（非 CSRF）：上传端点无大小限制（Task 31 记录 P2）——超大文件被整读入内存并触发解析/嵌入，为 DoS/资源消耗向量。**本任务作为下一个 P2 收敛**。

## 3. Production Impact

- 无（Bearer-only 架构对 CSRF 天然免疫；生产 CORS 白名单已收紧）。
- 上传大小限制为纯增强：拒绝超大文件（413），不影响正常上传、不改变 API 语义。

## 4. Recommended Fix

- **CSRF：无代码变更**。不引入 CSRF token/中间件（与 Bearer 架构冲突，属"为了形式增加无效 CSRF"）。
- **上传大小限制（本任务实施）**：
  1. `config.py` 新增 `MAX_UPLOAD_SIZE_MB`（默认 10MB）；
  2. `knowledge.py::upload_document` 顶部 Content-Length 预检（超限立即 413，不读 body）+ 读取后权威校验（防伪造 Content-Length）；
  3. 413 `{detail:{code:"FILE_TOO_LARGE", message}}`，与既有 401/403/404 语义契约一致；
  4. demo 与 production 分支同享限制。
- **可选（不阻塞，记录）**：启用 TrustedHostMiddleware（部署在反代后由反代校验 Host 时收益有限）。

## 5. 测试计划（Task 34 Phase 3）

| 场景 | 用例 | 位置 |
|------|------|------|
| GET 请求正常（JWT） | GET /auth/me + Bearer → 200 | test_security_posture.py（新增） |
| POST 无 CSRF token（JWT 模式证明） | POST /auth/logout + Bearer → 200 | test_security_posture.py（新增） |
| Demo 模式兼容 | 登录 → token 下发 + 无 Set-Cookie | test_security_posture.py（新增） |
| 安全头不回归 | nosniff / X-Frame-Options DENY / Referrer-Policy | test_security_posture.py（新增） |
| 上传大小限制（demo 分支） | 超限文件 → 413 FILE_TOO_LARGE | test_security_posture.py（新增） |
| 上传大小限制（production 分支，PG） | 超限 413 / 正常 200 | test_kb_crud.py（新增） |
| CORS 不扩大 / Rate Limit 不受影响 | 本任务不改 main.py / rate_limit.py，无回归面 | 代码审计确认 |

## 6. P2 状态记录

- **P2-1（CSRF）：already resolved（复核确认）**——Task 24 已判定 ACCEPTED LIMITATION（架构无攻击面）+ 防御回归测试 5 用例；本任务复核代码确认无 cookie 会话、无 withCredentials、无 CSRF 中间件需求。**不重复实现**。
- **下一个未完成安全 P2：上传无大小限制** → 本任务收敛（见 §4）。
- 复核确认：Task 31 记录 P2「health/detail 无鉴权」为有意开放（compose healthcheck 依赖无鉴权 /health /ready）→ 维持记录不修复；「AuthGuard 无角色守卫」已由 Task 33 复核解决（RoleGuard 接线 AppLayout）。
