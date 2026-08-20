# Audit Log 现状审计（Task 37 — P1 B2 落库前审计）

> 审计日期：2026-08-20
> 基线：main@`4e9150f`（Task 36 RC Audit 全绿）
> 方法：100% Cloud-only —— GitHub API 读取 audit 模型/中间件/迁移/管理端点源码
> 结论：模型与中间件钩子已存在，但 **DB 持久化为 stub**；存在 1 处模型-迁移漂移；读端点生产返回 demo 数据

---

## 1. Current State

### 1.1 模型（`backend/app/models/audit_log.py`）
`AuditLog` 模型**已存在**，字段完整（比 Task 37 建议字段更全）：
- `user_id`（FK users SET NULL，index）/ `action`（String 50，index）/ `resource_type`（String 50，index）
- `resource_id`（UUID，可空）/ `description`（String 500，必填）/ `detail`（JSONB，默认 {}）
- `ip_address` / `user_agent` / `request_id`（String 36）/ `status`（success/failure）
- Base 提供 `id` / `created_at` / `updated_at` / `created_by` / `updated_by` / `is_deleted`

### 1.2 中间件（`backend/app/core/audit.py`）
`AuditMiddleware` **已存在**：捕获 POST/PUT/DELETE/PATCH + /auth/login+refresh，构建 audit_data（action/resource_type/resource_id/user_id/ip/user_agent/request_id/status_code），structlog 记录，并调用 **`write_audit_to_db()` —— 当前为 STUB**（注释"Phase 5 通过 Repository 实现持久化"，仅再记一条 structlog）。
- **缺口 A**：`request.state.user` 几乎永远未设置（get_current_user 是依赖，不写 request.state）→ 中间件捕获的 user_id 恒为 None。
- **缺口 B**：中间件 `action = f"api.{method}.{path}"` 超 `String(50)` 上限 → 直接落库会 DataError。

### 1.3 迁移（`backend/alembic/versions/0006` + `0007`）
`audit_logs` 表由 **0006 创建**（action/resource_type/created_at 索引），**0007_kb_versioning_audit_enhance 已补 `request_id` 列**（注释明确「仅添加 request_id」）——模型字段与迁移**无漂移**，无需新迁移。
> 排障记录：实施时曾误建 0010 迁移补 request_id，CI backend-pg 立即以 `DuplicateColumnError` 暴露重复列 → 删除该迁移，alembic head 保持 0009（f3c9c1a 全绿）。

### 1.4 读端点（`backend/app/api/v1/admin.py::list_audit_logs`）
`GET /admin/audit-logs`（SYSTEM_ADMIN/HQ_ADMIN/BRANCH_ADMIN/COMPLIANCE）**在全部模式下返回硬编码 `_DEMO_AUDIT_LOGS`** —— 生产环境管理员看到的是假审计数据。无 DB 分支。
- 前端 `AuditLogPage`（admin/audit）已存在并调用该端点（Task 32 组件测试覆盖）。

### 1.5 需要审计的关键路径（P0 目标）
| 路径 | 端点 | 现状 |
|------|------|------|
| 知识库 create/update/delete | /admin/knowledge-bases | 生产 DB backed（Task 21）；无显式审计 |
| 文档 upload/publish/unpublish/delete | /admin/knowledge-bases/{id}/documents/* | 生产 DB backed（Task 22）；无显式审计 |
| 认证 login 成功/失败 | /auth/login | 中间件捕获（user_id=None）；无显式审计 |
| 管理权限变更 | /admin/users/* | **admin 用户端点全部 demo-only**（内存 _DEMO_USERS，无生产分支）→ 生产无此路径可审；中间件广谱捕获兜底 |
| 其余写操作（customers/scripts/training/community/compliance） | 各 router | 中间件广谱捕获（落库后由 user_id 归属） |

## 2. Missing（实现缺口）

1. **DB 持久化未实现**（B2 核心）：`write_audit_to_db` 为 stub → 所有审计事件仅 stdout。
2. **无 AuditLog Repository**（`audit_log_repository.py` 不存在）——无 create/list/query 能力。
3. **中间件 user_id 恒 None**（get_current_user 未写 request.state.user）。
4. **读端点生产返回 demo 数据**：管理员无法查看真实审计。
5. **无审计相关测试**（repository/PG/API 层均无）。
6. 模型-迁移：经复核（0006+0007）**无漂移**，无需新迁移（见 §1.3 排障记录）。

## 3. Production Risk

- **B2（P1）**：审计事件无持久化 → 合规追溯/安全调查无数据支撑；管理员审计页显示假数据（误导）。
- 中间件 action 超长若直接落库 → DataError（落库实现时须截断/规范化）。
- audit_logs 表自 0006 存在但从未写入 → 迁移链路从未被写入路径验证。

## 4. Implementation Plan（Task 37）

1. ~~0010 迁移~~ → **已取消并删除**（0007 已含 request_id；误建迁移经 CI 暴露后移除，head 保持 0009）。
2. **Repository（已实现）**：`repositories/audit_log_repository.py` —— create_log / list_logs（过滤+分页）/ query_by_user / query_by_resource；UUID 归一化 + 长度截断。
3. **audit.py（已实现）**：`record_audit_log(...)`（生产独立 session 落库 + 失败仅告警；demo 仅 structlog）+ `write_audit_to_db` 接中间件（action 规范化 ≤50、status 按 status_code）。
4. **deps.py（已实现）**：`get_current_user` 增加 `request: Request`（置于默认参数之前）并 `request.state.user = user`。
5. **关键路径接入（已实现）**：KB create/update/delete；Document upload/publish/unpublish/delete；Auth login 成功/失败；admin `list_audit_logs` 生产分支读 DB。
6. **测试（已实现，全绿）**：`test_audit_log_pg.py` 6 用例 + `test_audit_log.py` 4 用例（demo 回归）。
7. **验证（f3c9c1a 全矩阵）**：Backend **300 passed / 54 skipped**、backend-pg **54 passed**、Vitest **107**、Prod ✅。
8. **范围外（记录）**：admin 用户/合规/社区/话术管理端点整体为 demo-only（生产化属业务功能，Task 37 不开发）；`/admin/users/*` 权限变更由中间件广谱捕获兜底。

## 5. 设计原则（已遵循）

- 不影响现有业务 API / 不改响应结构（读端点同 schema 映射）。
- 审计写独立 session + 内部 try/except → 失败不影响主业务。
- 异步优先（async session）。
- demo 模式行为零变化（仅 structlog）。
