# Performance Baseline（Task 41 · Cloud CI Capacity Baseline）

> 状态：**CLOUD CI CAPACITY BASELINE（非正式 SLA）**——CI Runner 环境数据，非生产硬件/网络/模型配额
> Commit: 0d47da0（Performance Benchmark workflow run 32358977127 全绿）

---

## Benchmark Environment

- **Runner**：GitHub Actions `ubuntu-latest`（2vCPU/7GB 级 CI 环境，非生产硬件）
- **Services**：PostgreSQL 16 + pgvector（docker）、Redis 7（docker）、backend uvicorn（单 worker）、Python 3.12
- **数据**：synthetic seed（seed.py 基线 + seed_backup_fixture 的 KB/Doc/3 chunks/AuditLog）
- **AI**：Layer A/B 用 mock provider（**含模拟流延迟，见下**）；Layer C 真实 AI = **NOT RUN（无 AZB_AI_API_KEY secret）**
- **Profile**：quick（deterministic n=10-30、http n=5-30、容量 1/5/10×3）

## 核心 p50/p95（0d47da0，err 均为 0）

| 项 | p50 (ms) | p95 (ms) | tps | 说明 |
|---|---|---|---|---|
| api_health（ASGI） | 1.65 | 2.45 | 572 | liveness |
| api_ready | 31.5 | 32.9 | 31.6 | DB+Redis+AI 全检查 |
| api_kb_list（admin） | 20.8 | 74.5 | 38 | 含 RBAC+org 过滤 |
| sse_product_qa（mock） | **3522** | **4967** | 0.28 | RAG 端到端 + **mock 流延迟**（TTFE 2778ms） |
| http_health（uvicorn） | 2.14 | 3.22 | 427 | 真实 HTTP |
| http_sse_product_qa（mock） | **3211** | **4948** | 0.30 | TTFE **19.5ms**（首事件快；完成慢因 mock 流） |
| http_sse_sales_agent（mock） | 28.8 | 83.4 | 24.8 | TTFE 20.4ms；工具链快 |
| 容量 health c1 / c5 / c10 | 2.4 / 8.0 / 12.5 | 2.5 / 9.9 / 17.3 | 425/134/83 | **线性扩展，0 错误** |
| db_org_count | 0.30 | 1.22 | 2908 | 简单 COUNT |
| redis_incr（原子计数） | 2.32 | 2.63 | 424 | 含短生命周期连接 |
| redis_session_set_get | 4.69 | 5.19 | 210 | JSON 读写 |

## 主要瓶颈（Observed）

1. **Product QA SSE 总延迟 3.2-3.5s**：其中 **RAG 检索真实 0.36-0.80s**（`rag_query_result` 日志，retrieval_count=3，pgvector+BM25+RRF 双查询）；
   其余 ~2.8s 为 **mock provider 模拟流延迟**（每 2-4 字 sleep 0.02-0.06s，非真实）。真实 AI latency = **Not Benchmarked**（需层 C）。
2. **RAG 检索 0.5s 为真实可观察热点**（小数据量下仍 ~0.4-0.8s）——建议后续 EXPLAIN + 分项 profiling（embedding/vector/BM25/RRF/permission）。
3. Redis 短生命周期 client（Task 40）每操作建连：incr p50 2.3ms / session 4.7ms——**可接受**（毫秒级），高并发下需连接池评估。

## AI / RAG / SSE 指标

- **RAG retrieval**：latency 356-796ms（日志提取，deterministic 模式 10 次）；retrieval_count=3（fixture 数据量）
- **SSE TTFE**：Product QA 19.5ms、Sales Agent 20.4ms（mock，首事件即达）
- **AI latency/token usage**：**NOT RUN**（无真实 AI secret；需配置 `AZB_AI_API_KEY` 后手动 workflow_dispatch run_ai=true）

## 容量结论（Capacity Caveats）

- health API 1→5→10 并发 p50 2.4→8.0→12.5ms、0 错误——**线性扩展无退化迹象**；CI Runner 2vCPU 下未打爆。
- **CI Runner benchmark ≠ production capacity**：非生产硬件/网络/云 DB-Redis/模型配额，不构成 SLA/QPS 承诺。
- 未测：CPU/Memory 利用率、PG 连接池（pool_size=10/max_overflow=20）压力、Redis P99 长尾、ingestion/embedding 成本、Script generation、Training/score。

## Recommended Next Actions

1. **配置 AZB_AI_API_KEY secret** → 手动 `workflow_dispatch run_ai=true` 完成层 C（真实 AI latency/token usage，成本可控）。
2. RAG 检索分项 profiling（vector vs BM25 vs RRF vs permission）→ 决定是否需要索引/查询优化（当前不因单次 benchmark 改库）。
3. 生产部署后以真实硬件/网络重跑本 harness 作为容量基线；PG 连接池/Redis 连接池压测留给专项。
4. 若后续观测到 Redis client 建连成为瓶颈 → 评估连接池（当前毫秒级，非紧急）。

## Not Benchmarked（明确未测，不伪造）

Script generation SSE、document ingestion/embedding、Training/score、真实 AI latency/token、CPU/Memory、PG 连接利用率、Redis P99 长尾、生产吞吐。
