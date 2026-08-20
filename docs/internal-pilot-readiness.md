# Internal Pilot Readiness — 正式试点前检查表（RDY 阶段5）

> 文档基线：随 RDY（Internal Pilot Readiness Final Prep）增量维护。
> 状态标记：**READY** = 已验证可进入试点；**BLOCKED** = 必须解决后才能试点；
> **EXTERNAL DEPENDENCY / ACCEPTED RISK** = 依赖外部资源或已记录风险，不伪装为 READY。
> 验证证据一律来自 GitHub Actions 云端结果（100% Cloud-only）。

---

## 1. 代码与发布基线

| 项目 | 状态 | 证据 |
|------|------|------|
| 代码版本 | READY | backend/pyproject.toml `0.1.0`；frontend package.json `0.1.0`；README 一致 |
| Git HEAD（Current main） | READY | main 最新提交链（RDY 完成后确认 `main == origin/main`） |
| Release Decision | READY | **PRODUCTION CANDIDATE**（Task 42 + ULTIMATE/HF2 全仓库统一；不提前宣布 PRODUCTION READY） |
| 文档基线 | READY | project-status 顶部 Documentation Freeze 标记；历史记录保留 |

## 2. 数据库与迁移

| 项目 | 状态 | 证据 |
|------|------|------|
| PostgreSQL 16 + pgvector | READY | docker-compose.prod.yml（pgvector/pgvector:pg16）；CI/PG 集成全绿 |
| Alembic 迁移到 head | READY | docker-compose.prod.yml backend command 自动 `alembic upgrade head`；production-validation L100 验证 |
| 迁移 head | READY | 0011_message_finish_reason（conversations/messages.finish_reason） |
| seed 幂等 | READY | test_seed_idempotency + test_e2e_seed_idempotency（首次 1 条、二次不重复；3 文档/9 chunks） |
| Redis | READY | docker-compose.prod.yml（redis:7-alpine，AOF）；Redis Multi-instance workflow（Task 40）✅ |
| 云托管备份 / 多地域灾备 / Redis HA | EXTERNAL DEPENDENCY | Accepted Risk（正式生产依赖外部对象存储/托管服务，Pilot 用 docker volume + 备份 workflow） |

## 3. 试点数据（Pilot Dataset）

| 项目 | 状态 | 证据 |
|------|------|------|
| 演示 AGENT（13800138000） | READY | seed.py（AGENT/浦东团队）；Pilot GF seed.agent_user PASS |
| 试点客户（5 个，脱敏） | READY | seed.py PILOT_CUSTOMERS（陈/刘/周/赵/孙，全部 assigned_to=AGENT 同组织；tags 标识 PILOT / COMPLIANCE_RISK / OBJECTION） |
| 客户互动/跟进 | READY | seed_pilot_customers 每个客户 1 互动 + 1 跟进；Pilot GF PASS |
| 产品知识库 | READY | e2e_seed_knowledge：3 文档 / 9 chunks / embedding 1536 维；metadata dataset_tag=E2E_TEST/PILOT |
| 合规高风险案例 | READY | 赵先生（返佣/承诺收益诉求，tags=COMPLIANCE_RISK）→ Compliance RED 演练 |
| 常见异议案例 | READY | 孙女士（理赔时效/线上投保疑虑，tags=OBJECTION）+ 知识库《销售合规与常见异议指南》 |
| 训练场景 | READY | seed_training_scenarios（23 个）；Training/Growth 数据连续（Pilot GF PASS） |
| 外部试点数据注入（正式试点） | EXTERNAL DEPENDENCY | 模式 B：受控渠道注入（不进 Git）；当前 A：Synthetic 可复现 |

## 4. 凭据与 Secrets

| 项目 | 状态 | 证据 |
|------|------|------|
| E2E Test Credential（CI-only） | READY | global-setup.ts 默认 888888 + `E2E_TEST_PASSWORD` env 覆盖（仅云端测试） |
| Demo Credential | READY | seed.py `AZB_DEMO_PASSWORD` 注入（默认 888888 仅 CI/Demo） |
| **Pilot Credential（正式试点）** | **BLOCKED 前置** | 试点部署时必须 `AZB_DEMO_PASSWORD` 注入强密码（Secret/env），**禁止沿用 888888**；seed 后轮换 |
| Production Secrets | READY | AZB_AI_API_KEY / AZB_AI_BASE_URL / AZB_AI_MODEL / AZB_AI_EMBEDDING_MODEL 从 GitHub Secrets 注入（pilot-golden-flow / real-ai-layer-c） |
| 无 secret 入库 | READY | secret scan CLEAN（无真实密码/API key/PAT/JWT/DB 密码进 Git） |

## 5. Real AI

| 项目 | 状态 | 证据 |
|------|------|------|
| Provider（DashScope/Qwen） | READY | pilot-golden-flow 真实 AI 27/27 PASS（qwen + text-embedding-v3） |
| Product QA SSE | READY | Pilot GF RAG hit/citation PASS；Layer C：TTFB p50=542ms / total p50=546ms（0/3 error） |
| Script Generation | READY | Pilot GF Agent 话术生成 + compliance=GREEN PASS；Layer C：total p50=6,324ms（0/3 error） |
| Sales Agent GF | READY | Pilot GF 8 事件/rag_status=ALLOW/citations=3/compliance=GREEN PASS；Layer C：total p50=28.8s（延迟分解见 performance-real-ai.md：话术生成占 ~79%，RAG ~3%） |
| 无 Mock fallback | READY | production 环境（DEMO_MODE=false）AI 缺 Key 时报错不静默降级（README/Gateway） |
| REFUSE 无依据 | READY | product_type=量子保险 → results=0 refuse=True（Task 17B 边界） |

## 6. 权限与合规

| 项目 | 状态 | 证据 |
|------|------|------|
| P0-1 assigned 隔离（生产 AGENT） | READY | can_access_customer 同源；Pilot GF perm.* PASS + E2E Pilot-2（200/404） |
| Demo 用户不绕过权限 | READY | DataPermissionChecker `settings.DEMO_MODE and user.demo_mode`（ULTIMATE Pilot 修复 + 回归测试） |
| RAG 权限（org/allowed_roles） | READY | chunk metadata 携带 org/allowed_roles；越权不可见 |
| Compliance 检查 | READY | Agent/脚本真实 check_compliance（RED 拦截语义）；赵先生高风险案例可演练 |

## 7. 部署与环境

| 项目 | 状态 | 证据 |
|------|------|------|
| docker-compose.prod.yml | READY | PG16+pgvector / Redis7 / backend（migration+seed+uvicorn 4 workers）/ frontend；健康检查 ready |
| .env.production 模板 | READY | AZB_TRUST_PROXY=false / AZB_DEMO_PASSWORD 必改 / AI/RAG/DB/JWT 占位（RDY 阶段4 补齐） |
| .env.example | READY | 新增 TRUST_PROXY / DEMO_PASSWORD 说明 |
| Production-like 启动 | READY | production-validation ✅（DEMO_MODE=false，无 Mock fallback） |
| frontend build | READY | tsc hard gate + `npm run build`（frontend-typecheck / production-validation） |
| Observability | READY | 结构化日志 + request_id 链路（Audit Log 落库 Task 37/37b RESOLVED） |
| 外部告警平台 | EXTERNAL DEPENDENCY | Accepted Risk（正式生产接入监控告警） |
| 渗透测试 | EXTERNAL DEPENDENCY | Accepted Risk（上线前外部渗透） |
| 上传病毒扫描 | EXTERNAL DEPENDENCY | Accepted Risk（正式生产对象存储/杀毒） |
| localStorage token / refresh 吊销 | EXTERNAL DEPENDENCY | Accepted Risk（迁移内存 token + refresh revoke 评估） |

## 8. 运维

| 项目 | 状态 | 证据 |
|------|------|------|
| Backup/Restore | READY（Pilot 级） | Task 38 Cloud Verified（docker volume + workflow）；正式生产对象存储/多地域为外部依赖 |
| 滚动发布 | EXTERNAL DEPENDENCY | Accepted Risk（正式生产发布流程） |
| Rollback contact | EXTERNAL DEPENDENCY | 试点需指定运维负责人与回滚预案（见下） |
| Support owner | EXTERNAL DEPENDENCY | 试点期间需指定业务/技术支持 owner |

---

## 9. 试点前置必办（进入试点前必须完成）

1. **Pilot 凭据轮换**：seed 前设 `AZB_DEMO_PASSWORD=<强密码>`（Secret 注入），seed 后停用未使用演示账号 —— 当前 BLOCKED 前置于此。
2. 试点业务数据（真实脱敏数据）通过 External Pilot Data 通道注入（不进 Git）。
3. 指定 rollback contact 与 support owner。
4. 正式试点环境 Secrets：AI Key / DB 密码 / JWT 强密钥全部就位（当前模板占位）。

## 10. Known Limitations（如实记录）

- KB 仅 3 文档 9 chunks：Agent 自由召回场景下 RRF 分数恒高，语义 REFUSE 依赖 product_type 边界（Task 17B），不依赖分数阈值。
- Sales Agent 为进程内会话（无长期记忆）；正式试点不建议要求跨会话上下文。
- 真实 AI 性能基准为云环境测量（非生产 SLA），见 `docs/performance-real-ai.md`。
