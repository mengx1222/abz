# Documentation Reconciliation Audit（Task 43 · 全仓库文档现实同步）

> 目的：把 GitHub main 所有项目文档统一到当前真实状态；消除历史漂移/过时数字/错误状态/文档间矛盾。
> 规则：GitHub main 源码为唯一代码事实；测试/验证数字以对应 GitHub Actions 真实 run 为证据。

---

## 当前事实真相表（Source = 源码/CI 证据）

| 项 | 真实值 | Source / Commit / Workflow Evidence |
|---|---|---|
| Git HEAD | `887dce5`（main == origin/main） | refs API 2026-08-20 |
| Version | `0.1.0`（backend/pyproject + frontend/package.json + config.APP_VERSION 一致） | Task 35 对齐后复核 |
| 技术栈 | FastAPI + SQLAlchemy async + PostgreSQL 16/pgvector + Redis 7 + React/TypeScript/Vite + structlog | backend/pyproject、frontend/package.json |
| Release Decision | **PRODUCTION CANDIDATE**（Task 42 Security Final Review） | docs/security-final-review.md @ 887dce5 |
| Backend pytest | **307 passed / 68 skipped** | CI run @ 887dce5 |
| Backend PG（真实 PG16+pgvector） | **59 passed** | CI backend-pg @ 887dce5 |
| Vitest | **107 passed** | CI frontend @ 887dce5 |
| TypeScript hard gate | **tsc -b 0 errors**（Task 19 RESOLVED） | CI frontend typecheck step @ 887dce5 |
| Vite build | ✓ | CI @ 887dce5 |
| Playwright E2E | **27 passed**（含 Golden Flow） | e2e-playwright @ 045f87d（Task 33；其后无 frontend/src 变更，仍为最新有效） |
| Real AI Smoke | 最近 **PASS @ 94ce52f（2026-08-15）**；其后 runs 因 `REAL_AI_SMOKE_TEST` 开关未开启 **skipped**（opt-in workflow） | real-ai-smoke workflow runs |
| Performance Benchmark | **Cloud CI Capacity Baseline**（Task 41，非 SLA；真实 AI 层 NOT RUN） | performance-benchmark @ da3edcf |
| API endpoints | **92**（backend/app/api/v1 routers） | 源码统计（api.md 旧值 89 过时） |
| Frontend routes | **22**（routes.tsx） | 源码统计（information-architecture 旧值 21 过时） |
| Alembic migrations | **10 个版本文件，head=0010_audit_log_org_scope** | backend/alembic/versions（database.md 旧值 7 过时） |
| P1 blockers | **无**（B1/B2 已收敛 Task 37/38） | docs/security-final-review.md |
| P2 / Accepted Risks | localStorage token、环境 badge、上传病毒扫描、Redis HA、外部告警平台、滚动发布、渗透测试、演示凭据轮换、真实硬件性能基准 | docs/security-final-review.md |
| Backup/Restore | IMPLEMENTED / CLOUD VERIFIED（Task 38 云端双绿） | database-backup-audit.md |
| Audit Log | RESOLVED / DB 持久化 + org 隔离（Task 37） | audit-log-production-audit.md |
| Observability | Signals Ready（Task 39；外部告警平台 Integration Required） | observability-audit.md |
| Redis multi-instance | IMPLEMENTED / CLOUD VERIFIED（Task 40；外部 Redis HA 为依赖） | redis-multinstance-audit.md |

## 已确认的文档漂移（待修正）

| 文档 | 漂移 | 修正 |
|---|---|---|
| README.md | ①发布状态 "Internal Pilot Candidate"（现 PRODUCTION CANDIDATE）②Known Limitations：TS hard gate 待恢复（已 RESOLVED）/AI Sales Agent 未实现（已实现）/前端组件测试仅 utils（已全覆盖）/CSRF 未实现（复核 N/A）③Playwright "11/11"（现 27）④文档索引 "7 迁移"（现 10） | 更新状态与限制、测试数字、迁移数 |
| docs/deployment.md | §4.2/4.3 "make init 10 步" + 虚构账号 admin/admin123/hq_admin/demo123（真实：alembic upgrade + python -m scripts.seed；demo 账号 1380013800x/888888） | 对齐真实初始化与演示账号 |
| docs/database.md | 迁移数 "7 个 Alembic 迁移"（现 10，head=0010） | 更新迁移数 |
| docs/release-verification.md | Real AI Sales Agent Smoke 行 "无 key 时 NOT RUN"（最近 PASS @ 94ce52f；opt-in） | 更新表述 |
| docs/api.md | "89 端点（2026-08-17）"（现 92） | 更新数字（以代码为准） |
| docs/information-architecture.md | "21 条路由"（现 22） | 更新数字 |
| 历史记录（worklog/Historical Log/Task audit） | 旧测试数字/旧 HEAD/旧状态 = 历史当时事实 | **保留**（不重写历史） |

## 统一状态枚举

`Implemented` / `Validated` / `Planned` / `Known Limitation` / `Accepted Risk` / `Not Implemented` / `Not Verified`。

## 保留与不动的部分

- worklog.md 与 Task audit 文档的历史记录（Task 9/15/30-36 等原始结论与数字）保留——历史事实不美化。
- 当前 Snapshot/Open Issues 区不再出现已收敛项（本次修正的核心）。
