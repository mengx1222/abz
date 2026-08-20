"""Rate Limiting 中间件。

- Demo 模式：内存令牌桶（兼容历史行为）。
- Production 模式：Redis 原子计数（Lua INCR+EXPIRE，跨实例共享）；
  Redis 不可用 → fail-closed 503（禁止静默内存降级，Task 40）。
"""
import threading
import time
from math import ceil

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from structlog import get_logger

from app.core.config import settings
from app.core.redis_store import redis_incr_with_ttl, redis_ttl

logger = get_logger()


class TokenBucketRateLimiter:
    """线程安全的令牌桶限流器。"""

    def __init__(self, rate: float = 10.0, capacity: int = 100) -> None:
        self.rate = rate
        self.capacity = capacity
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> bool:
        """尝试获取令牌，成功返回 True。"""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
            self._last_refill = now

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    @property
    def remaining(self) -> float:
        """返回当前剩余令牌数。"""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            return min(self.capacity, self._tokens + elapsed * self.rate)

    @property
    def reset_in(self) -> float:
        """返回桶完全充满所需的秒数。"""
        with self._lock:
            return max(0.0, (self.capacity - self._tokens) / self.rate)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """基于 IP 的 Rate Limiting 中间件。"""

    # Demo 模式放宽倍数
    DEMO_RELAX_FACTOR = 5

    # 限流规则: (rate, capacity)
    RULES: list[tuple[str, float, int]] = [
        ("/api/v1/auth/login", 2.0, 5),
        ("/api/v1/ai/", 5.0, 20),
        ("__default__", 30.0, 100),
    ]

    # 不限流路径
    EXEMPT_PATHS = {"/api/v1/health", "/api/v1/ready"}

    def __init__(self, app) -> None:
        super().__init__(app)
        self._buckets: dict[str, TokenBucketRateLimiter] = {}
        self._buckets_lock = threading.Lock()
        self._demo_mode = settings.DEMO_MODE

    def _get_limiter(self, key: str, rate: float, capacity: int) -> TokenBucketRateLimiter:
        """获取或创建指定 key 的令牌桶。"""
        with self._buckets_lock:
            if key not in self._buckets:
                self._buckets[key] = TokenBucketRateLimiter(rate=rate, capacity=capacity)
            return self._buckets[key]

    def _get_client_ip(self, request: Request) -> str:
        """从请求中提取客户端 IP。"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        return request.client.host if request.client else "unknown"

    def _match_rule(self, path: str) -> tuple[float, int]:
        """根据路径匹配限流规则，返回 (rate, capacity)。"""
        for rule_path, rate, capacity in self.RULES:
            if rule_path == "__default__":
                continue
            if path.startswith(rule_path):
                return rate, capacity
        # 返回默认规则
        for rule_path, rate, capacity in self.RULES:
            if rule_path == "__default__":
                return rate, capacity
        return 30.0, 100

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # 免限流路径
        if path in self.EXEMPT_PATHS:
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        rate, capacity = self._match_rule(path)

        # Task 40：production → Redis 原子计数（跨实例共享）
        if not self._demo_mode:
            return await self._dispatch_redis(request, call_next, client_ip, path, rate, capacity)

        # Demo 模式放宽（内存令牌桶）
        rate *= self.DEMO_RELAX_FACTOR
        capacity = int(capacity * self.DEMO_RELAX_FACTOR)

        key = f"{client_ip}:{path}"
        limiter = self._get_limiter(key, rate, capacity)

        if not limiter.acquire():
            retry_after = limiter.reset_in
            logger.warning(
                "rate_limited",
                ip=client_ip,
                path=path,
                retry_after=round(retry_after, 2),
            )
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "请求过于频繁，请稍后再试",
                    },
                    "retry_after": round(retry_after, 2),
                },
                headers={
                    "Retry-After": str(int(retry_after) + 1),
                    "X-RateLimit-Limit": str(capacity),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(retry_after) + 1),
                },
            )

        response = await call_next(request)

        # 添加限流头
        response.headers["X-RateLimit-Limit"] = str(capacity)
        response.headers["X-RateLimit-Remaining"] = str(int(limiter.remaining))
        response.headers["X-RateLimit-Reset"] = str(int(limiter.reset_in) + 1)

        return response

    async def _dispatch_redis(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
        client_ip: str,
        path: str,
        rate: float,
        capacity: int,
    ) -> Response:
        """Production：Redis 原子固定窗口计数（跨实例共享）。

        窗口秒数 = ceil(capacity / rate)（近似令牌桶的桶满时间）；窗口上限 = capacity（不削弱限制）。
        Redis 不可用 → fail-closed 503（安全关键限流不放行、不静默内存降级）。
        """
        window = max(1, ceil(capacity / rate)) if rate > 0 else 1
        key = f"rl:{client_ip}:{path}"

        current = await redis_incr_with_ttl(key, window)
        if current is None:
            logger.warning(
                "rate_limiter_unavailable",
                ip=client_ip,
                path=path,
                error_code="RATE_LIMITER_UNAVAILABLE",
            )
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMITER_UNAVAILABLE",
                        "message": "限流服务暂不可用，请稍后重试",
                    },
                },
            )

        remaining = max(0, capacity - current)
        ttl = await redis_ttl(key) or window

        if current > capacity:
            logger.warning(
                "rate_limited",
                ip=client_ip,
                path=path,
                retry_after=ttl,
                error_code="RATE_LIMITED",
            )
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "请求过于频繁，请稍后再试",
                    },
                    "retry_after": int(ttl),
                },
                headers={
                    "Retry-After": str(int(ttl) + 1),
                    "X-RateLimit-Limit": str(capacity),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(ttl) + 1),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(capacity)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(ttl) + 1)
        return response
