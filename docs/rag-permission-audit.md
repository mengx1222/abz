# RAG 权限审计文档 — Task 17B

> 审计基线：`main @ fe32aa8`（Task 18 修复后）
> 审计日期：2026-08-18
> 状态：审计完成 → 修复已实施（见本文档 §4 与提交记录）

---

## 1. 审计范围

阅读文件：
- `backend/app/rag/retriever.py` / `pipeline.py` / `safety.py`
- `backend/app/core/authorization.py` / `deps.py`
- `backend/app/models/knowledge.py` / `user.py` / `organization.py`
- `backend/app/repositories/*`（无 knowledge 专用 repo，知识库 CRUD 在 `api/v1/knowledge.py` demo 内存实现）
- `backend/app/services/ai/service.py`（ProductQaService）、`script_service.py`、`customer_service.py`
- `backend/app/api/v1/ai.py` / `knowledge.py` / `script.py`
- `docs/rag.md` / `docs/security.md` / `docs/database.md` / `docs/architecture.md` / `docs/project-status.md` / `worklog.md`

---

## 2. 审计表

| 审计项 | 当前实现（文件:行号） | 缺口 | 修复方案锚点 |
|--------|----------------------|------|--------------|
| `KnowledgeBase.allowed_roles` 字段定义 | `models/knowledge.py:48-50` — JSONB, nullable=True（null=全员）；alembic `0002_knowledge_ai.py:37` 一致 | 字段存在，但**从未在检索链路使用** | `retriever.py` SQL WHERE 层按 `allowed_roles` 过滤（`?` 操作符） |
| `KnowledgeBase.organization_id` 字段定义 | **不存在**（模型与 alembic 0002 均无此列） | 组织范围无处落地，`org_id` 被误用为 KB id（见下） | 模型 + 新迁移 `0008` 增加可空 `organization_id`（FK organizations.id，SET NULL）；`NULL` 语义=未限定组织（历史数据全局可见，等效 `is_public`），已设置则严格按可访问组织过滤 |
| `Retriever._filter_by_permission` 现状 | `retriever.py:482-489` — 空实现 `return results  # TODO: 实现权限过滤逻辑` | 角色过滤完全缺失；且仅在召回后 Python 过滤（Step 4），非 SQL WHERE 层 | 填充真实逻辑：SQL 层主过滤 + 本方法作为召回后二次校验（纵深防御），日志记录 `filtered_count` 不记录正文 |
| `Retriever.search(user_roles, org_id)` 调用链 | `retriever.py:192-239` 接收参数；`pipeline.py:181-235` `query()` 接收 `user_roles` **无 `org_id` 透传**；`chat_with_rag()` 同 | pipeline 不传 org_id；DemoRetriever 忽略 user_roles/org_id；部分调用方不传 user_roles | pipeline `query()/chat_with_rag()` 新增 `org_id`/`accessible_org_ids` 透传；调用方按 §4.4 补传 |
| `org_id` 当前语义（是否被误用为 KB id） | `retriever.py:306-307`（vector）/ `383-384`（bm25）：`Document.knowledge_base_id.in_(select(KnowledgeBase.id).where(KnowledgeBase.id == org_uuid))` — 把 org_id 当 **KnowledgeBase.id** 匹配 | **确认误用**。org UUID ≠ KB UUID，条件永不命中；若调用方传 org_id 会把该组织检索全部置空（当前无调用方传参故未暴露） | 改为 `KnowledgeBase.organization_id.in_(accessible_org_ids)` 子查询（§4.2） |
| `_product_boundary_condition` 可否作为权限过滤范式 | `retriever.py:241-255` — SQL WHERE 层条件，与 `status=='published'`、`effective_date` 同级拼入 `_vector_search`/`_bm25_search` stmt | 无（该范式可复用） | 权限条件按同一范式：`_vector_search`/`_bm25_search` 内 JOIN KnowledgeBase + 追加 role/org WHERE |
| `DataPermissionChecker.filter_accessible_org_ids` 可否复用 | `authorization.py:138-170` — SYSTEM_ADMIN→`["__ALL__"]`；HQ/BRANCH_ADMIN→本机构+子机构（正式模式递归 org.children）；TEAM_LEADER→团队+子团队；AGENT→本机构 | 可复用，但 `"__ALL__"` 特殊值需在 SQL 层识别（跳过 org 过滤） | pipeline/调用方用 `DataPermissionChecker(user).filter_accessible_org_ids()` 产出，传 `accessible_org_ids` 给 retriever |
| 各 RAG 调用点是否传 `user_roles`/`org_id` | `ai/service.py:139-143` `_demo_chat`：❌ 均不传（demo 无 user 对象）；`ai/service.py:242-247` `_real_chat`：⚠️ 传 `user_roles=[user.role_code]`、❌ 不传 org_id；`script_service.py:514-516`（production）/ `659-661`（demo）：❌ 均不传（方法仅有 user_id，无 User 对象）；`api/v1/knowledge.py:353` `index_document`：入库路径无检索，不涉及 | 3 处 RAG 检索调用点权限参数缺失/不全 | §4.4 逐个补齐；script_service production 从 DB 加载 User；无用户信息时保守全拒 |

### 硬性确认（与任务描述比对）

1. **角色枚举**：`core/authorization.py:22-28` `_ROLE_HIERARCHY` = `SYSTEM_ADMIN(100) / HQ_ADMIN(80) / BRANCH_ADMIN(60) / TEAM_LEADER(40) / AGENT(20)` ✅ 与任务一致。
2. **组织范围解析**：复用 `DataPermissionChecker.filter_accessible_org_ids()`，SYSTEM_ADMIN 返回 `["__ALL__"]` ✅。
3. **权限继承链**：`KnowledgeBase → Document → DocumentChunk`（FK：chunks.document_id → documents.id → knowledge_bases.id）。**父级权限列（allowed_roles / organization_id）仅存在于 KnowledgeBase**，子表无冗余列 → 检索时经 `Document.knowledge_base_id` JOIN KnowledgeBase 实现子节点继承父节点权限 ✅ 与任务一致（无需改子表）。
4. **`allowed_roles = NULL` 语义**：全员可见但仍受组织范围约束。代码现状 `is_public`/`allowed_roles` 均未参与检索 → 需实现；修复后：role 条件 `allowed_roles IS NULL OR allowed_roles ? role_code`，org 条件独立生效，NULL 不能绕过 org scope ✅ 按任务语义实现。

### 偏差记录（以代码为准）

- **D1（字段缺失）**：`KnowledgeBase.organization_id` 不存在。任务 §2.3 的 SQL 模板假设该字段存在 → 本次新增（模型 + 迁移 0008，可空列）。这是实现组织隔离的必要前置。
- **D2（存量数据 org=NULL）**：现有 seed/测试创建的 KB 均无组织归属。为不破坏存量检索，`organization_id IS NULL` 的 KB 视为"未限定组织"（全局可见，与 `is_public=True` 语义一致）；**已设置 org 的 KB 必须满足 `organization_id IN (accessible_org_ids)`**。最小权限原则下，新知识库建议显式设置组织。

---

## 3. 当前权限链路（修复前）

```
User → Auth(JWT) → RBAC(require_role, 仅路由级) → Org Scope(DataPermissionChecker, 仅客户/文档资源)
→ KB Scope(allowed_roles: 字段存在但检索未用) → Retrieval(无权限 WHERE) → Confidence Gate → LLM → Citation(未过滤)
```

**任一层拒绝知识不得进入最终回答的目标未达成**：`_filter_by_permission` 空桩 + org_id 误用 + 3 处调用点不传参 = 无权限用户物理上可通过 RAG 召回/citation/SSE 获得全部已发布知识。

---

## 4. 修复方案（已实施，对应提交）

| Step | 内容 | 测试 | Commit |
|------|------|------|--------|
| S1 | `_filter_by_permission` 真实实现（SQL 主过滤 + 召回后二次校验）、`allowed_roles` 过滤、SearchResult 携带 kb 权限 | `tests/rag/test_role_filter.py` | `fix(rag): enforce allowed_roles filtering in retrieval` |
| S2 | `org_id` 语义修正 → `KnowledgeBase.organization_id.in_(accessible_org_ids)`；模型 + 迁移 0008；DemoRetriever 组织过滤 | `tests/rag/test_org_scope.py` | `fix(rag): enforce organization scope in retrieval` |
| S3 | pipeline 透传 org_id/accessible_org_ids；ai/service、script_service 调用点补传（DataPermissionChecker 复用） | `pytest tests/rag tests/knowledge`（tests/knowledge 不存在 → tests/rag + 全量） | `fix(rag): propagate user roles and org scope from callers` |
| S4 | Citation/SSE 防泄漏断言（过滤后结果即最终集合）+ 空结果 REFUSE 不降级 | `tests/rag/test_citation_leak.py` | `security(rag): prevent unauthorized citation and sse leakage` |
| S5 | PG/pgvector 集成测试（KB-A/B/C 断言矩阵）+ CI backend-pg 纳入 | `tests/rag/test_permission_pg.py`（@integration） | `test(rag): add pg permission boundary integration tests` |

### 4.1 检索过滤实现（retriever.py）

```python
# _vector_search / _bm25_search 内，与 status/effective_date 同级追加：
stmt = stmt.join(KnowledgeBase, Document.knowledge_base_id == KnowledgeBase.id)
if user_roles:
    stmt = stmt.where(
        or_(
            KnowledgeBase.allowed_roles.is_(None),
            KnowledgeBase.allowed_roles.op("?")(role_code),  # jsonb 存在操作符
        )
    )
if accessible_org_ids and "__ALL__" not in accessible_org_ids:
    stmt = stmt.where(
        or_(
            KnowledgeBase.organization_id.is_(None),          # 未限定组织的共享知识库
            KnowledgeBase.organization_id.in_([uuid.UUID(o) for o in accessible_org_ids if o]),
        )
    )
```

### 4.2 调用方权限参数来源

- `ProductQaService._real_chat` / `_demo_chat`：`DataPermissionChecker(user).filter_accessible_org_ids()` → `accessible_org_ids`；`user_roles=[user.role_code]`；`org_id=str(user.organization_id)`。demo 分支由 `chat()` 把 `user` 透传给 `_demo_chat`。
- `ScriptService._production_generate_scripts`：从 session 查询 `User`（by user_id）→ 同上；查询失败 → `user_roles=[]`（全拒，RAG 走 REFUSE），**不降级到通用知识**。
- `customer_service.py`：审计确认**无 RAG 调用**，无需改动。

### 4.3 DemoRetriever 等价过滤

- chunk dict 扩展 `kb_allowed_roles` / `kb_org_id` 键（`init_demo_index` 注入 demo-kb-001 策略）；
- `search()` 内按 `user_roles`（NULL→全员；非 NULL→role 在数组内）与 `org_id`（NULL→共享；非 NULL→相等）过滤；
- 与 production 语义一致：**allowed_roles NULL 仍受 org 约束**。

### 4.4 Citation / SSE 防泄漏

- 过滤后的 `search_results` 是构造 citation 与 SSE `rag_context`/`style_complete` 引用的**唯一来源**（已审计 `ai/service.py`、`script_service.py`：sources 均从 `search_results` 构造，无第二条数据路径）→ 断言测试 `test_citation_leak.py` 用例 H/I 固化。
- 空结果/低置信度 → 现有 `should_refuse_answer` → REFUSE，无 fallback（用例 J/K 固化）。

---

## 5. 附录：非本次范围问题（只记录，不修改）

| # | 问题 | 位置 | 说明 |
|---|------|------|------|
| N1 | 知识库 CRUD 仅 Demo 内存实现，无 PG 持久化路径 | `api/v1/knowledge.py` | 生产模式 `list/create/update` 均操作 `_demo_knowledge_bases`；文档表由 seed 脚本建立。真实 KB 管理链路未闭环（超出本任务范围） |
| N2 | `RAGPipeline.index_document` 生产分支 `# TODO: 存储到数据库` | `pipeline.py:168` | 生产文档入库未落库，仅 Demo 内存 |
| N3 | `ProductQaService` 会话历史 `# TODO: 从DB加载会话历史` | `ai/service.py:260` | 会话持久化未实现 |
| N4 | `knowledge_permissions` 细粒度表（docs/rag.md §5.3 设计）未建 | docs 设计 vs 实现 | 当前按 KB 级 allowed_roles + org 范围隔离，任务范围内够用 |
| N5 | `docs/rag.md` 中 `metadata.permission` 标签检索设计（§5.2）未实现 | docs 设计 vs 实现 | 与 N4 同源，KB 级权限为本次落地粒度 |
| N6 | CI `backend-pg` job 仅跑 `tests/unit/test_pg_integration.py` | `.github/workflows/backend-tests.yml` | 本次已追加 `tests/rag/test_permission_pg.py`；其余 RAG 生产路径仍只在 unit 层 mock |
| N7 | `authorization.py` 缺 `settings` 导入：`_collect_child_org_ids` 内 `settings.DEMO_MODE`（185 行）NameError | `core/authorization.py` | 既有 bug：生产模式 HQ_ADMIN/BRANCH_ADMIN/TEAM_LEADER 调 `filter_accessible_org_ids()` 组织树收集必崩。`authorization.py` 不在 Task 17B 允许修改范围 → 本次仅记录；PG 测试 monkeypatch 子树收集绕过。建议后续任务补 `from app.core.config import settings`（一行修复） |
| N8 | CI `scripts.seed` 创建的共享知识库 `organization_id=NULL`（全局可见语义）会进入任何用户检索集合，污染权限断言 | `backend/scripts/seed.py` | 业务语义：org=NULL=未限定组织的共享知识库（全员可见，设计如此）。测试侧处理：`test_permission_pg._seed` 前置删除 org=NULL KB（级联），保证权限矩阵断言纯净。seed 脚本本身不在本任务范围 |

---

## 6. 最终原则校验

> 一个没有权限的人，物理上无法通过 RAG（召回、citation、SSE、日志正文）获得这份知识。

- 召回：SQL WHERE 层过滤（vector + BM25 双路径）✅
- citation：过滤后集合构造 ✅
- SSE：`rag_context`/`style_complete` 引用来源同源过滤 ✅
- 日志：仅记 `filtered_count`，不记被过滤正文 ✅
- 拒答：空结果走 `should_refuse_answer` → REFUSE，无 fallback ✅
