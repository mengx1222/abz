# Real AI Performance（Layer C）— 实测基线

> RDY 阶段3 产出。区分两类基线，**不写虚假生产 SLA**：
> - **Cloud CI Baseline（Deterministic / Capacity）**：GitHub Actions 云端、mock provider 的功能/容量基准（Task 41 performance-benchmark）。
> - **Real AI Measured Baseline（Layer C）**：真实 DashScope/Qwen + 真实 PG/pgvector + Redis + Pilot seed 下的小规模实测（本文件）。
> 真实测量为云端 CI 环境，不等同生产硬件/SLA；仅用于相对分解与趋势观察。

---

## 1. 测量环境（GitHub Actions @ 43977ae）

| 项 | 值 |
|----|----|
| Workflow | `real-ai-layer-c`（opt-in：workflow_dispatch / 修改 benchmark 自身路径时触发；普通 push 不运行） |
| Provider / Model | DashScope Qwen `qwen-plus` + `text-embedding-v3`（Secrets 注入） |
| 环境 | PG16+pgvector、Redis7、`AZB_DEMO_MODE=false`、Pilot seed（5 客户 / 3 文档 9 chunks） |
| 样本量 | 每类 3 次（小规模、可控成本；`AZB_BENCH_REPEAT` 可调） |
| 脚本 | `backend/scripts/real_ai_layer_c_benchmark.py`（结果 `/tmp/real_ai_layer_c.json` artifact） |
| 测量指标 | time-to-first-event (TTFB)、total latency、p50/p95、阶段分解、tool/event 计数、error rate |

## 2. 实测结果（2026-08-20，repeat=3）

### 2.1 Product QA SSE（ProductQaService.chat）

| 指标 | mean | p50 | p95 |
|------|------|-----|-----|
| TTFB | 697 ms | 542 ms | 1,049 ms |
| Total | 703 ms | 546 ms | 1,056 ms |
| events | 4 / run | - | - |
| error rate | 0/3 | - | - |

结论：RAG 命中 + 流式回答全链路 <1.1s；TTFB 与 total 接近（单次模型响应）。

### 2.2 Script Generation（ScriptService.generate_scripts）

| 指标 | mean | p50 | p95 |
|------|------|-----|-----|
| Total | 6,306 ms | 6,324 ms | 6,373 ms |
| 生成话术 | 1 / run（style_complete） | - | - |
| error rate | 0/3 | - | - |

结论：含 RAG 增强 + 单条话术流式生成 + 合规检查，~6.3s（provider 生成占主导）。

### 2.3 Sales Agent Golden Flow（SalesAgentService.chat）— **27.6s 延迟分解**

| 阶段 | p50 | 占比（对 total 28.8s） |
|------|-----|------------------------|
| customer_context（读客户） | 4.4 ms | <0.1% |
| activity（沟通历史） | 2.5 ms | <0.1% |
| **RAG 检索（search_product_knowledge）** | **883 ms** | **~3%** |
| **话术生成（generate_sales_script, LLM）** | **22,715 ms** | **~79%** |
| compliance（合规检查） | 0.4 ms | <0.1% |
| 汇总/流式收尾（_summarize 等） | 其余 | ~18% |
| **Total（agent_complete.latency_ms）** | **28,782 ms（p50）** | 100% |
| tool_count | 5 | - |
| error rate | 0/3 | - |

**核心结论（27.6s 分解）**：
- 延迟主成分是 **话术生成（LLM provider 流式生成）≈ 22.7s，占 ~79%**；RAG 仅 ~883ms（~3%）；
  customer/activity/compliance 工具链 <1%——**非 RAG、非 tool chain、非 compliance 瓶颈**。
- 汇总/流式收尾 ~18%（含最终 LLM 汇总与事件输出），属 provider 生成的一部分。
- 这是云 CI 环境 + qwen-plus 的实测值；生产环境 latency 取决于所选模型档位与网络。

## 3. 与 Cloud CI Baseline 的关系

| 基线 | 用途 | 说明 |
|------|------|------|
| Deterministic（mock） | 功能正确性/容量趋势 | mock 伪向量/即时响应，**不代表真实模型延迟** |
| Real AI Layer C（本文件） | 真实链路延迟分解 | qwen-plus 实测；仅相对基准，**不承诺生产 SLA** |

## 4. 说明与限制

- 样本量 3（可控成本）；p95 为小样本插值，仅作量级参考。
- 未保存：完整 prompt、客户 PII、API key（脚本仅输出事件名/时长/计数）。
- 未发现 timeout / 无限 tool loop / 异常重试（error rate 0/3）——**只测量，未做优化**（按 RDY 指令）。
- 复测：Actions → Real AI Performance Layer C → Run workflow（repeat 1/3/5），或修改 benchmark 脚本自动触发。
