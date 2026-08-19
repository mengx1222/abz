# Security Hardening Audit（Task 31 — Production Readiness Hardening）

> 审计日期：2026-08-19
> 基线 HEAD：`05f9e3d`（Task 30 完成值）
> 方法：100% Cloud-only —— GitHub API 代码读取 + 静态审计，无本地运行。
> 原则：先审计发现问题，再最小修复（阶段 3）；P2 仅记录不扩大范围。

---

## 1. API 安全

| # | Current Status | Risk | Severity | Recommendation |
|---|---|---|---|---|
| A1 | 全部业务/管理 endpoint 均带 `Depends(get_current_user)` 或 `Depends(require_role([...]))`（admin 28/28、knowledge 11/11、community 11/11、其余 router 全配；`auth.py` 仅 login/refresh 公开，属正常） | 无未鉴权业务路径 | — | 保持；新增 router 必须显式加依赖 |
| A2 | `GET /api/v1/health/detail` 无鉴权，返回 `app_env`/`demo_mode`/`ai_provider`/masked DB-URL/Redis-URL/middleware stack（URL 密码已 `****` 脱敏） | 内部运行信息轻微泄露（版本/环境/中间件栈；URL 已脱敏无凭据泄露） | **P2** | 建议加 `Depends(get_current_user)` 或限制内部网段访问；长期可移除或仅 DEBUG 启用 |
| A3 | 生产模式（DEMO_MODE=false）`_create_provider` 无凭据时抛错，**绝不静默降级 Mock**（gateway.py） | 无 Mock 冒充真实 AI | — | 保持（Task 27/30 已验证） |
| A4 | `ErrorHandlerMiddleware` 放行 HTTPException（401/403/404 标准语义）；未捕获异常返回 500 且 DEBUG 关闭时**不**回显内部错误（`settings.DEBUG` 控制） | 生产不泄露堆栈/内部错误细节 | — | 保持 |
| A5 | Demo 模式 `get_db` 在「会话未建立」时降级内存（Task 24 P2-2 修复）；生产模式异常重新抛出 | Demo 与 production 行为已分离 | — | 保持 |

## 2. 权限安全

| # | Current Status | Risk | Severity | Recommendation |
|---|---|---|---|---|
| B1 | **`POST /admin/knowledge-bases/{kb_id}/documents/upload`（upload_document）生产分支查询 KB 后未校验 `_can_manage_kb`** —— 其他写端点（update/delete/publish/unpublish/delete_document）均有校验，唯独 upload 缺失 | **任何登录用户可向任意知识库上传文档**（污染知识库、绕过 KB 权限边界、数据完整性破坏） | **P1（必修）** | 生产分支加 `if not _can_manage_kb(current_user, kb_row): raise 403 FORBIDDEN`；Demo 分支（内存演示）风险低保持 |
| B2 | RBAC `require_role` 覆盖 admin 28 端点；越权返回统一 `403 FORBIDDEN` | 无角色绕过 | — | 保持 |
| B3 | 客户 IDOR：跨组织客户 → `NOT_FOUND`（不泄露存在性）；RAG 权限 SQL WHERE 层过滤（Task 17B）；越权 KB citation 不泄漏（test_agent_pg） | 资源枚举/越权已封堵 | — | 保持 |
| B4 | 404/403 语义：客户/文档/KB 不存在 → 404 NOT_FOUND；权限不足 → 403 FORBIDDEN（`get_current_user`/`require_role`/`_can_manage_kb` 统一 detail 结构） | 语义一致 | — | 保持 |

## 3. 数据安全

| # | Current Status | Risk | Severity | Recommendation |
|---|---|---|---|---|
| C1 | 仓库无真实 Secret：`.env.example`/`backend/.env.production` 均为 CHANGE_ME 模板；CI 经 GitHub Secrets 注入 | Secret 不入库 | — | 保持 |
| C2 | 日志扫描：logger 不打 `DATABASE_URL`/`API_KEY`/`SECRET` 字段；gateway 日志仅 provider/model/token count/latency；health 检查 error 仅 `str(exc)` | Secret 不进日志 | — | 保持 |
| C3 | 用户输入（message/RAG 查询）会进入 LLM prompt，但 `sanitize_user_input`（safety.py）先做 Prompt Injection 检测（HIGH → 拒答）；Agent 黄金链 RAG REFUSE 不编造 | 注入风险已缓解 | — | 保持 |
| C4 | SQL：repositories 全部使用 SQLAlchemy ORM/参数绑定，无 f-string 拼接 execute（已扫描） | 无 SQL 注入面 | — | 保持 |
| C5 | 文件上传：`upload_document` 不写磁盘（内容直接解析入库，无路径保存）→ 无路径遍历；**但无文件大小上限**（`await file.read()` 全量读内存） | 超大文件内存 DoS | **P2** | 加文件大小限制（如 5MB）+ 格式白名单校验 |
| C6 | 前端 token 存 `localStorage`（abz_token） | XSS 可窃取 token（CSP `script-src 'self'` 缓解） | **P2** | 正式生产评估 HttpOnly cookie 方案或强化 CSP/子资源完整性 |

## 4. 前端安全

| # | Current Status | Risk | Severity | Recommendation |
|---|---|---|---|---|
| D1 | API client（api.ts）：axios timeout 15s；401 非 auth 端点 → logout + 跳登录（Task 24 P2-2）；请求拦截附加 Bearer | token 处理正确 | — | 保持 |
| D2 | 前端 error 展示沿用后端 `detail.message`（业务错误文案，非内部堆栈）；`DEBUG=false` 时后端 500 不回显内部细节 | 无内部信息泄露 | — | 保持 |
| D3 | Sidebar adminNav 按角色过滤（SYSTEM_ADMIN/HQ_ADMIN/COMPLIANCE）；**AuthGuard 仅检查登录态，无角色级路由守卫**（AGENT 手输 /admin/* URL 可进页面，API 403 兜底显示错误） | 前端 UX 级：角色不可见但后端已 403 兜底 | **P2** | 加路由级角色守卫（或保持后端兜底并记录） |
| D4 | **无 React ErrorBoundary**：页面组件运行时崩溃 → 白屏无兜底 | 白屏/无错误提示 | **P2** | 加全局 ErrorBoundary + 友好错误页 |
| D5 | 无独立 production/demo 标识组件（页面不展示环境 badge） | 演示环境可能被误认为生产 | **P2** | 加环境 badge（生产隐藏，非生产显示） |

## 5. 可靠性审计

### Backend
| 项 | 状态 | 说明 |
|---|---|---|
| Exception handling | PASS | ErrorHandlerMiddleware 统一 500（DEBUG 控制详情）；HTTPException 放行标准语义 |
| Async session 生命周期 | PASS | `get_db` 生产模式 `async with` + finally close；pool_pre_ping + pool_size=10/max_overflow=20 |
| Background task | PASS | 无 `asyncio.create_task`/`BackgroundTasks` 吞异常点（已扫描） |
| AI provider fallback | PASS | 生产无凭据抛错；Provider 失败 Agent 不 fallback Mock（Task 27 测试）；错误不落业务数据 |
| Redis/PG failure | PARTIAL(P2) | PG 生产失败抛错（正确）；**Redis 连接失败 → no-op 客户端静默降级**（业务当前低依赖 Redis，可接受；多实例需 Redis 化限流/session 时需 fail-fast） |

### Frontend
| 项 | 状态 | 说明 |
|---|---|---|
| API timeout | PASS | axios timeout 15000ms |
| Loading 状态 | PASS | 主要页面有 loading（组件测试覆盖） |
| Error boundary | **P2** | 无全局 ErrorBoundary（见 D4） |
| 重复提交保护 | PASS | Sales Agent `isStreaming` 防重复 + 中止；主要 mutation 页面有 disable 态（既有组件测试覆盖） |

### CI
| 项 | 状态 | 说明 |
|---|---|---|
| 测试绕过 | PASS | 无 skip 大块测试/`if: false`；backend/backend-pg/frontend/e2e 均真实执行 |
| Workflow 失效步骤 | PARTIAL | production-validation 多个步骤 `continue-on-error: true`（展示型，最终结论看 step 结果；Task 30 已复核 Prod ✅） |
| Secrets 使用 | PASS | GitHub Secrets 注入 AZB_AI_* / E2E_*；无明文入库 |

---

## 6. 结论摘要

- **P0：无**
- **P1：1 项 —— B1 upload_document 越权上传（KB 写权限缺失）→ 阶段 3 修复**
- **P2：7 项（仅记录，不扩大范围）**：
  1. A2 health/detail 无鉴权（信息泄露轻，URL 已脱敏）
  2. C5 文件上传无大小限制
  3. C6 token localStorage（XSS 面，CSP 缓解）
  4. D3 AuthGuard 无角色路由守卫（后端 403 兜底）
  5. D4 无 React ErrorBoundary
  6. D5 无环境 badge
  7. Redis no-op 静默降级（多实例前需 fail-fast 决策）
- 其余审计项全部 PASS（鉴权全覆盖/RBAC/IDOR/CSRF/CORS/Headers/RateLimit/Secrets/日志/SQL/上传路径/AI fallback/session/CI）
