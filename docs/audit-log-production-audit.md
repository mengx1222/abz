# Audit Log Productionization Audit（Task 37）

> 状态：**RESOLVED**（真实 PostgreSQL 持久化 + 组织/角色权限隔离 + 云端全绿）
> 更新：2026-08-20（Task 37b 补强：organization_id 列 + 权限隔离 + sensitive 防护验证）

---

## Current State（现状）

- **模型**：`backend/app/models/audit_log.py::AuditLog`（表 `audit_logs`）字段完整：
  `user_id / organization_id（Task 37b 新增）/ action / resource_type / resource_id /
  description / detail(JSONB) / ip_address / user_agent / request_id / status / created_at`
- **迁移链**：`0006`（建表）→ `0007`（补 request_id）→ `0009`（基线）→ **`0010_audit_log_org_scope`（Task 37b 新增 organization_id 列 + 索引）**；alembic head = `0010_audit_log_org_scope`，`upgrade`/`downgrade` 对称
- **中间件**：`app/core/audit.py::AuditMiddleware` 广谱捕获 `POST/PUT/DELETE/PATCH`（跳过 /health、/ready），生产模式异步落库（独立 session），失败仅告警**不影响主业务**
- **显式高保真记录**（`record_audit_log`，比中间件语义更准）：KB create/update/delete、Document upload/publish/unpublish/delete、Auth login 成功（含组织归属）/失败
- **查询端点**：`GET /api/v1/admin/audit-logs`（SYSTEM_ADMIN/HQ_ADMIN/BRANCH_ADMIN/COMPLIANCE）——生产分支读真实 DB，demo 分支内存数据（兼容）
- **Repository**：`app/repositories/audit_log_repository.py`（create_log / list_logs 过滤+分页+倒序 / query_by_user / query_by_resource；UUID 归一化、列长截断、organization_ids 范围过滤）

## Gap（上一轮 67de760 对照生产验收的缺口）

| 缺口 | 说明 | 处置 |
|---|---|---|
| 无 organization_id 列 | 无法按组织隔离审计查询，且上一轮交付"无新增迁移"不满足 Alembic migration 验收 | ✅ 0010 迁移新增列 |
| 读端点无组织范围隔离 | BRANCH_ADMIN 可见全库（角色门槛已挡 AGENT，但管理角色间无组织隔离） | ✅ Task 37b C3 修复 |
| 权限隔离测试缺失 | 无组织越权/角色越权/同组织/管理员测试 | ✅ Task 37b C4 新增 5 用例 |
| sensitive 不落库无验证 | 中间件天然不落 body，但无测试固化契约 | ✅ 新增用例验证 |
| retention policy 未文档化 | 项目无自动清理基础设施 | 📋 记录为运维项（见下） |

## Target State（目标态）

- 审计事件真实落库（生产模式），可按 user/org/action/resource/时间过滤 + 分页查询
- 组织/角色双维度隔离：AGENT 403；HQ/BRANCH_ADMIN 仅见本机构+子机构；SYSTEM_ADMIN/COMPLIANCE 全库
- 敏感数据不落库；写入失败不破坏主业务事务

## Security / Privacy Boundary

- **不落库**：密码、JWT、API Key、Secret、完整 prompt、请求体（中间件仅记录 method/path/status_code；显式记录仅业务语义 description）
- **不泄露存在性**：组织越权采用**过滤式**（结果不含越权行）而非 403 报错，避免暴露其他组织审计事件的存在性；与项目既有列表查询约定一致
- **写失败策略**：`record_audit_log` 使用独立 session，捕获异常仅告警——核心业务事务不会因审计 DB 短暂异常而不可控；安全审计事件在中间件层亦不阻塞请求（响应已产生）

## Retention Policy

- 项目当前**无自动清理/归档基础设施**（无 cron、无 TTL job）——按验收要求**不伪造实现**
- 📋 **运维项（后续）**：建议生产部署时配置 `audit_logs` 定期清理（如保留 180 天，`DELETE WHERE created_at < now() - interval '180 days'` 分批执行 + 归档冷存储）；当前全量保留不设上限
- 索引 `ix_audit_logs_created_at` / `ix_audit_logs_organization_id` 支撑范围查询

## Migration Plan

- 0010 迁移 `add_column audit_logs.organization_id (UUID, nullable, index)`；downgrade `drop_index + drop_column`
- CI backend-pg：alembic `upgrade head`（0001→0010）验证通过；backend 全量 pytest + PG 集成测试 59 passed

## Test Matrix（Task 37b 增补，CI 日志提取真实数字）

| 维度 | 用例 | 结果 |
|---|---|---|
| Repository 增查 | create/list/过滤分页/query_by_* | ✅ |
| 落库正确性 | KB create → user_id/resource_id/description 正确 | ✅ |
| 删除保留 | 删除 KB 后审计行仍在（不级联） | ✅ |
| 读端点真实数据 | list_audit_logs 生产返回 DB 行（含 user_name） | ✅ |
| **角色越权** | AGENT → /admin/audit-logs **403** | ✅ |
| **组织越权** | BRANCH_ADMIN(orgA) 不见 orgB 审计行 | ✅ |
| **同组织可见** | BRANCH_ADMIN 见本 org 行 | ✅ |
| **管理员全库** | SYSTEM_ADMIN 见所有 org 行 | ✅ |
| **敏感字段不落库** | 中间件行 detail 仅 status_code，description 无 password/jwt/token/secret | ✅ |
| demo 回归 | login 成功/失败/logout/audit-logs demo 分支照常 | ✅ |

## 验证记录（6fc74db 全矩阵全绿）

- Backend: **300 passed / 59 skipped**；PG: **59 passed**（audit 11 全过）；Vitest **107（107）**；tsc 0；build ✓；Production Validation ✅
- 无 frontend/src 变更 → E2E 不触发（符合路径过滤，未强行改动）
- GitHub main == origin/main

## B2 Status

**RESOLVED**（Task 37 + Task 37b 补强）：Audit Log PostgreSQL-backed、migration、repository/service 架构、
关键生产 mutation 真实记录、组织/角色权限隔离、sensitive 不落库、CI 全绿——全部验收条件满足。

> Release Decision 不变：**READY FOR INTERNAL PILOT ONLY**（B1 数据库备份仍 OPEN，另有监控/多实例/凭据轮换等差距，不夸大为 Production Ready）
