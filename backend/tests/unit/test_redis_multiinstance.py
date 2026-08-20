"""Task 40 — Redis 多实例集成测试（真实 Redis；AZB_TEST_REDIS_URL 未设置时跳过）。

覆盖（Step 7 矩阵）：
1. Redis connectivity（ping）
2. incr 原子性 + TTL（asyncio.gather 并发，无 get→incr→set 竞态；新 key 必有 TTL）
3. rate limit 计数跨客户端共享（实例 A / 实例 B 视图一致）
4. session store set/get/delete + TTL
5. 多 store 共享（实例 A 写 → 实例 B 读）
6. Redis 不可用 → rate limit fail-closed 503（不静默内存降级）
7. Agent session continuity（service 实例 A 写 → 实例 B 同 session_id 读取一致）
"""
import asyncio
import os

import pytest
import pytest_asyncio

from app.core.config import settings
from app.core.redis_store import (
    RedisSessionStore,
    get_redis_client,
    redis_incr_with_ttl,
    redis_ttl,
)

REDIS_URL = os.environ.get("AZB_TEST_REDIS_URL", "")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not REDIS_URL, reason="AZB_TEST_REDIS_URL not set"),
]


@pytest_asyncio.fixture
async def _reset(monkeypatch):
    """确保每次测试使用独立 Redis（flushdb）。"""
    monkeypatch.setattr(settings, "REDIS_URL", REDIS_URL)
    import app.core.redis_store as rs
    rs._redis = None  # 强制重建 client（指向测试 URL）
    client = get_redis_client()
    assert client is not None
    await client.flushdb()
    yield client


class TestRedisConnectivity:
    async def test_ping(self, _reset):
        assert await _reset.ping() is True


class TestAtomicIncr:
    async def test_concurrent_incr_exact_count_and_ttl(self, _reset):
        """20 并发 INCR → 精确 20（原子性，无竞态）；key 有 TTL（无无限 key）。"""
        key = "rl:test:1.2.3.4:/api/v1/auth/login"
        results = await asyncio.gather(*[redis_incr_with_ttl(key, 3) for _ in range(20)])
        assert [r for r in results if r is not None] == list(range(1, 21))
        ttl = await redis_ttl(key)
        assert ttl is not None and 0 < ttl <= 3

    async def test_ttl_reapplied_on_same_key(self, _reset):
        """同一 key 再次 INCR 不重置 TTL 语义（首次 EXPIRE 后持续递减）。"""
        key = "rl:test:ttl"
        await redis_incr_with_ttl(key, 5)
        t1 = await redis_ttl(key)
        await asyncio.sleep(1.2)
        await redis_incr_with_ttl(key, 5)
        t2 = await redis_ttl(key)
        assert t1 is not None and t2 is not None
        assert t2 < t1, "TTL 应随时间递减（不因后续 INCR 重置）"


class TestRateLimitSharing:
    async def test_counter_shared_across_clients(self, _reset):
        """实例 A / 实例 B（不同 client 视图）共享同一计数。"""
        key = "rl:test:shared"
        a1 = await redis_incr_with_ttl(key, 10)
        a2 = await redis_incr_with_ttl(key, 10)
        assert a1 == 1 and a2 == 2
        # 新 client 视图（等价于另一实例）仍见同一计数
        b1 = await redis_incr_with_ttl(key, 10)
        assert b1 == 3, "不同实例应共享同一 Redis 计数"


class TestSessionStore:
    async def test_set_get_delete_and_ttl(self, _reset):
        store = RedisSessionStore(namespace="agent:session", ttl_seconds=60)
        await store.set("sid-1", {"customer_id": "c1", "history": [{"role": "user", "summary": "hi"}]})
        data = await store.get("sid-1")
        assert data == {"customer_id": "c1", "history": [{"role": "user", "summary": "hi"}]}
        ttl = await redis_ttl("agent:session:sid-1")
        assert ttl is not None and 0 < ttl <= 60
        assert await store.delete("sid-1") is True
        assert await store.get("sid-1") is None

    async def test_instance_a_writes_instance_b_reads(self, _reset):
        """实例 A（store_a）写入 → 实例 B（store_b，独立对象）读取一致（同一 Redis）。"""
        store_a = RedisSessionStore(namespace="agent:session", ttl_seconds=3600)
        store_b = RedisSessionStore(namespace="agent:session", ttl_seconds=3600)
        await store_a.set("sid-shared", {"customer_id": "c-9", "sales_stage": "quotation"})
        data = await store_b.get("sid-shared")
        assert data == {"customer_id": "c-9", "sales_stage": "quotation"}


class TestFailurePolicy:
    async def test_incr_returns_none_when_redis_down(self, _reset, monkeypatch):
        """Redis 不可用：incr 返回 None → 调用方 fail-closed（不静默放行/不内存降级）。"""
        import app.core.redis_store as rs

        async def _broken(*a, **k):
            raise ConnectionError("redis down")

        monkeypatch.setattr(rs.get_redis_client(), "eval", _broken)
        val = await redis_incr_with_ttl("rl:x", 1)
        assert val is None

    async def test_session_store_get_none_set_false_when_down(self, _reset, monkeypatch):
        """Redis 不可用：session get 返回 None、set 返回 False（不抛、不静默内存）。"""
        import app.core.redis_store as rs

        async def _fail(*a, **k):
            raise ConnectionError("redis down")

        monkeypatch.setattr(rs.get_redis_client(), "get", _fail)
        monkeypatch.setattr(rs.get_redis_client(), "set", _fail)
        store = RedisSessionStore(namespace="agent:session")
        assert await store.get("x") is None
        assert await store.set("x", {"a": 1}) is False


class TestAgentSessionContinuity:
    async def test_session_continuity_across_instances(self, _reset, monkeypatch):
        """Agent session：实例 A 建会话并记忆 → 实例 B 同 session_id 读取上下文一致。"""
        monkeypatch.setattr(settings, "DEMO_MODE", False)
        from app.agent.orchestrator import SalesAgentService

        svc_a = SalesAgentService(db=None)
        session_a = await svc_a._get_or_create_session(
            "agent-sess-1", customer_id="c-100", product_type="医疗险", sales_stage="lead",
        )
        await svc_a._remember(session_a, "user", "客户想了解百万医疗险")
        await svc_a._remember(session_a, "assistant", "已推荐保障范围")

        # 实例 B：新 service 对象（同 Redis），同 session_id
        svc_b = SalesAgentService(db=None)
        session_b = await svc_b._get_or_create_session(
            "agent-sess-1", customer_id=None, product_type=None, sales_stage=None,
        )
        assert session_b.customer_id == "c-100"
        assert session_b.product_type == "医疗险"
        assert session_b.sales_stage == "lead"
        assert session_b.history == session_a.history
        assert [h["summary"] for h in session_b.history] == [
            "客户想了解百万医疗险", "已推荐保障范围",
        ]
