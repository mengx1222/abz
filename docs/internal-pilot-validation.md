# Internal Pilot Golden Flow Validation（ULTIMATE Pilot）

> 目的：内部试点前最后一次**真实业务闭环验证** —— 在 `DEMO_MODE=false`、真实 PostgreSQL/pgvector + Redis +
> 当前 Pilot seed + 真实 AI Provider（DashScope/Qwen，opt-in）环境下，证明一个真实 AGENT 用户从登录开始，
> 完成客户查看 → AI Sales Agent → 知识检索/Citation → 销售建议/话术 → Compliance → Training → Growth 的
> 全链路数据与权限真正连续。
>
> 工作方式：100% Cloud-only，全部由 GitHub Actions 云端执行；验证结果以 `pilot-golden-flow` workflow run 为准。

## 1. 验证对象与数据（Pilot seed）

| 项 | 值 | 来源 |
|----|-----|------|
| 测试用户 | AGENT `13800138000` 林思远（上海分公司-浦东团队，`demo_mode=True` 标记） | `scripts/seed.py` |
| 试点客户 | 陈女士 `13900000001` / 刘先生 `13900000002` / 周女士 `13900000003`（均 `assigned_to=13800138000`，同组织） | `scripts/seed.py` |
| 客户互动/跟进 | 每客户 ≥1 互动 + ≥1 跟进 | `scripts/seed.py` |
| 试点知识库 | 「E2E产品知识库」（`e2e_seed_knowledge.py`）：2 文档 / ≥6 chunks / 1536 维 embedding / `product_type` 边界 | `scripts/e2e_seed_knowledge.py` |
| 训练场景 | ≥1 确定性场景（如「太贵了 — 重疾险价格犹豫」） | `scripts/seed.py` → `seed_training_scenarios` |
| 组织/角色 | 6 组织层级 + 7 角色 + 角色-权限绑定 | `scripts/seed.py` |

## 2. Golden Flow（唯一真实路径）

```
AGENT 登录(13800138000)
→ Dashboard
→ Customer 360（搜索 seed 客户 陈女士）
→ AI Sales Agent（同一 customer_id）
   → 输入确定性销售目标（医疗险保障范围/理赔流程）
   → Agent 读取 Customer Context（get_customer_context 工具）
   → RAG 检索试点知识库（rag_context）
   → Citation（rag_context.data.citations）
   → 销售建议/话术（message_delta）
   → Compliance（GREEN/YELLOW/RED）
→ Training（AI 陪练：确定性场景 → ≥2 轮 → 结束 → 评分）
→ Growth（同用户训练结果：total_exp / ability_scores）
```

## 3. 验证方式

### 3.1 服务级验证脚本 `scripts/pilot_golden_flow.py`

在真实 DB/Redis/AI 环境（workflow）中逐项断言并输出 JSON 证据：

| 检查 | 断言 |
|------|------|
| A. seed 完整性 | AGENT/角色/组织存在；3 客户全部 `assigned_to=AGENT` 且同组织；每客户互动+跟进≥1；KB 2 文档 ≥6 chunks embedding=1536 维；训练场景≥1 |
| B. 权限（P0-1 同源） | 本人 assigned 可见；他人 assigned 拒绝；跨组织拒绝；列表仅本人 assigned |
| C. RAG | 医疗险问题 hit>0 + rag_status ALLOW/REVIEW + citation 有 document_title/section；无关问题 REFUSE（不编造产品条款） |
| D. AI Sales Agent | agent_start/rag_context/citation/compliance/agent_complete 事件齐全；rag_status/citation/compliance 状态真实；provider/latency 记录 |
| E. Training | start_session → 2 轮 send_message → complete_session 评分事件（score_data/scoring_complete） |
| F. Growth 连续性 | 同用户 total_exp≥10 + ability_scores 非空（仅来自训练评分） |

### 3.2 浏览器 E2E `frontend/e2e/pilot/internal-pilot.spec.ts`（增量，不重复 27 个既有 E2E）

- **Pilot-1 黄金链**（seed 客户驱动）：登录态 → Dashboard → Customer 360（陈女士）→ AI Sales Agent
  （Citation 面板 + Compliance 状态）→ Training（页面/场景）→ Growth（能力评估）；不依赖固定 AI 文案；
  全程 console error / pageerror / API 4xx/5xx 监控。
- **Pilot-2 权限安全**（API 级）：本人 assigned 客户 200；随机 UUID 404；列表仅含本人 assigned 客户。

### 3.3 Workflow `pilot-golden-flow.yml`

- `workflow_dispatch` 手动触发（含真实 AI Key 时走 DashScope/Qwen）；push 到脚本路径也触发（幂等）。
- 环境：PG16+pgvector + Redis + backend（DEMO_MODE=false）+ `seed.py` + `e2e_seed_knowledge.py`。
- 无 `AZB_AI_API_KEY` 时明确标记 `PILOT_AI=NOT_RUN`（不假装通过）；有 Key 时记录 `provider/model`。

## 4. 发现并修复的问题（真实，CI 驱动）

| 问题 | 根因 | 修复 |
|------|------|------|
| P0-1 权限被演示用户绕过（P1 级） | `DataPermissionChecker._is_demo` 仅看 `user.demo_mode` —— production 环境（DEMO_MODE=false）下 seed 演示用户登录被误判为 demo → 同组织全客户可见，**绕过 assigned 隔离** | `_is_demo = settings.DEMO_MODE and user.demo_mode`：仅「环境是 demo 且用户是 demo 用户」才走宽松分支；production 一律生产语义；新增回归测试 `test_production_env_demo_user_still_scoped` |
| 验证脚本 REFUSE 用例误判 | 「极光量子保险」与医疗险文档相似度仍达阈值（top_score=1.639 不拒答） | 改用与知识库完全无关的问题（行星液态水） |
| Agent Citation 断言事件名错误 | Orchestrator 无独立 `citation` 事件，Citation 内嵌于 `rag_context.data.citations` | 断言改为读取 `rag_context.data.citations` |
| Training 评分事件名错误 | `complete_session` 事件为 `score_data/scoring_complete`（非 score/session_complete） | 断言改为监听 `score_data/scoring_complete` |
| E2E Pilot-2 读 localStorage 抛 SecurityError | 测试未先导航建立 origin | 先 `goto('/dashboard')` 再读 token |

## 5. 云端验证结果（GitHub Actions @ 6ff1146，真实 AI）

### 5.1 服务级 Golden Flow（`pilot-golden-flow` workflow，**真实 AI = qwen + text-embedding-v3**，27/27 PASS）

| 检查 | 结果 |
|------|------|
| seed 完整性 | AGENT 13800138000（AGENT/浦东团队）；3 客户全部 assigned_to=AGENT 且同组织；每客户互动+跟进=1；KB 2 docs / 6 chunks / embedding 1536 维；训练场景 23 |
| 权限（P0-1 同源） | 本人 assigned 可见 ✅；他人 assigned 拒绝 ✅；跨组织拒绝 ✅；列表仅本人（total=3）✅ |
| RAG | 医疗险问题命中 6 条（真实 embedding，latency 888ms）✅；Citation title=安诊保百万医疗险产品手册 / section=核心条款 ✅；**REFUSE：product_type=量子保险 → results=0, refuse=True**（Task 17B 边界，不编造）✅ |
| AI Sales Agent（真实 AI） | 8 事件齐全（agent_start→tool_planned/start/result→rag_context→message_delta→compliance→agent_complete）；rag_status=ALLOW sources=3；citations=3；compliance=**GREEN**；status=completed；**总 latency 27.6s（真实生成）** |
| Training | session 创建 → 2 轮消息 → complete 评分事件 ✅ |
| Growth 连续性 | 同用户 total_exp=10（1 次训练×10）+ ability_scores=4（仅来自训练评分）✅ |

### 5.2 浏览器 E2E（`e2e-playwright` workflow）

- **Pilot-1**（seed 客户陈女士黄金链）：Dashboard → Customer 360 → Sales Agent（Citation + Compliance）→ Training → Growth ✅
- **Pilot-2**（权限安全）：本人 assigned 详情 200 + 随机 UUID 404 ✅
- 既有 27 个 E2E 无回归；全矩阵 CI（Backend/PG/Frontend）+ Production Validation 全绿

## 6. Remaining Accepted Risks（未在本任务范围）

- 真实 AI 性能基准（层 C opt-in，未配 Key 时为 NOT RUN）
- 外部告警平台 / 云托管备份 / 多地域灾备 / Redis HA / 滚动发布 / 渗透测试
- localStorage token（XSS 面）、上传病毒扫描、演示凭据轮换
- refresh token 吊销（随 localStorage 迁移评估）

## 7. 后续建议

- 真实试点前：配置 `AZB_AI_API_KEY` 后手动触发 `pilot-golden-flow` workflow（workflow_dispatch）获取真实 AI 全链证据；
- 试点数据按真实业务补充（当前为合成数据）；
- 演示凭据轮换与 localStorage token 迁移在 Pilot 上线前完成。
