import logging
from typing import Protocol
from uuid import UUID

import redis.asyncio as redis
from redis.commands.core import AsyncScript
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Atomic fixed-window rate limiting script
RATE_LIMIT_LUA = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])

local current = redis.call('INCR', key)
if current == 1 then
    redis.call('EXPIRE', key, window)
end

local ttl = redis.call('TTL', key)
if ttl < 0 then
    ttl = window
end

if current > limit then
    return {0, ttl}
else
    return {1, ttl}
end
"""


class RateLimiter(Protocol):
    async def is_allowed(self, project_id: UUID) -> tuple[bool, int]:
        """Check if request is allowed for project_id.
        Returns: (allowed: bool, retry_after_seconds: int)
        """
        ...

    async def is_healthy(self) -> bool:
        ...


class RedisRateLimiter:
    def __init__(
        self,
        redis_client: redis.Redis,
        limit: int | None = None,
        window_seconds: int | None = None,
    ) -> None:
        self.redis = redis_client
        self.limit = limit or settings.rate_limit_requests
        self.window_seconds = window_seconds or settings.rate_limit_window_seconds
        self._script: AsyncScript | None = None

    def _get_script(self) -> AsyncScript:
        if self._script is None:
            self._script = self.redis.register_script(RATE_LIMIT_LUA)
        return self._script

    async def is_allowed(self, project_id: UUID) -> tuple[bool, int]:
        key = f"ratelimit:{project_id}"
        try:
            script = self._get_script()
            res = await script(
                keys=[key],
                args=[self.limit, self.window_seconds],
            )
            # res is [allowed_int, ttl_int]
            allowed = bool(res[0] == 1)
            ttl = int(res[1]) if res[1] > 0 else self.window_seconds
            return allowed, ttl if not allowed else 0
        except (RedisError, ConnectionError, TimeoutError, OSError) as exc:
            # Rule: If Redis is down, limiter fails OPEN
            logger.warning("Redis rate limiter unavailable (%s). Failing open.", exc)
            return True, 0

    async def is_healthy(self) -> bool:
        try:
            res = await self.redis.ping()
            return bool(res)
        except Exception as exc:
            logger.warning("Redis health check failed: %s", exc)
            return False


class FakeRateLimiter:
    """In-memory rate limiter for tests."""

    def __init__(self, limit: int = 120, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.counts: dict[UUID, int] = {}
        self.should_fail_open = False
        self.force_block = False
        self.healthy = True

    async def is_allowed(self, project_id: UUID) -> tuple[bool, int]:
        if self.should_fail_open:
            return True, 0
        if self.force_block:
            return False, self.window_seconds

        current = self.counts.get(project_id, 0) + 1
        self.counts[project_id] = current
        if current > self.limit:
            return False, self.window_seconds
        return True, 0

    async def is_healthy(self) -> bool:
        return self.healthy
