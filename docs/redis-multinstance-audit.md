# Redis Multi-instance Audit（Task 40 · Session / RateLimit Production Hardening）

> 状态：**IMPLEMENTED / CLOUD VERIFIED**——RateLimit 与 Agent Session 迁移 Redis 共享（原子计数 + TTL + 短生命周期 client）；AI conversation 保持 DB-backed
> 更新：2026-08-20（Task 40 落地，c2a6eae）

---

## Current State（源码级审计，main@1497c25）

| State Owner | 存储位置 | 多实例共享 | 判定 |
|---|---|---|---|
| **RateLimit（`core/rate_limit.py`）** | 进程内令牌桶 `self._buckets: dict[str, TokenBucketRateLimiter]`（threading.Lock） | ❌ 不共享 | **缺口 A**：实例 A 限流不作用于实例 B |
| **Agent Session（`agent/orchestrator.py`）** | `SalesAgentService._sessions: dict[str, AgentSession]`（MAX_SESSION_HISTORY=8，注释明示"进程内内存，显式限制"） | ❌ 不共享 | **缺口 B**：实例 A 写入的会话，实例 B 读不到 |
| **AI conversation（`ai/service.py` + `models/conversation.py`）** | **DB-backed**（Conversation/Message 模型，conversation_id 落库） | ✅ 共享 | 保留，不重复实现 |
| **Auth/token（`core/deps.py` + `auth_service.py`）** | **stateless JWT**（HTTPBearer，无 server-side session） | ✅ 天然共享 | 无需新增 session |
| **Redis client（`core/deps.py` `get_redis`）** | `redis.asyncio.Redis` 惰性单例 + **no-op fallback**（"using no-op client" + return） | — | **缺口 C**：silent fallback 违反 Step 4；且无外部调用方（未消费） |
| **Docker/部署（`docker-compose.prod.yml`）** | redis:7-alpine，`AZB_REDIS_URL` 环境注入 | ✅ 统一 endpoint | 保持 |
| **Health** | `/ready` 检查 Redis（`_check_redis`） | ✅ | 保持 |

## State Owners 明细

- **RateLimit**：`RateLimitMiddleware`（`core/middleware.py` 注册）；规则：login (2/s, cap 5)、/api/v1/ai/ (5/s, cap 20)、default (30/s, cap 100)；key=`{client_ip}:{path}`；demo 放宽 ×5。
- **Agent Session**：`SalesAgentService._get_or_create_session / _remember`；字段 session_id/customer_id/product_type/sales_stage/history(≤8)/tool_sequence。
- **AI conversation**：`ProductQaService`（DB Conversation + Message）——无需改动。
- **Redis client**：`deps.get_redis`（unused）+ health `_check_redis`（ping 2s）。

## Multi-instance Risk

1. 限流失效：实例 A 已触发 429，负载均衡切到实例 B 后可继续请求 → 登录暴力破解/滥用防护形同虚设。
2. Agent session 漂移：会话在实例 A 建立（含客户/产品/销售阶段上下文），请求落到实例 B → 上下文丢失，销售流程断裂。
3. silent fallback：Redis 不可用时若静默降级内存 → 生产行为随实例漂移且不可审计。

## Target Architecture（本 Task 落地）

```
┌─ Instance A ─┐   ┌─ Instance B ─┐
│ RateLimit    │   │ RateLimit    │
│ AgentSession │   │ AgentSession │
└──────┬───────┘   └──────┬───────┘
       └───── Redis ──────┘
         INCR+EXPIRE(Lua)   限流原子计数 + TTL
         JSON get/set + TTL  Agent session 共享
```

1. **RateLimit → Redis 原子计数**（固定窗口近似令牌桶）：Lua `INCR + EXPIRE-if-first` 原子执行（禁止 get→incr→set 竞态）；
   窗口秒数 = ceil(capacity/rate)（login=3s cap5、ai=4s cap20、default=4s cap100）；key 保持 `{ip}:{path}` 不变（不扩大/削弱）；
   demo 模式保留内存令牌桶（兼容）。
2. **Agent Session → Redis JSON store**（namespace `agent:session:{id}`，TTL 3600s）：production 读写 Redis；
   demo 保留内存 dict。
3. **Failure Policy（Step 4）**：
   - RateLimit（安全关键）：production Redis 不可用 → **fail-closed 503 RATE_LIMITER_UNAVAILABLE**（不放行不静默）；
   - Agent Session（非关键）：production Redis 不可用 → 明确错误（SSE error `AGENT_SESSION_UNAVAILABLE`），不静默建空会话；
   - demo 模式：内存兼容，边界清晰。
4. **get_redis no-op 修复**：移除 silent fallback；production 失败明确 error_code 记录。

## Migration Plan

1. 新增 `core/redis_store.py`：`get_redis_client()`（惰性单例）+ `RedisSessionStore`（JSON get/set/delete + TTL）+ `redis_incr_with_ttl()`（Lua 原子）。
2. `rate_limit.py`：production 分支走 Redis 原子计数；demo 分支内存桶不变。
3. `agent/orchestrator.py`：session 方法 async 化，production 走 Redis store。
4. 测试 + 云端验证（专用 workflow，真实 Redis）。
5. 文档同步。

## Implemented（Task 40 落地清单，c2a6eae 全矩阵全绿）

- **RateLimit → Redis 原子计数**（`core/rate_limit.py` `_dispatch_redis`）：Lua `INCR+EXPIRE-if-first` 原子执行；
  固定窗口（window=ceil(capacity/rate)）；key=`rl:{ip}:{path}` 不变；demo 模式保留内存令牌桶。
- **Failure Policy（Step 4）**：production Redis 不可用 → **fail-closed 503 RATE_LIMITER_UNAVAILABLE**（不放行、不静默内存降级）；
  Agent session 持久化失败 → 明确日志 `AGENT_SESSION_UNAVAILABLE`（非关键状态不阻塞主流程，行为已文档化）。
- **Agent Session → Redis**（`agent/orchestrator.py`）：production 走 `RedisSessionStore`（namespace `agent:session`，TTL 3600s）；
  实例 A 写入 → 实例 B 同 session_id 读取一致（test 验证）；demo 保留内存 dict。
- **get_redis no-op 移除**（`core/deps.py`）：production 初始化失败明确报错，demo 兼容。
- **Redis client 生命周期**：改为每操作短生命周期 client（`core/redis_store.py`），消除跨 event loop "Event loop is closed" 问题
  （pytest-asyncio 每测试新 loop；生产多 worker 同理）。
- **CI 基建**：backend-tests backend/backend-pg job 起真实 Redis 容器（production 语义测试依赖）；新增
  `redis-multiinstance.yml`（专用 workflow：真实 Redis + 9 用例集成验证）。

## Cloud Verification（c2a6eae）

- CI：Backend **307 passed / 68 skipped**（+9 redis skip 由专用 workflow 覆盖）；backend-pg **59 passed**；Vitest **107**；Prod ✅。
- `redis-multiinstance.yml`：**9/9 PASSED**（真实 Redis）——ping / 20 并发 INCR 精确计数+TTL / TTL 递减不重置 /
  跨 client 计数共享 / session set-get-delete+TTL / 实例 A 写 B 读 / Redis down → incr None（fail-closed 信号）/
  session down → get None+set False / Agent session 跨实例连续性（history 一致）。

## Accepted Limitations（Production Dependency，不伪造）

- **外部 Redis 高可用（哨兵/集群/持久化策略）未配置**——单 Redis 实例多实例共享已实现；生产 HA 为外部依赖。
- 固定窗口近似令牌桶语义（窗口上限=capacity，不削弱限制；瞬时速率特性略有差异，文档化）。
- 性能 benchmark（RPS/并发上限）留给后续任务，不凭空制定 SLA。
- Agent session TTL 3600s：超时未活动的会话由 Redis 自动过期（无无限 key）；历史消息上限 MAX_SESSION_HISTORY=8 不变。
- 不写入完整 prompt/客户敏感数据：session 仅存 {role, summary≤300 字符}。
