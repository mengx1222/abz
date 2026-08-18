# Admin Frontend Production 化审计（Task 23）

> 审计时间：2026-08-19 · 基线：`fb297f0`（Task 22 完成后）
> 范围：Knowledge Base / Document Admin 前端从 Demo/Mock 感知切换到真实 Production API 对接。
> 原则：最小生产化改造；不开发新后端能力、不重构 UI、不改变既有 API contract。

---

## 1. 现状 → 目标（阶段④ 改造清单）

### 1.1 前端现状

| 层 | 现状 | Production-ready? |
|----|------|-------------------|
| `services/knowledgeService.ts` | 已对接 KB list/create/get/update/delete + Document list/upload/publish/delete（真实 API client `api.ts`） | ✅ 基本 |
| `features/knowledge/KnowledgePage.tsx` | 通过 service 调真实 API（无 mock fallback）；KB 列表/创建/删除、文档列表/上传/发布/删除 UI 齐全 | ⚠️ 缺 detail/unpublish/update |
| `services/api.ts` | axios 拦截器：JWT 注入 + 401 → logout | ✅ |
| 错误语义 | 所有 catch 统一 toast「XX失败」，**不展示后端 404/403 detail.message** | ❌ 需修 |
| mutation 状态 | create/upload 有 loading；**publish/delete 无 loading/防重复** | ❌ 需补 |
| 「演示模式」Badge | 硬编码 `<Badge variant="warning">演示模式</Badge>`（production 也显示） | ❌ 需按环境 |
| 前端测试 | 仅 3 个 utils 测试（authStore/cn/roleRoutes） | ❌ 无页面测试 |
| E2E | auth/customers/dashboard/growth/product-qa/scripts/training | ❌ 无 knowledge |

### 1.2 后端真实 API contract（Task 21/22 已实现，核对确认）

```
GET    /api/v1/admin/knowledge-bases                  → list（角色+组织过滤）
POST   /api/v1/admin/knowledge-bases                  → create（org/roles/metadata；同名 409）
GET    /api/v1/admin/knowledge-bases/{kb_id}          → detail（越权/不存在 404）
PUT    /api/v1/admin/knowledge-bases/{kb_id}          → update（管理角色或创建者，越权 403；同名 409）
DELETE /api/v1/admin/knowledge-bases/{kb_id}          → delete（级联；越权 403）
GET    /api/v1/admin/knowledge-bases/{kb_id}/documents                → list（JOIN KB 过滤）
GET    /api/v1/admin/knowledge-bases/{kb_id}/documents/{doc_id}       → detail（越权/不存在 404）
POST   /api/v1/admin/knowledge-bases/{kb_id}/documents/upload         → upload（Task 20）
POST   /api/v1/admin/knowledge-bases/{kb_id}/documents/{doc_id}/publish    → publish（403 无权限）
POST   /api/v1/admin/knowledge-bases/{kb_id}/documents/{doc_id}/unpublish  → unpublish（403 无权限）
DELETE /api/v1/admin/knowledge-bases/{kb_id}/documents/{doc_id}       → delete（403 无权限）
```

错误结构（FastAPI）：`{ "detail": { "code": "...", "message": "..." } }`；
404 = 资源不可见/不存在（**不泄露存在性**）；403 = 可见但无写权限。

KB 响应：`id/name/description/category/status/document_count/total_chunks/is_public/allowed_roles/version/metadata/created_at/updated_at`（Task 21 `_kb_to_dict`）
Document 响应：`id/knowledge_base_id/title/file_name/file_type/file_size/status/chunk_count/parse_error/published_at/created_at/updated_at`（Task 22 `_doc_to_dict`）
**注意：detail 响应不含 `content_text`（后端未暴露）→ 前端详情面板展示元信息，正文展示记录为未接入项。**

### 1.3 改造清单（Target）

| # | 改动 | 文件 |
|---|------|------|
| 1 | service 补 `getKnowledgeDocument`（detail）、`unpublishDocument`；`KnowledgeDocument` 补 `parse_error`；导出 `getErrorMessage`（axios → detail.message） | `services/knowledgeService.ts` |
| 2 | 页面补 Document detail 视图（点击文档 → 详情面板，元信息展示） | `KnowledgePage.tsx` |
| 3 | 页面补 unpublish（published → 取消发布）与 KB edit（update 复用创建表单） | `KnowledgePage.tsx` |
| 4 | 404/403 语义：错误 toast 展示后端 `detail.message`（如「文档不存在」「无权限修改该知识库」），不展示「系统异常」 | `KnowledgePage.tsx` |
| 5 | mutation loading/防重复：publish/unpublish/delete/update 均有 loading + disabled | `KnowledgePage.tsx` |
| 6 | 「演示模式」Badge 按 `VITE_APP_ENV==='demo'` 显示（production 不显示） | `KnowledgePage.tsx` |
| 7 | 前端组件测试：KB list/Document list/detail/publish/unpublish/delete/error/404/403/loading/empty | `tests/features/knowledge.test.tsx` |
| 8 | E2E：knowledge admin 最小覆盖（KB 列表 → 文档列表） | `e2e/knowledge/knowledge.spec.ts` |
| 9 | 文档同步 | 见 §4 |

---

## 2. 权限语义（阶段⑦）

- 组织外/角色不符资源 → 后端 404 → 前端 toast 展示后端 message（「知识库不存在」/「文档不存在」），**不得展示为「系统异常」**，也不得暗示资源存在。
- 可见但无写权限 → 后端 403 → toast 展示「无权限…」。
- `api.ts` 的 401 → logout 行为保留（不改）。

## 3. Demo/Production 边界（阶段⑨）

- 前端 service 层**无任何 mock fallback**：页面始终请求真实 API；Production mode 下后端 DB-backed（Task 21/22），Demo mode 下后端内存数据（Task 21/22 兼容）。
- 修复「演示模式」Badge 硬编码：仅 `VITE_APP_ENV==='demo'` 时显示。

## 4. 未接入项（仅记录，不扩范围）

- Document detail 响应不含 `content_text`（后端 contract 如此）→ 前端详情面板只展示元信息。
- KB/Document 分页（后端 list 有 page/page_size，前端页面未用分页 UI）。
- KnowledgeBase `allowed_roles` / `organization_id` 创建参数（前端创建表单未暴露，缺省=当前用户组织，合理默认）。

---

## 5. 验证矩阵（阶段⑫）

TypeScript `tsc -b` 0 errors · Vitest 全绿 · Vite build · Backend pytest · backend-pg · Production Validation · Playwright E2E —— 全部 GitHub Actions。
