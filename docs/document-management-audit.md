# Document Management Production 化审计（Task 22）

> 审计时间：2026-08-18 · 基线：`4a73564`（Task 21 完成后）
> 范围：Knowledge Base 下 Document 管理生命周期（list / detail / publish / unpublish / delete）从 Demo/半生产迁移到 Production Database。
> 原则：不修改 RAG 算法、不重新设计权限模型（沿用 Task 17B/21）、不扩大范围。

---

## 1. 审计结论（段1）

| 接口 | 现状（审计前） | DB 读写 |
|------|---------------|---------|
| `GET /kb/{kb_id}/documents`（list） | `_ensure_demo_data()` + `_demo_documents` 内存过滤 | ❌ 无 |
| `POST /kb/{kb_id}/documents/upload`（upload） | ✅ **Task 20 已生产化**（解析→分块→embedding→PG+pgvector） | ✅ |
| `GET /kb/{kb_id}/documents/{doc_id}`（detail） | **接口不存在** | — |
| `POST /kb/{kb_id}/documents/{doc_id}/publish`（publish） | 内存 dict 改 `status=published` | ❌ 无 |
| `POST /kb/{kb_id}/documents/{doc_id}/unpublish`（unpublish） | **接口不存在** | — |
| `DELETE /kb/{kb_id}/documents/{doc_id}`（delete） | 内存列表过滤 | ❌ 无 |

### Demo fallback 依赖

- `_demo_documents: list[dict]` —— `get_demo_documents()` 硬编码文档
- `_ensure_demo_data()` —— 每次操作前置初始化

### 相关缺口

- **无 document repository**（`backend/app/repositories/` 无 document_repo）。
- **detail / unpublish 接口缺失** → 生产文档管理链路不完整。
- **delete 无级联语义保障**（内存列表删除；DB 层依赖 FK CASCADE，但从未走到）。

---

## 2. 实现方案（段2/段3）

### Repository 层（新建 `backend/app/repositories/document_repository.py`）

SQLAlchemy async，全部 DB 访问集中管理，API 层不直接操作 ORM：

- `create_document(...)` → DB insert（status/created_by/published_at）
- `get_document(doc_id, kb_id, user_roles, accessible_org_ids)` → DB query，**JOIN KnowledgeBase 可见性过滤**
- `list_documents(kb_id, status, user_roles, accessible_org_ids, page, page_size)` → DB query + 过滤 + 计数
- `update_document_status(doc_id, status, ...)` → DB update（publish/unpublish 共用）
- `publish_document(doc_id, published_by)` → `status=published` + `published_at=now`
- `unpublish_document(doc_id)` → `status=draft`
- `delete_document(doc_id)` → **物理删除**，FK `ondelete=CASCADE` 级联删 `document_chunks`（embedding 随 chunk 行删除，无孤儿数据）

**可见性过滤（`_visibility_join`）** —— Document 继承所属 KB 的权限，与 Task 17B/21 完全一致：
- 角色：`KB.allowed_roles IS NULL OR KB.allowed_roles ? role`
- 组织：`KB.organization_id IS NULL（共享） OR IN (accessible_org_ids)`；SYSTEM_ADMIN `__ALL__` 跳过

### API 层（`backend/app/api/v1/knowledge.py`）

- list / publish / delete：加 `db` 依赖 + production 分支（repository）；`DEMO_MODE=true` 保留内存行为
- **新增** `GET /kb/{kb_id}/documents/{doc_id}`（detail）：DB 查询 + 可见性过滤（越权/不存在 404）
- **新增** `POST /kb/{kb_id}/documents/{doc_id}/unpublish`：`status=draft`
- 写操作（publish/unpublish/delete）权限：**管理角色（SYSTEM_ADMIN/HQ_ADMIN/BRANCH_ADMIN/TEAM_LEADER）或创建者本人**（`_can_manage_kb` 复用，越权 403）
- delete 后同步回退 KB `document_count` / `total_chunks` 计数
- 响应结构 `_doc_to_dict` 与 Demo 一致；既有 API path / response schema 不变（新增路由向后兼容）

---

## 3. 权限验证（段4）

- **organization**：AGENT@A 可查看组织 A KB 的文档；AGENT@B list 不含 + detail 404（API 集成测试）
- **role**：KB `allowed_roles=["AGENT"]` 的文档，AGENT 可见、HQ_ADMIN 不可见（精确角色匹配，Task 17B §2.3.3 硬约束）
- **delete**：仅管理角色或创建者（AGENT 非创建者 → 403）

---

## 4. 数据库与迁移（段5）

- `Document.knowledge_base_id` → FK `knowledge_bases.id ON DELETE CASCADE` ✓（既有）
- `DocumentChunk.document_id` → FK `documents.id ON DELETE CASCADE` ✓（既有）
- `DocumentChunk.embedding`（Vector 1536）随 chunk 行一并删除 ✓
- **无需新增迁移**（Task 20/21 已含所需表结构与列）

---

## 5. 测试（段6）

`backend/tests/knowledge/test_document_management.py`（@integration，CI backend-pg 纳入）：

| # | 用例 | 断言 |
|---|------|------|
| 1 | document list success | 列表命中 + status 过滤 |
| 2 | document detail | 字段正确（title/file_type/status/kb_id） |
| 3 | organization isolation | AGENT@A 可见 / AGENT@B list 不含 + detail 404（API） |
| 4 | role isolation | AGENT 可见 / HQ_ADMIN 不可见 + get None（repo） |
| 5 | publish status change | publish → published+published_at+published_by；unpublish → draft |
| 6 | delete cascade | 删 doc → document_chunks（含 embedding）清零，无孤儿 |
| 7 | unauthorized delete | 非管理/非创建者 403；创建者 200（API） |

---

## 6. 修改文件

- `backend/app/repositories/document_repository.py`（新建）
- `backend/app/api/v1/knowledge.py`（list/publish/delete 生产化 + 新增 detail/unpublish）
- `backend/tests/knowledge/test_document_management.py`（新建）
- `.github/workflows/backend-tests.yml`（backend-pg 纳入 test_document_management）
- `docs/document-management-audit.md`（本文件）

---

## 7. 边界声明

- 已实现/已验证：Document list/detail/publish/unpublish/delete 生产化（DB backed）+ 权限继承（org/role）+ 级联删除无孤儿 + 未授权写操作 403，PG 集成测试固化。
- 未处理（不扩大范围）：AI Sales Agent、RAG 算法、权限模型、知识库 CRUD（Task 21 已闭环）、文档内容解析/分块逻辑（Task 20 已闭环）。
- Demo 模式行为完全保留。
