"""Task 40 — Redis 共享状态基础设施（RateLimit 原子计数 + Session JSON store）。

设计：
- 全局惰性 Redis client（decode_responses=True），连接失败返回 None（调用方决定 fail 策略）。
- `redis_incr_with_ttl`：Lua 原子 `INCR + EXPIRE-if-first`（禁止 get→incr→set 竞态），
  同时保证新 key 必然带 TTL（无无限 key）。
- `RedisSessionStore`：namespace + TTL 的 JSON session 读写（不写完整 prompt/敏感数据）。
"""
import json
import threading
from typing import Any, Optional

from redis.asyncio import Redis
from structlog import get_logger

from app.core.config import settings

logger = get_logger()

_redis: Optional[Redis] = None
_lock = threading.Lock()


def get_redis_client() -> Optional[Redis]:
    """惰性全局 Redis client。连接初始化失败返回 None（调用方决定 fail-closed/降级）。"""
    global _redis
    if _redis is None:
        with _lock:
            if _redis is None:
                try:
                    _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
                except Exception as e:  # pragma: no cover - 初始化失败防御
                    logger.error(
                        "redis_client_init_error",
                        error=str(e),
                        error_code="REDIS_INIT_FAILED",
                    )
                    _redis = None
    return _redis


# Lua：原子 INCR + 首次创建时设置 TTL（避免竞态与非过期 key 泄漏）
_INCR_WITH_TTL_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""


async def redis_incr_with_ttl(key: str, ttl_seconds: int) -> Optional[int]:
    """Redis 原子计数（INCR + EXPIRE）。返回新计数；Redis 不可用返回 None（调用方 fail-closed）。"""
    client = get_redis_client()
    if client is None:
        return None
    try:
        val = await client.eval(_INCR_WITH_TTL_SCRIPT, 1, key, int(ttl_seconds))
        return int(val)
    except Exception as e:
        logger.warning(
            "redis_incr_error",
            key=key,
            error=str(e),
            error_code="REDIS_INCR_FAILED",
        )
        return None


async def redis_ttl(key: str) -> Optional[int]:
    """查询 key 剩余 TTL（秒）；Redis 不可用返回 None。"""
    client = get_redis_client()
    if client is None:
        return None
    try:
        return int(await client.ttl(key))
    except Exception:
        return None


class RedisSessionStore:
    """通用 JSON session store（namespace 前缀 + TTL 过期）。

    - 只存结构化摘要（调用方保证不写完整 prompt/客户敏感数据）。
    - Redis 不可用：get 返回 None、set 返回 False（调用方按 fail 策略处理，禁止静默内存降级）。
    """

    def __init__(self, namespace: str = "session", ttl_seconds: int = 3600) -> None:
        self._ns = namespace
        self._ttl = ttl_seconds
        self._client = get_redis_client()

    def _key(self, sid: str) -> str:
        return f"{self._ns}:{sid}"

    async def get(self, sid: str) -> Optional[dict]:
        if self._client is None:
            return None
        try:
            raw = await self._client.get(self._key(sid))
            return json.loads(raw) if raw else None
        except Exception as e:
            logger.warning(
                "redis_session_get_error",
                sid=sid,
                error=str(e),
                error_code="REDIS_SESSION_GET_FAILED",
            )
            return None

    async def set(self, sid: str, data: dict, ttl: int | None = None) -> bool:
        if self._client is None:
            return False
        try:
            await self._client.set(
                self._key(sid),
                json.dumps(data, ensure_ascii=False),
                ex=ttl or self._ttl,
            )
            return True
        except Exception as e:
            logger.warning(
                "redis_session_set_error",
                sid=sid,
                error=str(e),
                error_code="REDIS_SESSION_SET_FAILED",
            )
            return False

    async def delete(self, sid: str) -> bool:
        if self._client is None:
            return False
        try:
            await self._client.delete(self._key(sid))
            return True
        except Exception:
            return False
