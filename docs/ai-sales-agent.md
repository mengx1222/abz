# AI Sales Agent（后端第一阶段）

> 状态：**Agent Core implemented / validated**（Task 27，HEAD=f93ac42 全绿：Backend 291/43、backend-pg 43 passed、Prod ✅）
> 范围：后端 Orchestrator + Tool Registry + SSE Contract + 测试矩阵 + 真实 AI Smoke。
> **未做（后续任务）**：前端 Agent UI（Task 28）、长期记忆/复杂 memory、复杂多 Agent 协作、
> 自动对外销售动作（发送消息/下单/投保等）——Agent 当前只生成建议/结果，对客动作由人工触发。

## 1. 架构

```
POST /api/v1/ai/sales-agent/chat (SSE)
        │
        ▼
SalesAgentService (Orchestrator, 确定性黄金链编排)
        │  仅安全状态说明（tool_planned），不泄露 CoT / 内部 prompt
        ▼
ToolRegistry（白名单 5 工具：name / input schema / 权限 / 超时 / 错误类型）
        │  携带当前 User（RBAC / Organization Scope 由底层 Service 再次执行）
        ▼
CustomerService / RAGPipeline / ScriptService / ComplianceEngine（复用既有能力）
        │
        ▼
AIGateway → Provider（Qwen / DeepSeek / OpenAI 兼容；DEMO_MODE=true 时为 Mock）
```

核心原则：
- 工具是 Agent 调用业务能力的**唯一入口**（白名单），禁止 LLM 自由生成函数名/URL
- Agent 不直接访问 ORM 做业务查询、不直接调用 Provider SDK、不自己实现权限过滤
- 所有业务工具复用现有 Repository / Service / RBAC 逻辑（Task 17B 权限不因 Agent 绕过）

## 2. 工具白名单（本阶段 5 个）

| 工具 | 复用能力 | 权限要求 | 超时 |
|------|---------|---------|------|
| `get_customer_context` | `CustomerService.get_customer`（IDOR 防护 + DataPermissionChecker） | customer:read | 15s |
| `get_customer_activity` | 同 Customer 详情的 interactions/followups 摘要 | customer:read | 15s |
| `search_product_knowledge` | `RAGPipeline.query` + Confidence Gate + Citation | rag:query | 30s |
| `generate_sales_script` | `ScriptService.generate_scripts`（RAG+Confidence+Compliance+持久化） | script:generate | 60s |
| `check_compliance` | `compliance_service.check_compliance` | 无 | 5s |

- **Training Service** 已有 start/send_message 能力 → 设计为后续 tool（本阶段不做复杂训练 Agent）。
- `get_customer_activity` 复用既有 Customer 数据（不重建 CRM）。

## 3. 编排与安全顺序（黄金链）

```
sanitize（Prompt Injection HIGH → 拒答，零工具调用）
  → get_customer_context（失败/越权 → NOT_FOUND 明确终止）
  → get_customer_activity
  → search_product_knowledge（RAG；REFUSE → 跳过话术生成，不编造）
  → generate_sales_script（复用 ScriptService 内部完整链）
  → check_compliance（最终校验；RED 结构化透传，阻止标记可用）
  → LLM 汇总（仅工具结果摘要；流式 message_delta）→ agent_complete
```

- 不能出现"AI 先自由生成，最后只打 compliance 标签"：Compliance 由真实 engine 对生成文本执行，
  RED 阻止直接使用、YELLOW 需人工确认、GREEN 正常通过。
- RAG `REFUSE` 时 Agent **不得**调用模型编造产品条款；拒答状态结构化返回前端。

## 4. 输入 / 输出 Contract

### 请求（POST /api/v1/ai/sales-agent/chat）

```json
{
  "customer_id": "uuid",
  "message": "客户想了解医疗险的保障范围",
  "product_type": "医疗险",      // 可选
  "sales_stage": "needs_analysis", // 可选
  "session_id": "uuid"             // 可选，服务端最小上下文管理
}
```

### SSE 事件流（`data: {json}`，与既有 ai.py 格式一致）

| 事件 | 说明 |
|------|------|
| `agent_start` | request_id / session_id / customer_id |
| `tool_planned` | 安全状态说明（"正在查询客户信息"等），非思维链 |
| `tool_start` / `tool_result` | 工具执行（含 ok / error_type / duration_ms / summary） |
| `rag_context` | rag_status（ALLOW/REVIEW/REFUSE/ERROR）+ confidence + citations |
| `message_delta` | 最终回复流式输出 |
| `compliance` | 合规结果（status/score/issues） |
| `agent_complete` | status（completed/refused/error）+ message + tool_sequence + citations + compliance |
| `error` | 错误（message + error_type） |

安全：不输出/持久化模型隐藏推理过程、chain-of-thought、内部 prompt、系统密钥。

## 5. 权限 / 安全

- 所有工具携带当前 User，底层 Service / RAG **再次执行** RBAC / Organization Scope 检查
  （Task 17B 的 RAG role + org 过滤、Customer IDOR 防护均不因 Agent 绕过）
- 跨组织客户 → `NOT_FOUND`（不泄露存在性）；无权限工具调用 → 明确拒绝结果（非空白/fallback）
- Prompt Injection（HIGH）→ 拒答；MEDIUM 消毒后继续
- RAG REFUSE 后禁止通用模型知识编造产品事实
- Provider 失败（429/401/超时）→ 确定错误模型，**禁止 fallback Mock**
- 隐私：发送给模型的客户字段为最小化集合（name/age/gender/customer_type/stage/
  intention_level/product_type/tags），**不含 phone / notes / 身份证 / 银行卡**
- 日志只记录 request_id / user_id / provider / model / latency / tool_sequence / status / token usage

## 6. 错误模型

`ToolResult{ok, error_type, message}`；error_type ∈
`PERMISSION_DENIED / NOT_FOUND / TOOL_TIMEOUT / PROVIDER_ERROR / INVALID_ARGS / INTERNAL`。
- 工具超时（asyncio.wait_for）→ TOOL_TIMEOUT
- 未知工具（非白名单）→ INVALID_ARGS
- 生产模式 `DEMO_MODE=false` 下 AI Provider 缺凭据 → 初始化即抛错（不静默降级）

## 7. 成本 / 安全边界

- `MAX_TOOL_CALLS = 8`（黄金链固定 4-5，余量防循环）
- `MAX_TOOL_LOOP = 3`（连续相同工具调用检测 → AgentLoopError 安全终止）
- 单工具超时 5-60s（按工具）；RAG context 4000 字符上限
- 内存 session（进程内）：保留最近 8 条消息 + customer/product/stage。
  **限制**：多实例部署下 session 不共享（当前单实例开发/试点可接受，见 release-readiness）

## 8. 测试矩阵

- **Unit（12 用例，SQLite + DEMO_MODE=false + mock provider + 最底层 FakePipeline）**：
  白名单/未知工具/超时、黄金链事件顺序、无产品类型跳 RAG、客户不存在/越权 IDOR、
  注入拒答、RAG REFUSE 跳话术、Compliance RED 透传、Provider 失败不 fallback、
  循环/预算防护、Session 连续性、Script REFUSE 透传
- **PG + pgvector（5 用例，真实 PG）**：RAG 工具角色+组织双权限过滤（citation 不泄漏）、
  无权 KB → REFUSE、完整黄金链、跨组织客户 IDOR、注入全链拒答
- **真实 AI Smoke（phase10，opt-in / Secrets）**：真实登录 → 客户 → RAG → Script →
  Compliance → SSE 事件流 → agent_complete（workflow_dispatch / REAL_AI_SMOKE_TEST=true）

## 9. 限制与后续

- 前端 Agent UI → **Task 28**
- 长期记忆 / 复杂会话管理（当前内存 session 单实例）
- Training tool、复杂自动化（多 Agent / 自动执行销售动作）→ 未来规划
- Admin 管理 API Demo-only 等既有 P 系列问题与本模块无关
