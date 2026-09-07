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


class TestRateKey:
    """限流身份键：登录用户按 user_id，未认证/无效 token 按 IP（NAT 修复）。"""

    @staticmethod
    def _request(auth: str | None = None):
        from fastapi import Request

        headers = []
        if auth is not None:
            headers.append((b"authorization", auth.encode()))
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/dashboard",
            "headers": headers,
            "client": ("1.2.3.4", 12345),
        }
        return Request(scope)

    def test_valid_token_uses_user_key(self):
        from app.core.rate_limit import RateLimitMiddleware
        from app.core.security import create_access_token

        token = create_access_token({"sub": "user-abc", "phone": "13800138000"})
        request = self._request(f"Bearer {token}")
        key = RateLimitMiddleware._get_rate_key(request, "1.2.3.4")
        assert key == "u:user-abc"

    def test_no_auth_uses_ip_key(self):
        from app.core.rate_limit import RateLimitMiddleware

        request = self._request(None)
        assert RateLimitMiddleware._get_rate_key(request, "1.2.3.4") == "ip:1.2.3.4"

    def test_invalid_token_falls_back_to_ip(self):
        from app.core.rate_limit import RateLimitMiddleware

        request = self._request("Bearer not-a-jwt")
        assert RateLimitMiddleware._get_rate_key(request, "1.2.3.4") == "ip:1.2.3.4"

    def test_non_bearer_uses_ip_key(self):
        from app.core.rate_limit import RateLimitMiddleware

        request = self._request("Basic dXNlcjpwYXNz")
        assert RateLimitMiddleware._get_rate_key(request, "1.2.3.4") == "ip:1.2.3.4"
