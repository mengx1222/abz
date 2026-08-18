# Knowledge Base CRUD Production 化审计（Task 21）

> 审计时间：2026-08-18 · 基线：`e44a139`（Task 20 完成后）
> 范围：Knowledge Base 管理链路（list / create / detail / update / delete）从 Demo/In-memory 迁移到 Production Database。
> 原则：不开发新 AI 功能、不修改 RAG 核心算法、不重新设计权限模型（沿用 Task 17B）。

---

## 1. 审计结论（段1）

**五个 CRUD 接口在 Production 模式下全部仍依赖 Demo 内存数据，无任何数据库读写。**

| 接口 | 现状（审计前） | DB 读写 |
|------|---------------|---------|
| `GET /knowledge-bases`（list） | `_ensure_demo_data()` + `_demo_knowledge_bases` 内存过滤 | ❌ 无 |
| `POST /knowledge-bases`（create） | 写入 `_demo_knowledge_bases`（id=`demo-kb-*`） | ❌ 无 |
| `GET /knowledge-bases/{kb_id}`（detail） | 内存 `next(...)` 查找 | ❌ 无 |
| `PUT /knowledge-bases/{kb_id}`（update） | 内存 dict 原地修改，version+1 | ❌ 无 |
| `DELETE /knowledge-bases/{kb_id}`（delete） | 内存列表过滤删除 | ❌ 无 |

### Demo fallback 依赖清单

- `_demo_knowledge_bases: list[dict]` —— 三个硬编码知识库（产品/话术/合规），含 `allowed_roles`、`organization_id`（Task 17B 语义，`_demo_org_hq`）
- `_demo_documents: list[dict]` —— `get_demo_documents()` 硬编码文档
- `_ensure_demo_data()` —— 每次 CRUD 前置初始化（内存 + `init_demo_index()`）

### 相关缺口

- **无 knowledge repository**：`backend/app/repositories/` 有 9 个 repo（community/customer/dashboard/growth/notification/script/training/user），无 knowledge。
- **无 knowledge schemas**：`backend/app/schemas/knowledge.py` 不存在（请求体定义在 `api/v1/knowledge.py` 内）。
- **KnowledgeBase 模型无 `metadata` 列**：Task 21 要求创建时支持 metadata → 新增列 + alembic 0009。
- upload_document（Task 20 已生产化）在 production 下查询 KB 已走 DB（`sa_select(KnowledgeBase)`），但 list/create/update/delete 未同步 → KB 无法通过 API 在生产环境创建，上传链路实际上依赖 seed/手动插入的 KB。

---

## 2. 实现方案（段2/段3/段4）

### Repository 层（新建 `backend/app/repositories/knowledge_repository.py`）

SQLAlchemy async，全部 DB 访问集中在仓储层，API 层不直接操作 ORM：

- `create_knowledge_base(name, description, category, is_public, organization_id, allowed_roles, metadata_, created_by, status)` → DB insert
- `get_knowledge_base(kb_id, user_roles, accessible_org_ids)` → DB query + 可见性过滤
- `list_knowledge_bases(category, status, user_roles, accessible_org_ids, page, page_size)` → DB query + 过滤 + 计数
- `update_knowledge_base(kb_id, ...)` → DB update，`version+1`
- `delete_knowledge_base(kb_id)` → **物理删除**，FK `ondelete=CASCADE` 级联删 documents/document_chunks
- `name_exists(name, organization_id, exclude_id)` → 同名冲突检查
- `_apply_visibility(stmt, user_roles, accessible_org_ids)` → Task 17B 可见性语义：
  - 角色：`allowed_roles IS NULL OR allowed_roles ? role`（JSONB has_key）
  - 组织：`organization_id IS NULL（共享） OR organization_id IN (accessible_org_ids)`

### API 层（`backend/app/api/v1/knowledge.py`）

- 五个接口均增加 `db: AsyncSession = Depends(get_db)`；`DEMO_MODE=true` 时保留原内存逻辑（向后兼容），`DEMO_MODE=false` 走 repository。
- **create**：`organization_id` 缺省=当前用户组织；显式指定需管理角色（SYSTEM_ADMIN/HQ_ADMIN/BRANCH_ADMIN/TEAM_LEADER，否则 403）；支持 `allowed_roles`、`metadata`；同名 → 409 `DUPLICATE_NAME`。
- **list / detail**：`DataPermissionChecker(current_user).filter_accessible_org_ids()`（复用 Task 17B 授权组件）+ 角色过滤 → 越权/不存在 404。
- **update / delete**：写权限 = 管理角色 **或** `created_by == current_user.id`；越权 → 403。
- **响应结构**：`_kb_to_dict()` 保持与 Demo 完全一致的字段（id/name/description/category/status/document_count/total_chunks/is_public/allowed_roles/organization_id/version/created_at/updated_at + metadata），不破坏既有前端契约。
- **API path / schema 均未变更**（新增 request 可选字段向后兼容）。

### 权限继承（段4）

- 创建 KB 支持 `organization_id` / `allowed_roles` / `metadata`。
- 验证：AGENT@A 创建的 KB（继承 org A）→ AGENT@A 可见、AGENT@B 不可见（list 过滤 + detail 404）；`allowed_roles=["AGENT"]` → AGENT 可见、HQ_ADMIN 不可见（精确角色匹配，Task 17B §2.3.3 硬约束）。
- 未重新设计权限模型。

---

## 3. 测试（段5）

`backend/tests/knowledge/test_kb_crud.py`（@integration，CI backend-pg 纳入）：

| # | 用例 | 断言 |
|---|------|------|
| 1 | create success | org/roles/metadata/version 落库字段正确 |
| 2 | list isolation | `accessible_org_ids=[A]` → 仅 A + 共享（org=NULL）KB |
| 3 | update permission | 非创建者 403；创建者 200（API 层） |
| 4 | delete cascade | 删 KB → documents/document_chunks 级联清零 |
| 5 | organization scope | AGENT@A 可见、AGENT@B 列表不可见 + 详情 404（API 层真实 checker 链路） |
| 6 | role scope | allowed_roles=["AGENT"]：AGENT 可见、HQ_ADMIN 不可见 |
| 7 | duplicate name | 409 DUPLICATE_NAME + `name_exists` 语义 |

---

## 4. 修改文件

- `backend/app/repositories/knowledge_repository.py`（新建）
- `backend/app/api/v1/knowledge.py`（CRUD 生产化 + helpers + schema 扩展）
- `backend/app/models/knowledge.py`（KnowledgeBase + metadata 列）
- `backend/alembic/versions/0009_kb_metadata.py`（新建迁移）
- `backend/tests/knowledge/test_kb_crud.py`（新建）
- `.github/workflows/backend-tests.yml`（backend-pg 纳入 test_kb_crud）
- `docs/knowledge-crud-audit.md`（本文件）

---

## 5. 边界声明

- 已实现/已验证：KB CRUD 生产化（DB backed）+ 权限继承（org/role/metadata）+ 级联删除 + 同名处理，PG 集成测试固化。
- 未处理（不扩大范围）：知识库文档管理（list_documents/upload/publish/delete_document 的 CRUD 部分仍 Demo）、AI Sales Agent、RAG 算法、权限模型设计。
- Demo 模式行为完全保留（内存数据 + `demo-kb-*` id），前端与既有测试无回归。
