"""测试 Rate Limiting。"""
import time

from app.core.rate_limit import TokenBucketRateLimiter


class TestTokenBucketRateLimiter:
    def test_acquire_within_capacity(self):
        limiter = TokenBucketRateLimiter(rate=1000.0, capacity=10)
        assert limiter.acquire() is True
        assert limiter.acquire() is True

    def test_acquire_exceeds_capacity(self):
        limiter = TokenBucketRateLimiter(rate=0.0, capacity=5)
        for _ in range(5):
            assert limiter.acquire() is True
        assert limiter.acquire() is False

    def test_refill_over_time(self):
        limiter = TokenBucketRateLimiter(rate=1000.0, capacity=5)
        for _ in range(5):
            limiter.acquire()
        assert limiter.acquire() is False
        time.sleep(0.01)  # 10ms → ~10 tokens
        assert limiter.acquire() is True

    def test_multi_token_acquire(self):
        limiter = TokenBucketRateLimiter(rate=0.0, capacity=10)
        assert limiter.acquire(tokens=5) is True
        assert limiter.acquire(tokens=6) is False
        assert limiter.acquire(tokens=5) is True

    def test_empty_bucket(self):
        limiter = TokenBucketRateLimiter(rate=0.0, capacity=0)
        assert limiter.acquire() is False

    def test_burst_allowance(self):
        """桶初始满，应允许突发请求。"""
        limiter = TokenBucketRateLimiter(rate=0.0, capacity=100)
        for _ in range(100):
            assert limiter.acquire() is True
        assert limiter.acquire() is False
