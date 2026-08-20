# Database Backup & Restore Readiness Audit（Task 38 · P1 B1）

> 状态：**IMPLEMENTED / CLOUD VERIFIED（Pilot 级）**——backup + restore + CI 演练全部成功（Task 38）
> 更新：2026-08-20

---

## Current State（现状，源码级审计）

| 项 | 现状 |
|---|---|
| `pg_dump` / `pg_restore` 引用 | **0 命中**（全仓库 343 文件搜索） |
| backup/restore 脚本 | **无**（`scripts/` 仅 deploy.sh、phase5_deploy_check.sh） |
| backup workflow（GitHub Actions） | **无**（现有 5 个：backend-tests / e2e-playwright / frontend-typecheck / production-validation / real-ai-smoke） |
| `docker-compose.prod.yml` | PG16（pgvector/pgvector:pg16）命名卷 `pgdata`，**无备份挂载、无 dump 任务**；backend 启动链 `alembic upgrade head && seed && uvicorn` |
| 生产可执行备份能力 | **无**——任何 PG 卷/数据丢失均不可恢复（仅依赖 Docker 卷存活） |
| 备份存储位置 / retention | **无定义** |
| `.gitignore` | 覆盖 `*.db` / `pgdata/`，**未覆盖 `*.dump / *.backup / *.sql / backups/`**（新增 dump 有误提交风险） |
| `.env.example` | `AZB_DATABASE_URL`（asyncpg 格式）存在；**无备份专用变量**（如 `AZB_BACKUP_DIR`） |
| 凭据管理 | 部署凭据经 `.env.production`（gitignored）+ GitHub Secrets（CI）；备份脚本需沿用，不硬编码 |

## Gap（与生产验收的差距）

1. **无备份产出**：无法生成任何可恢复的数据库逻辑备份。
2. **无恢复路径**：无 `pg_restore` / 恢复脚本 / 恢复演练，无法证明备份可恢复。
3. **无完整性保障**：无 backup 文件校验（size/checksum/exit code）、无恢复后数据核验。
4. **无保留策略**：无 retention / 归档定义。
5. **无自动调度**：无 cron / workflow_dispatch 备份入口。
6. **CI 数据库 ≠ 生产备份**：backend-pg / production-validation 的 PG 仅服务测试，不构成备份能力（本 Task 明确不以此充数）。

## Production Risk

- **P1（正式生产阻塞，Task 36 确认）**：数据丢失（误删/部署事故/卷故障/勒索）后**无任何恢复手段**；当前唯一"防线"是 Docker 卷本身。
- 无备份 = 无可恢复性承诺；内部试点（PILOT）期间为 Accepted Risk，正式生产前必须收敛。

## Recommended Target（Pilot 级最小方案，本 Task 落地）

1. **`scripts/backup_database.sh`**：`pg_dump` custom format（`-Fc`）→ 带时间戳备份文件 → 输出目录可配（`AZB_BACKUP_DIR`）→ 失败非 0 → 打印安全摘要（文件、size、checksum）→ 不打印凭据。
2. **`scripts/restore_database.sh`**：目标库清理 → `pg_restore` 恢复 → exit code 校验 → 打印恢复摘要。
3. **`.github/workflows/database-backup-restore.yml`**（`workflow_dispatch`）：云端 PG16+pgvector → alembic → seed → **backup → 干净目标 → restore → 核验**（表数/关键数据/org/KB/Document/AuditLog/pgvector embedding）。
4. **完整性校验**：backup 存在 + size>0 + exit 0 + restore exit 0 + 确定性 row checks（seed 数据计数）。
5. **安全**：全程 synthetic/seed 数据；dump 产物仅存 runner 临时目录（`/tmp`），**不进 Git**；`.gitignore` 补充 dump/backup 扩展名。
6. **保留策略**：脚本/CI 演练按「覆盖式」管理（每次演练覆盖旧 artifact）；**正式生产自动备份（每日/每小时）+ 独立持久化对象存储 + 加密 + retention 为外部依赖**，文档明确，不伪造实现。

## Out of Scope（本 Task 不实现，记录为 Production Hardening 外部依赖）

- 云厂商对象存储（S3/GCS/COS）接入与正式归档。
- 自动定时备份 cron（需外部 scheduler / 云 DB 托管备份策略）。
- WAL 归档 / PITR（时间点恢复）、跨地域灾备、备份加密存储。
- 正式生产流量下的 backup 性能基准 / RPO-RTO 承诺。

## Cloud Verification（24cc2b1 演练 run 32344482596 全绿，日志可复现）

- `FIXTURE_OK`：合成数据写入（KB/Document/3 chunks/AuditLog，embedding 1536 维）
- `SNAPSHOT_OK` baseline：users 4 / roles 7 / role_permissions 84 / organizations 6 / knowledge_bases 1 /
  documents 1 / document_chunks 3 / audit_logs 1 / training_scenarios 23 / alembic_version 0010_audit_log_org_scope
- `BACKUP_OK`：dump size=131217，sha256 已记录；`INTEGRITY_OK`（存在 + size>0）
- `RESTORE_OK`：pg_restore 到干净目标库 anzhenbao_restore
- `VERIFY_OK`：**restored == baseline，mismatches={}**（含 org/KB/Document/AuditLog 与 pgvector）
- `APP_READY`：应用连接恢复库 `/api/v1/ready` 通过（2s）
- `NONZERO_OK`：错误凭据 → 非 0 退出
- `NO_BACKUP_IN_GIT_OK`：无 dump/backup 文件进入 Git

## Test Matrix（阶段 7，云端验证）

| # | 用例 | 通过标准 |
|---|---|---|
| 1 | backup script success | exit 0、文件生成 |
| 2 | invalid credentials → non-zero | 错误连接串 → 非 0 退出、安全报错 |
| 3 | backup file integrity | 存在、size>0、（sha256 校验） |
| 4 | restore to clean PG | 干净目标库恢复 exit 0 |
| 5 | restored key tables/data | 表数 + seed 确定性行数一致 |
| 6 | pgvector survives restore | vector 列可查询、embedding 计数一致 |
| 7 | Alembic-compatible state | 恢复后 alembic_version 与预期一致 |
| 8 | app health against restored DB | 应用连接恢复库 /ready 通过 |
| 9 | backup artifacts 不进 Git | repo 无 dump/backup 文件 |
| 10 | backup/restore 不破坏 seed | 恢复后 seed 数据完整、无重复 |
