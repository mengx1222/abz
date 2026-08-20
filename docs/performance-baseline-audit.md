# Performance Baseline Audit（Task 41 · Benchmark + Capacity Baseline）

> 状态：**Baseline 定义完成 → 云端 benchmark 执行中**
> 更新：2026-08-20

---

## Current Metrics（现状可观测信号，均有日志载体）

| 指标 | 载体 | 说明 |
|---|---|---|
| API latency | `RequestLoggingMiddleware` `request` 事件 `duration_ms` | 每个请求（跳过 /health） |
| API error | `request` 事件 `error_code=HTTP_4XX/5XX`（Task 39） | 分类计数 |
| AI latency/tokens | openai_provider `openai_chat_success`（latency_ms/prompt_tokens/completion_tokens） | chat/stream/embed |
| AI error | `openai_*_error`（error_code 401/403/429/5xx/连接，Task 39） | 无 body |
| RAG retrieval | `rag_query_result`/`rag_query_no_relevant_results`（retrieval_count/latency_ms，Task 39） | 检索耗时 |
| RAG refusal | `rag_prompt_injection_blocked`/`rag_confidence_none_refuse` | 拒答事件 |
| SSE | `product_qa_chat_start`/`sales_agent_chat_start`（user_id/session_id） | 起止事件 |
| DB/Redis health | `/ready` checks（2s timeout） | 连接状态 |
| 进程计数器 | `AppMetrics`（request/error/uptime） | /health/detail |

## Unknowns（未测量，不伪造）

- **无任何 QPS/SLA 数据**：当前只有单请求 latency_ms，无并发/吞吐/容量测量。
- 无 p50/p95 分位统计（日志未聚合）。
- 无 pgvector 查询单独耗时（RAG latency_ms 是整体；向量 vs BM25 vs RRF 分项未知）。
- 无 SSE time-to-first-event（TTFE）测量。
- 无 Agent tool chain 分项耗时（总 latency 可测，tool 级未分）。
- 无 DB connection pool 利用率、Redis P99、CPU/Memory 数据。
- Real AI provider latency 仅生产日志有，无受控 benchmark。

## Potential Bottlenecks（假设，待 benchmark 验证）

1. **Redis 每操作短生命周期 client**（Task 40 引入）：每次 INCR/session 读写新建 TCP 连接 → 高并发下连接建立开销 + TIME_WAIT；P99 待测。
2. **SQLAlchemy pool**：pool_size=10/max_overflow=20、无显式 pool_timeout/pool_recycle；并发>30 时排队等待（默认 timeout 30s）。
3. **RAG 双查询**（向量 + BM25 + RRF）：合成检索链每请求 2 次 DB 查询 + RRF 计算；高并发放大。
4. **SSE 长连接**：Product QA/Script/Sales Agent 长流占用 worker；无并发上限保护（仅 rate limit 20/窗口）。
5. **AI embedding 成本**：ingestion 每文档向量化（1536 维）耗时与费用；生产链路同步。
6. **N+1 风险**：Dashboard/Customer 聚合查询未 EXPLAIN 验证。
7. **Agent tool chain**：MAX_TOOL_CALLS=8 顺序工具调用，每工具含 RAG/DB 往返。

## Benchmark Plan（本 Task，分层）

| 层 | 内容 | AI | 环境 |
|---|---|---|---|
| **A. Deterministic** | API（health/kb/customer）/DB CRUD/Redis incr-session/RAG（vector+BM25+RRF+permission）/ingestion（mock embedding） | mock | PG16+pgvector+Redis（workflow 容器） |
| **B. Production-like** | uvicorn 起真实 backend：HTTP API/Product QA SSE/Script SSE/Sales Agent（mock AI）；容量 profiles 1/5/10 | mock | 同上 + uvicorn |
| **C. Real AI smoke（opt-in）** | Product QA/Script/Sales Agent 各 1-2 次真实调用；记录 provider/model/latency/token usage | **real**（`inputs.ai=true` 且 `AZB_AI_API_KEY` secret 存在，否则 NOT RUN） | 同上 + 真实 provider |

- 每项记录 p50/p95/error rate/throughput（可测才写）；SSE 解析真实 event stream（TTFE/completion/total）。
- 权限安全：RAG benchmark 使用 Task 17B 角色/组织过滤路径（不绕过）。
- 数据：合成 seed（现有 `seed_backup_fixture.py` 的 KB/Doc/chunks/audit + seed.py 基线），无真实客户数据。
- 容量：CI Runner 资源有限，profiles 1/5/10；**CI Runner benchmark ≠ production capacity**（文档明确）。

## 修复原则（Phase 10）

仅修复 benchmark 直接证明的瓶颈（如 Redis client 复用、pool timeout、明显缺索引）；不改 API contract、不绕权限、不因性能重构核心架构；发现 timeout/429 必须正确报错（不 fallback Mock）。
