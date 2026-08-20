# Release Candidate Audit（Task 36 — Final Audit）

> 审计日期：2026-08-20
> 基线：main@`783cb61`（Task 35 全绿：Backend 296/48、PG 48、Vitest 107、E2E 27、Prod ✅）
> 方法：100% Cloud-only —— GitHub API 读取 199 个源码文件全文扫描 + 既有审计结论复核（Task 30-35），无本地 clone/测试
> 范围：Backend / Database / AI-RAG / Frontend / Security / Deployment 六域；只读审计，最小修复（仅必要）

---

## Git

- HEAD：`783cb61`（== origin/main）
- Version：**v0.1.0**（config.py / pyproject.toml / package.json / README 一致，Task 35 对齐）
- Backup：`backup/task-36-20260820-0804`
- CI：全绿（783cb61：CI ✅ + Prod ✅；E2E 27 passed 历史 ✅）

## Backend

**Status：PASS（Production Safe）**

| 检查项 | 结果 | 证据 |
|--------|------|------|
| 全部 router 生产路径 DB backed | ✅ | 各 service production 分支持久化；demo 分支全部 `settings.DEMO_MODE` 门控 |
| NotImplemented / 未实现路径 | ✅ 0 命中 | 全文扫描 `NotImplemented` 0 处 |
| Mock fallback（生产） | ✅ 无 | `effective_ai_provider` 仅 demo 强制 mock；Provider 失败 raise 不降级（Task 27/30/31 验证） |
| Silent failure / 异常吞掉 | ✅ 无新增 | 24 处 `except Exception` 逐一复核：rollback+raise / logger 记录 / 有意降级且有真实 fallback（如 customer_service JSON 解析失败 → 结构化分析兜底） |
| bare pass | ✅ 全部无害 | 12 处：type-hint helper / 有意分支（SYSTEM_ADMIN __ALL__）/ 脚本占位 |
| TODO 标注 | ⚠️ 4 处已知限制 | `ai/service.py` + `api/v1/ai.py`：AI 会话历史未持久化（P2 A2，Task 27/30 已记录）——product-qa 单次问答主链路不受影响，会话列表/详情生产返回空 |

## Frontend

**Status：PASS（Production Safe，2 个低优先级记录）**

| 检查项 | 结果 | 证据 |
|--------|------|------|
| TypeScript 硬门禁 | ✅ | `tsc -b` 0 errors（CI frontend job + frontend-typecheck + Docker 镜像构建 npm run build，Task 19/35） |
| console.log/debug | ✅ 0 命中 | 全文扫描 |
| @ts-ignore / eslint-disable | ✅ 0 命中 | 全文扫描 |
| API error / loading / empty / 权限 / 401 处理 | ✅ | api.ts 401 语义 + getErrorMessage 透传 + 页面 loading/error/empty + RoleGuard 角色守卫 + ErrorBoundary 全局（Task 24/28/32/33） |
| `any` 使用 | ⚠️ 5 处低优先级 | GrowthPage catch(e:any)×3 / communityService SSE data:any（SSE 事件松散类型）/ cn.test 测试产物；tsc 未启用 strict → 不阻断 |

## Database

**Status：PASS**

| 检查项 | 结果 | 证据 |
|--------|------|------|
| Migration 完整性 | ✅ | Alembic `0001_initial → 0009_kb_metadata` 线性无分支，head 正确（backend-pg + Prod 每轮 `alembic upgrade head` 验证） |
| 新字段迁移覆盖 | ✅ | 全部模型字段随 9 个迁移；无模型-迁移漂移（backend-pg 48 passed 含各表 DDL 校验） |
| FK / Cascade | ✅ | 组织树 FK + document→chunk/embedding CASCADE 无孤儿（Task 22 test_document_management） |
| Index / pgvector | ✅ | vector 索引 + 检索路径（Task 12/13/20） |
| Seed | ✅ | seed.py 幂等 + 权限绑定 await 修复（Task 35，3 回归用例） |

## AI/RAG

**Status：PASS（Task 17B 后能力保持）**

| 检查项 | 结果 | 证据 |
|--------|------|------|
| Real AI provider | ✅ | DashScope/Qwen，Real AI Smoke 8/8（phase9/10）+ GF-1 真实 AI E2E（Task 29） |
| Mock 不冒充生产 | ✅ | demo 强制 mock；生产无凭据抛错（Task 30/31） |
| Citation / Refusal / Permission filtering | ✅ | E2E G-1/G-2 + test_agent_pg（角色+组织双权限，不泄漏）+ 产品边界（Task 17B/29） |
| SSE | ✅ | Sales Agent SSE 事件流 + 安全状态说明（Task 27/28/29） |
| Prompt Injection | ✅ | sanitize + HIGH 拒答 + 全链测试（Task 27/30） |

## Security

**Status：PASS（无新发现；既有已收敛项全部保持）**

| 检查项 | 结果 |
|--------|------|
| JWT（Bearer HS256 + refresh） | ✅ 401/403 语义契约 + 防御测试 |
| CORS | ✅ 生产 FRONTEND_URL 白名单；demo `*` 为 ACCEPTED RISK（仅演示） |
| Security Headers | ✅ nosniff/X-Frame-Options DENY/CSP/HSTS（生产）+ 回归测试 |
| Rate Limit | ✅ 令牌桶（login 2/s、/ai/ 5/s）——**内存实现（P2 A1，多实例不共享）** |
| CSRF | ✅ 无攻击面（Bearer-only，Task 24/34 复核） |
| Secret 管理 | ✅ 仓库无真实 secret（仅 CHANGE_ME 模板）；CI 用 GitHub Secrets（AZB_AI_API_KEY 等） |
| 上传安全 | ✅ 大小限制 10MB + 413（Task 34）+ 写权限校验（Task 31 P1-1） |
| 越权/IDOR | ✅ test_permission_pg / test_agent_pg / E2E 覆盖 |

## Deployment

**Status：PASS（PILOT 级）**

| 检查项 | 结果 |
|--------|------|
| Docker 多阶段构建 | ✅ backend（curl healthcheck 就绪）/ frontend（nginx + npm run build） |
| docker-compose.prod.yml | ✅ 4 服务 + healthcheck + depends_on service_healthy + 持久卷 + 资源限制 |
| Migration 启动自动执行 | ✅ `alembic upgrade head && python -m scripts.seed && uvicorn` |
| 环境变量 | ✅ AZB_ 前缀统一；.env.production 模板 + 部署路径文档化（Task 35） |
| CI pipeline | ✅ backend/backend-pg/e2e/prod/typecheck 全矩阵；E2E 27 passed |
| 多实例/滚动部署 | ⚠️ 未实现（P2 A1/A5：内存限流/会话 + 单容器部署） |

## Final Decision

### **READY FOR INTERNAL PILOT ONLY**

（维持 Task 30 判定；未达 **PRODUCTION CANDIDATE**）

**依据**：六域审计全部通过（无新增生产阻断 bug、无安全漏洞、无 mock 冒充、无 silent failure、迁移/部署/CI 一致）。但距离 PRODUCTION CANDIDATE 仍有以下**明确差距**（全部为既有已记录项，非本次新发现）：

1. **P1 B1**：数据库备份系统 NOT IMPLEMENTED（部署可恢复性）
2. **P1 B2**：Audit Log 未 DB 持久化（仅 structlog，合规审计需求）
3. **P2**：AI 会话历史未持久化（product-qa 生产返回空会话）
4. **P2**：Redis no-op 静默降级 + rate limit/agent session 内存实现（多实例不共享）
5. **P2**：token localStorage（XSS 面）、环境 badge 硬编码
6. **记录**：demo 用户默认凭据（888888）未轮换（PRODUCTION READY 前置）
7. **记录**：无外部监控告警（Prometheus/Grafana）、无性能基准、无滚动部署（P2 A4/A5/K1）
8. **记录（卫生）**：23 个源文件为 CRLF 行尾（混合行尾，历史无影响；建议后续引入 .gitattributes 规范化）

**进入 PRODUCTION CANDIDATE 前必须**：① B1 备份系统；② B2 Audit Log 落库；③ 监控告警；④ 多实例（Redis 化限流/会话）+ 滚动发布；⑤ 性能基准；⑥ 演示凭据轮换；⑦ 安全复审/渗透测试（与 Task 30 §13 一致）。

---

## 附：Phase 3 最小修复决策

本次审计**未发现需要立即修复的新问题**（文档错误/CI 配置错误/生产阻断 bug/安全漏洞均为 0 新增）——前序任务（Task 30-35）已收敛对应类别。故无 fix/test commit；仅提交审计文档 + 状态文档同步。`ai.py` 会话 TODO 属功能缺口（会话持久化 = 新功能），按任务约束不开发。
