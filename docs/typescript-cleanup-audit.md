# TypeScript Cleanup Audit — Task 19

> 基线：`main @ c9ec80c`（Task 18 后）→ 修复完成 `acebb0e`（tsc -b = 0 errors）
> 日期：2026-08-18

## 1. 基线错误统计（云端 `npx tsc -b`，Frontend Typecheck workflow 首跑）

**总错误数：32**

| 错误码 | 数量 | 含义 |
|--------|------|------|
| TS6133 | 22 | 声明但从未使用的变量/导入 |
| TS2322 | 5 | 类型不匹配（Badge variant、lazyNamed 泛型） |
| TS2367 | 2 | 与已窄化类型无重叠的比较（冗余条件） |
| TS2339 | 1 | 属性不存在（PostListItem.content） |
| TS2353 | 1 | 对象字面量多余属性（favorites_count） |
| TS2551 | 1 | 属性不存在/拼写（favorites_count → views_count） |

## 2. 涉及文件（14 个）

| 文件 | 错误数 | 优先级 |
|------|--------|--------|
| `features/training/TrainingChatPage.tsx` | 6 | P1（含 1 个 TS1128 语法错误） |
| `features/admin/ScriptManagePage.tsx` | 5 | P1 |
| `features/community/CommunityPage.tsx` | 5 | P1（含公共类型根因） |
| `features/admin/AuditLogPage.tsx` | 3 | P2 |
| `features/knowledge/KnowledgePage.tsx` | 4 | P2（3 处 Badge danger 公共根因） |
| `features/admin/CompliancePage.tsx` | 1 | P2 |
| `features/admin/CommunityManagePage.tsx` | 1 | P2 |
| `features/admin/TrainingManagePage.tsx` | 1 | P2 |
| `features/training/TrainingPage.tsx` | 2 | P2 |
| `features/scripts/ScriptsPage.tsx` | 1 | P2 |
| `features/growth/GrowthPage.tsx` | 1 | P2 |
| `app/routes.tsx` | 1 | P1（公共类型） |
| `components/ui/Badge.tsx` | 0（修复点） | P0 公共组件根因 |
| `services/communityService.ts` | 0（修复点） | P0 公共契约根因 |

## 3. 公共类型问题（根因优先）

1. **Badge.variant 缺 `primary/info/danger`** → 4 处 TS2322（CommunityPage:243、KnowledgePage:200/254/377）。修复：Badge 公共组件补 3 个 variant + 样式（1 处修复 4 错误）。
2. **PostDetail 缺 `favorites_count`** → TS2353/TS2551（CommunityPage:168/302）。后端 `FavoriteToggleResponse` 返回该字段；`PostDetail` 详情接口不返回 → 前端补 `favorites_count?: number`（可选，渲染 fallback 0）。
3. **PostListItem 无 `content`**（仅 `summary`）→ TS2339（CommunityPage:78）。修复：列表卡用 `summary`，移除对 `content` 的访问。
4. **lazyNamed 泛型推断退化为 `{}`** → TS2322（routes.tsx:21）。React 19 `React.lazy` 需显式泛型：`React.lazy<ComponentType>(...)`。

## 4. Feature-level 问题

- **TS6133×22**：删除全部未使用导入/变量/常量（含 TrainingChatPage 的 DIFFICULTY_CONFIG 常量、abortRef、difficulty 等）。
- **TS2367×2**（ScriptManagePage:229）：`status === 'approved' && status !== 'pending' && status !== 'rejected'` 在窄化后无重叠 → 删除冗余比较（行为不变）。
- **排障记录**：
  - DIFFICULTY_CONFIG 删除残留孤立 `};` → TS1128 语法错误（vite build 失败），已清理。
  - CompliancePage 三个组件各有 `useToast()` 作用域：Page 的 toast 未使用（保留 `useToast();`），RulesTab/ReviewsTab 的 toast 被使用（保留解构）——首次批量替换误伤，已恢复。
  - KnowledgePage 删除 `user` 变量后 `useAuthStore` import 变为未使用 → 删除 import。

## 5. 修复结果

- **`npx tsc -b`：32 → 0 errors**（云端 Frontend Typecheck workflow @ `acebb0e` success）
- CI Hard Gate 恢复：`backend-tests.yml` frontend job 增加显式 `TypeScript typecheck (tsc -b)` 步骤 + Build 恢复 `npm run build`（tsc -b && vite build）
- 独立 `frontend-typecheck.yml` workflow 保留（frontend/** 变更快速验证）

## 6. 变更文件清单（Task 19）

- 类型修复（4 commits）：`9e29aab`、`c03dc2e`、`cfdfbab`、`25aa3a0`、`acebb0e`（含 2 个排障修复 commit）
- CI：`backend-tests.yml`（Hard Gate 恢复）、`e2e-playwright.yml`（paths 增加 frontend/src/**，src 变更触发 E2E）、`frontend-typecheck.yml`（新增）
- 前端：13 个 tsx/ts 文件类型修复（见 §2）
- 文档：本文件、project-status、release-verification、release-readiness、testing、worklog
