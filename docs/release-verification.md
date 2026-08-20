# Release Verification Snapshot — 安诊保 AI 副驾



> 建立时间：2026-08-17

> 本文件为本次 **Release Baseline 真实验证快照**，与 [project-status.md](project-status.md)（唯一当前状态来源）互证。

> 判定来源：最新 CI（`backend-tests` / `production-validation` / `e2e-playwright`）+ 历史 Real AI Smoke 记录。



---



## 1. 版本与 Git



| 项 | 值 |

|----|-----|

| Release Version | **v0.1.0**（backend/pyproject.toml = 0.1.0，frontend/package.json = 0.1.0，README = v0.1.0） |

| Release Status | **Internal Pilot Candidate** |

| Git HEAD（验证时 Current main） | **Task 42（Security Final Review + Production Candidate Gate，58cca41）** |

| Release Baseline Content | `9befe4b`（Task 15） |

| GitHub main HEAD | 与 HEAD 一致（default branch = main；无 force push） |

| Repository Status | CLEAN（无 download/upload/tool-results/skills/.env；仅占位符模板 .env.example/.env.production；Task 24 卫生扫描通过） |



---



## 2. 模块验证状态



| 模块 | 状态 | 依据 |

|------|------|------|

| Backend | ✅ | pytest **265 passed, 5 skipped**（Task 17B 本地全量；基线 228 → 265）；FastAPI + SQLAlchemy 2 async + Alembic |

| Frontend | ✅ | Vitest **27 passed（3 files）** + **TypeScript `tsc -b` 0 errors + CI Hard Gate（Task 19）** + `vite build` ✓；React 19 + Vite 8 + TS ~6.0 |

| PostgreSQL 16 + pgvector | ✅ | PG 集成 **5 passed**（含 RAG 产品边界）+ **RAG 权限边界 5 用例**（test_permission_pg.py，CI backend-pg 纳入）；Production Validation 真实容器 |

| Redis | ✅ | Production Validation 真实容器 |

| RAG | ✅ | 向量+BM25+RRF+Confidence Gate+Refusal+Citation+**产品边界**（Task 12/13）+ **权限过滤（allowed_roles + 组织范围，Task 17B）** + **Production Ingestion（Task 20）**：Role Filtering Implemented+Tested（test_role_filter.py）、Organization Filtering Implemented+Tested（test_org_scope.py）、Citation/SSE Leakage Protected（test_citation_leak.py）、Prompt Injection Cannot Bypass（test_permission_pg.py::J） |

| Real AI Provider | ✅ | 阿里云百炼 DashScope（qwen-plus / text-embedding-v3）；**Real AI Smoke 8/8 PASS**（真实，非 Mock） |

| Security | ✅ | JWT/RBAC（7 角色）/IDOR 防护/限流/输入消毒/Prompt Injection/**RAG 权限边界（Task 17B）**/安全头/审计/Secret 不入库 |

| Compliance | ✅ | GREEN/YELLOW/RED 规则引擎 + 生成链验证 + 徽章 UI + 管理后台规则/审核流 |

| E2E（Playwright） | ✅ | **13/13 PASS**：Stage 1（Login/Dashboard/Customer）+ Stage 2（Product QA/Script）+ **Stage 3 Training（Task 17A）** |

| Docker | ✅ | dev + prod compose；Production Validation 在 8050d0b 全绿 |

| Health / Ready | ✅ | `/api/v1/health`、`/api/v1/ready`、`/api/v1/health/detail` |



---



## 3. Test Snapshot（最新真实结果）



| 测试域 | 结果 | 位置 |

|--------|------|------|

| Backend pytest（SQLite） | **307 passed, 68 skipped**（含安全态势 12；audit demo 回归 4 Task 37；observability 7 Task 39；redis multi-instance 9 Task 40 由专用 workflow 覆盖） | CI `backend-tests` @ Task 40（c2a6eae） |

| Backend PG 集成（真实 PG16+pgvector） | **59 passed**（+Agent RAG 权限/黄金链/IDOR 5 Task 27；+上传大小限制 Task 34；+seed 幂等 3 Task 35；+audit log 6 Task 37；+org/role 隔离与敏感字段 5 Task 37b） | CI `backend-pg` @ Task 37b（6fc74db） |
| DB Backup & Restore 演练（Task 38） | **PASS**：backup(131217B)→clean restore→verify 全绿（restored==baseline，mismatches={}；pgvector 1536 维恢复；alembic 0010；app /ready） | `database-backup-restore.yml` @ Task 38（24cc2b1） |
| Observability（Task 39） | **Signals Ready**：/ready 503 + READINESS_FAILED；request 日志 user_id/org/error_code；AI error_code（401/429/5xx）+ 去 body；RAG retrieval/latency；redaction 7 用例全过 | `backend-tests` @ Task 39（0425d67） |
| Redis Multi-instance（Task 40） | **PASS**：RateLimit Redis 原子计数（跨实例共享）+ Agent session 共享（TTL 3600s）+ fail-closed 503 + 9/9 真实 Redis 集成用例 | `redis-multiinstance.yml` @ Task 40（c2a6eae） |
| Performance Baseline（Task 41） | **PASS（Cloud CI Capacity Baseline）**：health 2.1ms/427tps、kb 20.8ms、容量 1-10 并发线性 0 err、RAG 0.36-0.8s、Redis 2.3-4.7ms、Sales Agent 28.8ms（mock）；真实 AI NOT RUN | `performance-benchmark.yml` @ Task 41（0d47da0） |

| Frontend Vitest | **107 passed（16 files）**（含 ErrorBoundary 4，Task 33；Admin 8/8 页面组件全覆盖） | CI `backend-tests` frontend job @ Task 33（045f87d） |

| Frontend build | `tsc -b` 0 errors + `vite build` ✓ | CI `frontend` @ Task 24 |

| Playwright E2E | **27 passed**（+GF-1 Golden Business Flow 完整黄金链） | CI `e2e-playwright` @ Task 29 |

| Real AI Smoke | **8/8 PASS** | CI `real-ai-smoke` run 31866434810（commit 94ce52f） |

| Production Validation | **PASS** | workflow_dispatch @ Task 28（手动触发，docker compose + PG/Redis 真实容器） |



> 历史测试数字（133/151/163/174/190/197/206/210/221...）见 [project-status.md](project-status.md) 的 Historical Verification Log（G 记录），不再混入 Current Snapshot。



---



## 4. Known Issues



| 级别 | 项 | 状态 |

|------|-----|------|

| **P0** | 无 | — |

| P1-3 | growth_service.course_detail 生产路径仍 Demo Only（DB 无课程表） | 未解决（成长模块主链路不受影响） |

| ~~P1-6~~ | ~~前端既有 TypeScript 类型错误，CI 暂用 `vite build` 绕过 tsc 硬门禁~~ | ✅ **RESOLVED（Task 19）**：`tsc -b` 0 errors + CI Hard Gate 恢复 |

| ~~P2-1~~ | ~~无 CSRF 显式防护~~ | ✅ **收敛（Task 24；Task 34 复核确认已解决，不重复实现）**：Bearer 架构无 CSRF 攻击面（ACCEPTED LIMITATION）+ 防御测试 4 + CSRF 回归 5（Task 34） |

| ~~P2-2~~ | ~~Demo 模式无 Token 返回 200~~ | ✅ **RESOLVED（Task 24）**：3 Confirmed Bug 修复（含受保护端点 500→401 真实 bug）+ 测试 3 |

| ~~P2-3~~ | ~~前端页面组件无测试~~ | ✅ **RESOLVED（Task 24/32/33）**：Admin 8/8 页面组件测试全覆盖（Task 32 +22 用例）；Task 33 审计复核见 [admin-component-test-audit.md](admin-component-test-audit.md) |

| 无 ErrorBoundary（P2） | 全局错误边界缺失，页面渲染错误整页白屏 | ✅ **RESOLVED（Task 33）**：ErrorBoundary 全局接线（App.tsx）+ 组件测试 4 用例；Vitest 107 passed |

| 上传无大小限制（P2） | KB 文档上传无限制，超大文件整读内存（DoS 向量） | ✅ **RESOLVED（Task 34）**：MAX_UPLOAD_SIZE_MB=10 + Content-Length 预检 + 读取后校验 → 413 FILE_TOO_LARGE；PG 45 passed |

| seed 权限绑定丢失（P2-4） | seed.py 绑定插入缺 await，role_permissions 静默不落库 | ✅ **RESOLVED（Task 35）**：补 await + 幂等回归测试 3（backend-pg 48 passed，df00d11） |

| 版本号不一致（P2-4） | config APP_VERSION=1.0.0-rc.1 ≠ 0.1.0，health 对外失真 | ✅ **RESOLVED（Task 35）**：对齐 0.1.0 |

| 前端镜像构建绕过 tsc（P2-4） | frontend/Dockerfile 用 npx vite build（P1-6 过时注释） | ✅ **RESOLVED（Task 35）**：改 npm run build，对齐 CI 门禁 |

| ~~P2-4~~ | ~~Seed 未集成到迁移~~ | ✅ **RESOLVED（Task 24）**：e2e seed 确定性加固 + 幂等测试 3 |

| — | Training E2E / Growth E2E | **Planned / Remaining**（非本次范围） |

| — | AI Sales Agent | **Planned**（未实现） |



---



## 5. Internal Pilot Readiness



| 最低标准 | 满足 |

|----------|------|

| Core Production Services | ✅ |

| PostgreSQL + pgvector | ✅ |

| Redis | ✅ |

| Docker | ✅ |

| Real AI Provider | ✅ |

| Real AI Smoke | ✅ 8/8 |

| RAG | ✅ |

| Citation | ✅ |

| Refusal | ✅ |

| RBAC | ✅ |

| Compliance | ✅ |

| Playwright Stage 1 | ✅ |

| Playwright Stage 3（Training） | ✅（Task 17A） |

| Playwright Stage 2 | ✅ |

| CI Green | ✅ |

| Docs Consistent | ✅（Task 15 校准） |

| No P0 | ✅ |



**Internal Pilot: YES；Production Candidate: YES**（Task 42 Security Final Review）→ 判定 **PRODUCTION CANDIDATE**（Accepted Risks：外部告警平台、云托管备份/多地域灾备/Redis HA、滚动发布、渗透测试；详见 [security-final-review.md](security-final-review.md)）。



> 注意：**PRODUCTION CANDIDATE** ≠ PRODUCTION READY。升级生产前须收敛 Accepted Risks：外部告警平台接入、云托管数据库备份/多地域灾备/Redis HA、滚动发布、正式渗透测试、演示凭据轮换。


| Real AI Sales Agent Smoke | **opt-in / workflow_dispatch**（phase10 黄金链，需 Secrets；无 key 时 NOT RUN） | CI `real-ai-smoke` |

| Real AI Golden Flow Smoke | **phase11 新增（opt-in）**：登录→客户→Agent(RAG/Citation/Compliance)→Training(评分)→Growth(数据连续)；真实 Provider；需手动 workflow_dispatch | CI `real-ai-smoke` @ Task 29 |

| Production Readiness Review | **READY FOR INTERNAL PILOT（Task 30）**：Security/Data/AI/RAG/Frontend/E2E/Deployment Gate PASS；Backup NOT IMPLEMENTED（P1）；Observability/Audit PARTIAL；详见 [production-readiness-review.md](production-readiness-review.md) |
