# 发布就绪基线 — 安诊保 AI 副驾

> 建立时间：2026-08-17
> Git HEAD：`fedc279`（Task 16 校准：GitHub main == origin/main == Release Baseline）
> 项目版本：`0.1.0`（pyproject）
> 判定：**READY FOR INTERNAL PILOT**（尚未生产部署）

---

## 1. 能力检查表

| 维度 | 状态 | 依据 |
|------|------|------|
| Core Services Production 化 | ✅ | 全部 Service 生产路径闭环（P1-4 已清） |
| 真实 PostgreSQL + pgvector | ✅ | Production Validation + PG 集成测试（含产品边界） |
| 真实 Redis | ✅ | Production Validation |
| 真实 AI Provider（DashScope/Qwen） | ✅ | Real AI Smoke 8/8 PASS（qwen-plus / text-embedding-v3） |
| RAG（向量+BM25+RRF+Confidence Gate+Citation+产品边界+**权限过滤**） | ✅ | Task 12/13 E2E 真实验证 + **Task 17B RAG 权限加固（allowed_roles + 组织范围，SQL WHERE 层；tests/rag/ 35 用例 + PG 权限边界 5 用例）** |
| 安全（JWT/RBAC/限流/消毒/Prompt Injection/**RAG 越权防护**） | ✅ | 单元 + API 集成测试；RAG 权限阻断项已清零（Task 17B） |
| Playwright E2E | ✅ | 阶段一 + 阶段二，11/11 PASS |
| Frontend | ✅ | Vitest + Vite build 通过 |
| Backend | ✅ | pytest 全绿（单元/集成/PG） |
| Docker 部署 | ✅ | 开发 + 生产 compose 均通过 Production Validation |
| 文档一致性 | ✅ | Task 14 全量校准 |

## 2. 已知限制（Known Limitations）

| 项 | 说明 | 影响 |
|----|------|------|
| ~~前端 tsc 硬门禁（P1-6）~~ | **已 RESOLVED（Task 19）**：`tsc -b` 0 errors，CI frontend job 已恢复显式 TypeScript typecheck + `npm run build` 硬门禁 | — |
| growth course_detail（P1-3） | 课程表未落库，生产返回 None | 低（成长模块主链路不受影响） |
| 前端组件级测试缺失（P2-3） | 仅 utils 有 vitest | 低 |
| Seed 手动执行（P2-4） | 未集成进迁移流程 | 低（compose 启动命令已含 seed） |
| AI Sales Agent | 未实现（文档标注 Planned） | 不阻塞本期发布 |

## 3. 剩余 P0 / P1 / P2

- **P0**：无
- **P1**：P1-3（course_detail Demo Only）；~~P1-6（前端 tsc 硬门禁）~~ **RESOLVED**
- **P2**：P2-1（CSRF）、P2-2（Demo 401）、P2-3（组件测试）、P2-4（seed 集成）

## 4. Verified Facts（当前已验证事实）

```
Real PostgreSQL + pgvector:  PASS
Real Redis:                 PASS
Real DashScope / Qwen:      PASS
Real AI Smoke:              8/8 PASS
Playwright:                 Stage 1 PASS, Stage 2 PASS (11/11)
Production Validation:      PASS
Known:                      Frontend TypeScript hard gate still pending (P1-6)
```

## 5. 发布判定

| 等级 | 说明 | 当前 |
|------|------|------|
| NOT READY | 核心链路未验证 | — |
| READY FOR INTERNAL DEMO | 可演示 | — |
| **READY FOR INTERNAL PILOT** | 内部试点：真实环境核心链路全验证，剩余项为低风险改进 | ✅ **当前状态** |
| PRODUCTION READY | 生产上线：需完成 P1/P2 收敛、生产 Secret 管理、安全加固复审 | 未达到 |

> 进入 PRODUCTION READY 前必须：① 恢复前端 tsc 硬门禁；② 收敛 P1/P2；
> ③ 生产部署演练（`scripts/deploy.sh` + `docker-compose.prod.yml`）；④ 安全复审。
