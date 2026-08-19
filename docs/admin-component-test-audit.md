# Admin 组件测试覆盖审计（Task 33 — P2-3 复核）

> 审计日期：2026-08-20
> 基线：main@`f670f99`（Task 32 全绿：Vitest 103/103、Backend 291/44、backend-pg 44、E2E 27、Prod ✅）
> 方法：100% Cloud-only —— GitHub API 读取 `frontend/src/features/admin` 与 `frontend/src/tests` 全部文件，无本地 clone/测试
> 范围：Admin 前端页面 Vitest 组件测试覆盖（P2-3）复核；只读审计，不改代码

---

## 1. 当前覆盖情况（结论：8/8 全覆盖，P2-3 已完成）

`frontend/src/features/admin/` 共 **8 个页面**，全部已有对应组件测试：

| # | Admin 页面 | 测试文件 | 用例数 | 覆盖维度 |
|---|-----------|----------|-------|----------|
| 1 | AnalyticsPage（数据看板） | `tests/features/analytics.test.tsx` | 4 | loading / error / success 渲染 / empty（null 数据不崩溃） |
| 2 | AuditLogPage（审计日志） | `tests/features/auditLog.test.tsx` | 4 | loading / error / 列表渲染 / 筛选（含「创建客户」多元素 getAllByText） |
| 3 | CommunityManagePage（社区管理） | `tests/features/communityManage.test.tsx` | 7 | loading / error+重试 / empty / 列表 / pin mutation / delete mutation（confirm+toast） |
| 4 | CompliancePage（合规中心） | `tests/features/compliance.test.tsx` | 8 | rules loading/error/empty/list/toggle mutation；reviews list/approve mutation/error |
| 5 | ScriptManagePage（话术管理） | `tests/features/scriptManage.test.tsx` | 6 | loading / error / empty / 列表 / approve mutation / reject mutation |
| 6 | SettingsPage（系统设置） | `tests/features/settings.test.tsx` | 3 | loading / 渲染 / update mutation |
| 7 | TrainingManagePage（训练管理） | `tests/features/trainingManage.test.tsx` | 6 | loading / 列表 / publish mutation（draft-only 按钮）/ delete mutation / error |
| 8 | UsersPage（用户管理） | `tests/features/users.test.tsx` | 5 | loading / error+重试 / empty / 列表 / disable mutation（confirm+toast） |

**合计：8/8 页面，43 用例**（与全量 Vitest 103 passed / 15 files 一致，Task 32 已收敛）。

## 2. 测试模式一致性审计

| 维度 | 状态 | 说明 |
|------|------|------|
| service mock | ✅ 统一 | 全部 `vi.mock('../../services/adminService')`；返回 AxiosResponse 形状统一 `axiosRes(data)` helper（`{ data: ... }` 包装，匹配页面 `res.data.data` 解包） |
| auth mock | ✅ 无需 | Admin 页面测试直接 render 页面组件（不经过 AuthGuard/RoleGuard），无 auth 依赖；auth 行为由 `authStore.test.ts` + E2E login 覆盖 |
| error handling | ✅ 覆盖 | 每页均有 `mockRejectedValue` 用例断言错误 UI + 「重新加载」恢复按钮 |
| loading 状态 | ✅ 覆盖 | 每页均有 pending promise 用例断言 loading 文案 |
| empty state | ✅ 覆盖 | 每页均有空数据用例（`data: []` 或 `data: null`） |
| permission denied | ⚠️ 部分 | 仅 `knowledge.test.tsx`（非 admin）显式覆盖 403（KB list 403、delete document 403，断言后端 message 透传 toast）。Admin 页面测试无显式 403 用例 —— 但 Admin 页面将 403 与通用错误走同一 `getErrorMessage → toast` 渲染路径，错误用例已覆盖该渲染路径 → **低优先级补充项，本次不新增** |

## 3. 缺失页面 / 缺口清单

- **Admin 域：无缺失**（8/8 全覆盖）。
- **非 Admin 页面（单测缺口，均有 E2E 覆盖，低优先级）**：
  - `features/notifications/NotificationsPage` — 无单测（无对应 E2E spec，**唯一无任何测试覆盖页面**）
  - `features/growth/GrowthPage` — 无单测（E2E `growth.spec.ts` 覆盖）
  - `features/training/TrainingPage` / `TrainingChatPage` — 无单测（E2E `training.spec.ts` 覆盖）
  - `features/community/CommunityPage` — 无单测（E2E `admin-community.spec.ts` 覆盖）
  - `features/product-qa/ProductQaPage` — 无单测（E2E `product-qa.spec.ts` 覆盖）
  - `features/customers/CustomerDetailPage` — 无单测（E2E `customer-detail.spec.ts` 覆盖）
  - `features/scripts/ScriptsPage` — 无单测（E2E `script-generation.spec.ts` 覆盖）
  - `features/auth/LoginPage` — 无单测（E2E `login.spec.ts` + authStore.test.ts 覆盖）
  - `features/sales-agent/SalesAgentPage` — ✅ 有单测（11 用例）+ E2E 2 用例

## 4. 测试优先级（若继续补测）

| 优先级 | 页面 | 理由 |
|--------|------|------|
| P1 | NotificationsPage | **唯一零测试页面**（无单测无 E2E） |
| P2 | GrowthPage / TrainingPage | 高频业务页面，E2E 已覆盖主链，单测补分支 |
| P3 | ProductQa / Scripts / Community / CustomerDetail / Login | E2E 覆盖充分，单测边际价值低 |

## 5. 不纳入范围说明

1. **P2-3 判定为已完成，不重复开发**：8/8 Admin 页面已覆盖 loading/error/empty/list/mutation，模式统一。本任务不新增 Admin 测试。
2. **不补 Admin 403 显式用例**：403 与通用错误走同一渲染路径，现有 error 用例已覆盖；显式 403 用例边际价值低（记录，后续可选）。
3. **不补 RoleGuard 组件级测试**（`components/layout/RoleGuard.tsx`）：复核发现 Task 31 记录的 P2「AuthGuard 无角色路由守卫」**已解决** —— RoleGuard 已在 `AppLayout.tsx` L20-22 接线（`<RoleGuard><Outlet/></RoleGuard>`），`config/roleRoutes.ts` + `tests/utils/roleRoutes.test.ts`（13 用例）覆盖访问规则；仅缺 RoleGuard 组件级渲染测试，属低优先级，本次不新增。
4. **不开发 AI Sales Agent、不增加业务功能**：本审计只读，后续实施仅限 P2 技术债收敛。

## 6. 结论与后续动作

- **P2-3：RESOLVED（复核确认，无需开发）**。
- 按 Task 33 指令，转入**下一个最高优先级未完成 P2**：**前端全局 ErrorBoundary（Task 31 记录「无 ErrorBoundary」）** —— 当前仓库无任何 ErrorBoundary 组件（仅 `utils/apiError.ts`），任意页面渲染错误将导致整页白屏且无恢复路径；补齐后任意子树崩溃可降级为可恢复 fallback，直接提升 Production Confidence。详见本任务 Commit 2/3。
