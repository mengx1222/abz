# Demo Auth Audit（Task 32 — P2-2 Demo 401 一致性 + P2-3 Admin 组件测试覆盖）

> 审计日期：2026-08-19
> 基线 HEAD：`c0bb2b5`（Task 31 完成值）
> 方法：100% Cloud-only —— GitHub API 代码读取 + 既有测试证据。

---

## 1. P2-2 结论：**already resolved（Task 24 已完成，不重复开发）**

### 1.1 当前 Demo mode 与 Production mode 行为差异

| 项 | Demo mode | Production mode |
|---|---|---|
| 认证 | 支持内置演示账号（13800138000-003）+ token 重建演示用户（`get_current_user` fallback） | 仅 DB 用户 + JWT 校验（无 fallback） |
| 401 语义 | 无 token/无效 token → 401（与生产一致） | 无 token/无效 token → 401 |
| DB 降级 | 会话未建立时降级内存数据（Task 24 P2-2 修复后仅限该场景） | 异常重新抛出，无降级 |
| 登录 | `verification_code` 或 `password`（演示码 888888） | 同 API，DB 凭证 |

### 1.2 401/403/404 返回语义（已统一）

- **401**：`get_current_user`（无 token → `UNAUTHORIZED`；无效/过期 token → `INVALID_TOKEN`；refresh token → `INVALID_TOKEN_TYPE`；用户不存在 → `USER_NOT_FOUND`）——统一 `detail={code,message}` 契约
- **403**：`require_role` 越权 → `FORBIDDEN`；`_can_manage_kb` → `FORBIDDEN`；用户禁用 → `USER_DISABLED`
- **404**：资源不存在 → `NOT_FOUND`（不泄露存在性）
- `ErrorHandlerMiddleware` 放行 HTTPException（Task 24 P2-2 修复：此前认证失败 500→401 真实 bug 已修复）

### 1.3 前端 401 识别与 token 失效处理（已正确）

- `api.ts`：401 且非 `/auth/*` 端点 → `store.logout()`（清 localStorage token/user）+ 跳转 `/login`；auth 端点自身 401（登录失败）交由调用方展示错误（Task 24 P2-2 修复）
- `authStore`：`logout()` 清理 `abz_token`/`abz_user` + 状态重置；`restoreSession` 校验 token 存在
- `AuthGuard`：无 token → `<Navigate to="/login">`（未登录访问受保护页面重定向）
- 无 silent fallback 到匿名数据、无错误信息泄露（后端 DEBUG=false 不回显内部细节）

### 1.4 测试证据（已存在）

- `backend/tests/api/test_security_posture.py`：
  - `TestAuthSemantics`：state change 无 Bearer → 401、protected read 无 Bearer → 401、invalid token → 401 INVALID_TOKEN、refresh token → 401 INVALID_TOKEN_TYPE
  - `TestUnauthorizedResponseContract`：登录失败 401 统一 ErrorResponse、missing token detail 契约
- `backend/tests/api/test_auth_api.py` + `backend/tests/unit/test_auth.py`：登录/刷新/登出语义
- `frontend/src/tests/utils/authStore.test.ts`：token 存储/清理
- `frontend/e2e/auth/login.spec.ts`：AGENT 表单登录 → Dashboard
- 前端组件测试：401 处理（api client）已有 authStore 测试覆盖

### 1.5 结论

P2-2（Demo 401 一致性）在 Task 24 已 RESOLVED（代码 + 测试 + E2E 证据齐全）。**不重复开发**，进入 P2-3。

---

## 2. P2-3 审计：Admin Component Test Coverage

### 2.1 现状（Admin 8 页面）

| Admin 页面 | 组件测试 | 状态 |
|---|---|---|
| CommunityManagePage | `communityManage.test.tsx`（6 用例：loading/error/empty/list/pin/delete） | ✅ 已有（Task 25） |
| CompliancePage | `compliance.test.tsx` | ✅ 已有（Task 24） |
| ScriptManagePage | `scriptManage.test.tsx` | ✅ 已有（Task 25） |
| **AnalyticsPage** | **无** | ❌ 缺口 |
| **AuditLogPage** | **无** | ❌ 缺口 |
| **SettingsPage** | **无** | ❌ 缺口 |
| **TrainingManagePage** | **无** | ❌ 缺口 |
| **UsersPage** | **无** | ❌ 缺口 |

### 2.2 缺口补测（Task 32 新增 5 文件 22 用例）

| 文件 | 用例 | 覆盖 |
|---|---|---|
| `analytics.test.tsx` | 4 | loading（正在加载数据）/ error（加载数据失败）/ success（AI 使用情况/培训数据/社区热门帖子/统计卡）/ empty（暂无数据） |
| `auditLog.test.tsx` | 4 | loading（正在加载日志）/ error / empty（暂无审计日志记录）/ list（用户名/描述/资源类型） |
| `settings.test.tsx` | 3 | loading（正在加载设置）/ error / success（AI/RAG/合规/通知/社区设置组标题） |
| `trainingManage.test.tsx` | 6 | loading / error（重新加载）/ empty（未找到匹配的场景）/ list（标题+状态）/ publish mutation（toast）/ delete mutation（confirm→toast） |
| `users.test.tsx` | 5 | loading / error（重新加载）/ empty（未找到匹配的用户）/ list（姓名/手机号/角色）/ disable mutation（toast） |

策略：`vi.mock('../../services/adminService')` 全量 mock（不触真实网络）+ `axiosRes` 包装响应形状（与既有 communityManage/scriptManage 测试模式一致）。

### 2.3 结论

P2-3 Admin 组件测试覆盖从 3/8 页面提升到 **8/8 页面**（22 新增用例）。剩余非 Admin 页面（ProductQa/Scripts/Training/Growth/Notifications/Community 等）由各自模块测试/E2E 覆盖，不在本 P2 范围。
