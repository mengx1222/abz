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
| Git HEAD | `9befe4b`（Task 15 Release Baseline） |
| GitHub main HEAD | 与 HEAD 一致（default branch = main） |
| Repository Status | CLEAN（Task 14 清理后 268 blob；无 download/upload/tool-results/skills/.env） |

---

## 2. 模块验证状态

| 模块 | 状态 | 依据 |
|------|------|------|
| Backend | ✅ | pytest **224 passed, 5 skipped**（CI 8050d0b）；FastAPI + SQLAlchemy 2 async + Alembic |
| Frontend | ✅ | Vitest **27 passed（3 files）** + `vite build` ✓（CI）；React 19 + Vite 8 + TS ~6.0 |
| PostgreSQL 16 + pgvector | ✅ | PG 集成 **5 passed**（含 RAG 产品边界测试）；Production Validation 真实容器 |
| Redis | ✅ | Production Validation 真实容器 |
| RAG | ✅ | 向量+BM25+RRF+Confidence Gate+Refusal+Citation+**产品边界**（Task 12/13 修复闭环，E2E 验证） |
| Real AI Provider | ✅ | 阿里云百炼 DashScope（qwen-plus / text-embedding-v3）；**Real AI Smoke 8/8 PASS**（真实，非 Mock） |
| Security | ✅ | JWT/RBAC（7 角色）/IDOR 防护/限流/输入消毒/Prompt Injection/安全头/审计/Secret 不入库 |
| Compliance | ✅ | GREEN/YELLOW/RED 规则引擎 + 生成链验证 + 徽章 UI + 管理后台规则/审核流 |
| E2E（Playwright） | ✅ | **11/11 PASS**：Stage 1（Login/Dashboard/Customer List/Detail）+ Stage 2（Product QA 4 + Script 3） |
| Docker | ✅ | dev + prod compose；Production Validation 在 8050d0b 全绿 |
| Health / Ready | ✅ | `/api/v1/health`、`/api/v1/ready`、`/api/v1/health/detail` |

---

## 3. Test Snapshot（最新真实结果）

| 测试域 | 结果 | 位置 |
|--------|------|------|
| Backend pytest（SQLite） | **224 passed, 5 skipped** | CI `backend-tests` @ 8050d0b |
| Backend PG 集成（真实 PG16+pgvector） | **5 passed** | CI `backend-pg` @ 8050d0b |
| Frontend Vitest | **27 passed（3 files）** | CI `frontend` @ 8050d0b |
| Frontend build | `vite build` ✓ | CI `frontend` @ 8050d0b |
| Playwright E2E | **11/11 passed（37.8s）** | CI `e2e-playwright` @ 477a3ca（代码未变） |
| Real AI Smoke | **8/8 PASS** | CI `real-ai-smoke` run 31866434810（commit 94ce52f） |
| Production Validation | **PASS** | CI @ 8050d0b |

> 历史测试数字（133/151/163/174/190/197/206/210/221...）见 [project-status.md](project-status.md) 的 Historical Verification Log（G 记录），不再混入 Current Snapshot。

---

## 4. Known Issues

| 级别 | 项 | 状态 |
|------|-----|------|
| **P0** | 无 | — |
| P1-3 | growth_service.course_detail 生产路径仍 Demo Only（DB 无课程表） | 未解决（成长模块主链路不受影响） |
| P1-6 | 前端既有 TypeScript 类型错误，CI 暂用 `vite build` 绕过 tsc 硬门禁 | 未解决（TS 清理为独立任务） |
| P2-1 | 无 CSRF 显式防护 | 低风险（JWT Bearer） |
| P2-2 | Demo 模式无 Token 返回 200 | 低风险（仅 Demo） |
| P2-3 | 前端页面组件无测试 | 仅 utils 有 vitest |
| P2-4 | Seed 未集成到迁移 | 需手动执行 |
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
| Playwright Stage 2 | ✅ |
| CI Green | ✅ |
| Docs Consistent | ✅（Task 15 校准） |
| No P0 | ✅ |

**Internal Pilot: YES** → 判定 **READY FOR INTERNAL PILOT**（详细判定见 [release-readiness.md](release-readiness.md)）。

> 注意：**READY FOR INTERNAL PILOT** ≠ PRODUCTION READY。进入生产前须：恢复前端 tsc 门禁、收敛 P1/P2、生产部署演练、安全复审。
