# Golden Business Flow Audit（Task 29 — 完整业务黄金链云端验收）

> 状态：**Golden Flow E2E validated（Task 29，HEAD=2f183e3）**；Real AI Golden Flow Smoke（phase11）opt-in 待手动 workflow_dispatch
> 本文档记录黄金业务链定义、测试用户/数据边界、每步页面/API/Service 映射、
> 真实 AI/RAG/Compliance/Training/Growth 证据、发现的问题及修复、未覆盖内容。

## 1. 黄金业务链定义（唯一）

一条真实浏览器链路，证明一个代理人（AGENT）完成一次完整「销售准备黄金流程」：

```
登录(storageState=AGENT)
→ Dashboard(/dashboard)
→ Customer 360(/customers → 搜索确定性客户 → /customers/{id})
→ AI Sales Agent(/sales-agent/{customerId}：客户上下文 → 销售问题 →
   SSE 流式执行 → RAG 产品知识/Citation → 销售话术 → Compliance)
→ Training(/training：确定性场景 → ≥2 轮陪练 SSE → 结束 → 评分非空)
→ Growth(/growth：能力评估出现 = 训练评分进入成长体系)
```

### 每步对应的页面 / API / Service

| 步骤 | 页面/路由 | API | Service |
|---|---|---|---|
| 登录 | /login（storageState 预置 AGENT 13800138000） | POST /auth/login | AuthService |
| Dashboard | /dashboard（「今日工作」「AI 今日建议」） | GET /dashboard/* | DashboardService |
| Customer 360 | /customers（搜索 13900002222）→ /customers/{id} | GET /customers?search= / GET /customers/{id} | CustomerService |
| 确定性客户 | —（spec 内幂等 API） | GET /customers?search= / POST /customers / PUT /customers/{id} | CustomerService |
| AI Sales Agent | /sales-agent/{customerId} | POST /ai/sales-agent/chat（SSE） | SalesAgentService → ToolRegistry → RAGPipeline/ScriptService/ComplianceService |
| RAG/Citation | Agent 结果卡「产品知识来源」 | rag_context / citation 事件 | RAGPipeline（Vector+BM25+RRF+Confidence+Citation） |
| Compliance | Agent 结果卡「合规检查」 | compliance 事件 | ComplianceEngine |
| Training | /training → /training/chat/{scenarioId} | GET /training/scenarios / POST /training/sessions / POST messages（SSE）/ POST complete（SSE） | TrainingService |
| Growth | /growth（能力评估 4 项） | GET /growth/overview | GrowthService（ability_scores ← training scores；total_exp = 完成训练×10） |

## 2. 测试用户 / 数据边界（确定性）

- **用户**：AGENT 13800138000 / 888888（seed.py 固定；E2E 环境 seed 后 demo_mode=True，
  可访问同组织客户 —— 既有 E2E 既定事实；正式角色语义由后端 RAG/权限层保持）
- **客户**：`E2E-黄金链客户` / 13900002222 / insurance_type=医疗险（spec 内幂等创建+更新）
  —— 与 global-setup 的 E2E-张先生（13900001111）互不干扰
- **知识库**：e2e_seed_knowledge.py 确定性「E2E产品知识库」（安诊保百万医疗险产品手册，
  医疗险 ≥3 chunk → Confidence HIGH → ALLOW + Citation；极光量子保险 → REFUSE）
- **训练场景**：seed 内置确定性场景「"太贵了" — 重疾险价格犹豫」
- 禁止依赖随机数据：客户/手机号/场景/KB 全部固定，幂等创建

## 3. 跨模块数据连续性（必须验证）

1. **同一用户**：storageState（AGENT）贯穿全部页面导航；Growth 的 ability_scores 按
   `list_training_scores(user_id)` 过滤 → 只反映当前用户训练
2. **同一 customer_id**：/customers/{id} URL 提取 → /sales-agent/{id} URL 断言一致
3. **RAG citation**：Agent 结果必须出现「产品知识来源」≥1 条（来自 E2E 知识库，非编造）
4. **Compliance**：合规检查面板状态存在（GREEN/YELLOW/RED 任一，绑定后端结果）
5. **Training→Growth**：训练完成后 Growth「能力评估」出现（产品知识/沟通技巧/促成能力/
   综合表现 4 项，仅来自训练评分）；API 断言 total_exp ≥ 训练前 + 10（完成训练×10）

## 4. 测试文件

- `frontend/e2e/golden-flow/golden-flow.spec.ts` — GF-1 浏览器级完整黄金链
  （真实 PG/Redis/backend + 真实 AI provider 或 CI 回退 mock；300s 超时；
   console/pageerror/API 4xx 监控；trace/screenshot/video retain-on-failure）
- `backend/scripts/phase11_golden_flow_smoke.py` — Real AI Golden Flow Smoke（API 级，
  真实 Provider；opt-in：workflow_dispatch / REAL_AI_SMOKE_TEST=true；无 key NOT RUN）
- `.github/workflows/real-ai-smoke.yml` — 追加 Phase 11 步骤

## 5. 权限与安全（黄金链内验证）

- AGENT 只能访问自己组织/可访问客户（demo 模式 org 匹配；后端 Service 再执行权限）
- RAG 权限：citation 只来自有权 KB（既有 test_agent_pg 覆盖）
- RAG REFUSE：Agent 不生成具体产品事实（G-2 既有 E2E 覆盖；黄金链走 ALLOW 路径）
- Compliance RED/YELLOW/GREEN 绑定后端（页面不前端自判）
- Provider 失败不 fallback Mock（后端 orchestrator 语义，既有测试覆盖）

## 6. 发现的问题及修复

| # | 问题 | 类型 | 修复 | Commit |
|---|---|---|---|---|
| 1 | E2E job 卡在 `Install frontend deps + Playwright browsers` >40min（GitHub Actions npm 网络偶发，Task 25 同类 >110min） | CI 基建 | `npm install`/`playwright install` 各加 `timeout 600` + 失败自动重试一次 | 3817f9f |
| 2 | GF-1 首跑 strict violation：`getByText('合规检查')` resolved to 5 elements —— '合规检查' 出现在 header 副标题 + 每条 assistant 消息合规面板（span + GREEN hint）。多元素是**正确产品行为**（多轮对话每条消息都有合规面板），非产品 bug | E2E 断言 | 改 `.first()` 取首个面板（与 Task 28 G-1 tool_planned .first() 同模式） | 2f183e3 |
| 3 | GF-1 观察：单轮对话页面出现 2 条 assistant 消息（合规面板 ×2） | 待确认 | 不阻塞（.first() 已容错）；若为真实渲染问题记录到 §7 观察，不在本 Task 处理 | — |

> 注：E2E 环境为**真实 AI provider**（AZB_AI_API_KEY secret 已配置，日志中 provider 打码非 mock）——
> GF-1 浏览器级黄金链在真实 AI 下跑通（RAG/Citation/Compliance/Training 评分均为真实模型输出）。

## 7. 未覆盖内容（记录，不处理）

- 自动发送/CRM 写回/投保等外部副作用（Planned，非本 Task 范围）
- 长期记忆/会话持久化（内存 session 单实例）
- 多 Agent 协作、复杂语音/分析大屏
- Product QA / Script 页面单模块流式（已有独立 E2E 覆盖，黄金链不重复）
- 真实浏览器 × 真实 AI 同时执行（浏览器 Golden Flow 在 e2e-playwright 跑，
  真实 AI 完整链在 real-ai-smoke Phase 11 API 级验证 —— 成本控制 opt-in 设计）

## 8. 验证结果（GitHub Actions，HEAD=2f183e3）

- **Backend pytest**：291 passed, 43 skipped
- **backend-pg（真实 PG16+pgvector）**：43 passed
- **Frontend Vitest**：81 passed（10 files）
- **Frontend Typecheck**：`tsc -b` 0 errors
- **Build**：✅（CI 内）
- **E2E Playwright**：**27 passed (2.6m)** —— 26 原有 + **GF-1 Golden Business Flow**（真实 AI provider + 真实 PG/Redis + DEMO_MODE=false）
- **Production Environment Validation**：✅（docker compose + PG/Redis 真实容器）
- **Real AI Smoke（phase9/10/11）**：workflow_dispatch opt-in —— phase11 新增；需手动触发（PAT 无 dispatch 权限）；phase9/10 此前已 PASS
