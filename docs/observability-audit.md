# Observability Audit（Task 39 · Monitoring + Alerting + Observability Hardening）

> 状态：**Signals Ready（结构化信号 + 关键错误可观察 + 云端测试）**；外部告警平台 = Integration Required
> 更新：2026-08-20

---

## Current State（现状，源码级审计）

| 信号 | 现状 | 判定 |
|---|---|---|
| 结构化日志（structlog） | ✅ 全 backend 统一 structlog；事件名即 event_type 风格（`request`/`unhandled_error`/`openai_chat_error`/`rag_query_no_relevant_results` 等） | ✅ |
| request_id | ✅ `RequestIDMiddleware`：注入 + 响应头 `X-Request-ID` 回显；`ErrorHandlerMiddleware`/`AuditMiddleware`/AI/RAG 日志均携带 | ✅ |
| 请求级结构化日志 | ✅ `RequestLoggingMiddleware`：method/path/status_code/duration_ms/request_id（跳过 /health 防噪声）；`AppMetrics` 线程安全计数器 | ⚠️ 缺 user_id/org 归属 |
| 异常处理 | ✅ `ErrorHandlerMiddleware`：unhandled_error 结构化日志（request_id/path/error/exc_info）+ 500 JSON（含 request_id） | ✅ |
| 健康检查 | ✅ `/health`（liveness）/ `/ready`（DB+Redis+AI checks）/ `/health/detail`（masked URL） | ⚠️ **/ready 依赖异常仍 HTTP 200**（SuccessResponse 恒 200，仅 data.status=not_ready） |
| AI 可观察 | ✅ openai_provider：成功日志含 prompt/completion_tokens/latency_ms；chat/stream/embed 错误日志 | ⚠️ 错误日志无统一 `error_code`（401/429/timeout 无法机器区分） |
| RAG 可观察 | ✅ pipeline：rag_query_no_relevant_results / rag_prompt_injection_blocked / rag_confidence_none_refuse / document_index_error | ⚠️ 成功检索无 retrieval_count/latency 记录 |
| SSE 可观察 | ✅ product_qa_chat_start（user_id/conversation_id/question[:100]）/ product_qa_chat_error | ✅ |
| DB/Redis 失败 | ✅ health `_check_database`/`_check_redis` warning 日志 + 状态上报 | ⚠️ 无 error_code |
| Audit/Backup 失败 | ✅ audit_log_error warning / backup 脚本非 0 退出 | ✅ |
| 敏感信息防护 | ✅ health/detail `_mask_url`；日志不落 body/token（Task 37 已验证 audit） | ⚠️ **无 redaction regression 测试** |

## Missing Signals（缺口）

| # | 缺口 | Severity | 说明 |
|---|---|---|---|
| M1 | `/ready` 依赖异常仍 200 | **High** | 编排/探针无法从 HTTP 状态区分就绪与否；需非 200（503）+ error_code |
| M2 | request 日志无 user_id/org | Medium | 无法回答"哪个用户受影响"（中间件态已有 user，补字段即可） |
| M3 | AI 错误无统一 error_code | Medium | 401/429/timeout 无法被监控机器消费 |
| M4 | RAG 成功检索无 retrieval_count/latency | Low | 无法评估检索质量与耗时趋势 |
| M5 | secret redaction 无测试固化 | **High** | 存在回归风险（新日志语句可能泄密） |
| M6 | health/ready 依赖失败无测试 | Medium | 行为未锁定 |

## Recommended Minimum（本 Task 落地）

1. **M1**：`/ready` not_ready → HTTP 503 + `data.error_code="READINESS_FAILED"`（保留 checks 明细）；依赖异常日志补 error_code。
2. **M2**：`RequestLoggingMiddleware` 在 `request.state.user` 存在时记录 `user_id`/`organization_id`；`status_code>=500` 附 `error_code="HTTP_5XX"`，`>=400` 附 `HTTP_4XX`（防噪声：不逐业务错误升级告警）。
3. **M3**：openai_provider 错误日志补 `error_code`：401→`OPENAI_AUTH_ERROR`、429→`OPENAI_RATE_LIMIT`、超时→`OPENAI_TIMEOUT`、其余→`OPENAI_CHAT_ERROR`（stream/embed 同理）。
4. **M4**：pipeline 检索结果日志补 `retrieval_count` + `latency_ms`（成功路径最小增强）。
5. **M5/M6**：新增 `test_observability.py`：/ready 依赖失败 503、request_id 传播、health/detail 脱敏、结构化错误字段；AI 401/429 error_code 日志断言（capsys 捕获）。

## 指标语义（阶段 6，当前以结构化日志输出，不虚构 SLA/QPS）

| 指标 | 载体（事件名） | 关键字段 |
|---|---|---|
| API request/error/latency | `request` | method/path/status_code/duration_ms/request_id/user_id/error_code |
| AI success/error/latency/tokens | `openai_chat_success` 等 | provider/model/latency_ms/prompt_tokens/completion_tokens/status |
| AI 401/429/timeout | `openai_chat_error` 等 | error_code/status_code/request_id |
| RAG hit/refusal/error | `rag_query_*` / `rag_*_refuse` | retrieval_count/latency_ms/refusal_reason/top_score |
| SSE completion/error | `product_qa_chat_*` | user_id/conversation_id/status/error |
| Ingestion success/failure | `document_index_*` | title/error/chunks |
| Audit write failure | `audit_log_error` | action/resource_type/error |
| DB/Redis health | `/ready` checks | database/redis 状态 |

## Alerting State

- **Implemented**：稳定可消费信号（结构化事件 + error_code + /health /ready 语义 + AppMetrics 计数器）。
- **Integration Required（外部依赖）**：Prometheus/Alertmanager 抓取与告警规则、云日志（含 Sentry 类错误上报）、
  日志采集管道（vector/fluentd）——不假装已接入；生产环境接入为后续运维项。

## Security / Privacy（阶段 7）

- 日志禁止：完整 prompt（SSE 记录 question[:100] 摘要）、客户敏感 payload、API Key、PAT、JWT、DB 密码、refresh token、完整 Authorization header。
- `/health/detail` 输出 masked URL（`_mask_url`）。
- 新增 redaction regression：断言典型错误场景与健康检查输出不含凭据。

## Out of Scope

- 完整 Prometheus/Alertmanager/Grafana 监控栈、分布式 tracing（OpenTelemetry）、SLO/SLA 承诺与性能基准（需真实压测）。
