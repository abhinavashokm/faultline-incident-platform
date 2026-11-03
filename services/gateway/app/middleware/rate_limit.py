import asyncio
import collections
import logging
import math
import time
from typing import Callable, Protocol

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings
from app.errors import rate_limit_exceeded_response

logger = logging.getLogger(__name__)


def get_client_ip(request: Request, trust_forwarded_for: bool) -> str:
    """Determine client IP from peer or X-Forwarded-For if trusted."""
    if trust_forwarded_for:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            first_ip = xff.split(",")[0].strip()
            if first_ip:
                return first_ip
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


class RateLimiter(Protocol):
    async def check(self, key: str) -> tuple[bool, int]:
        """Check rate limit for key. Returns (allowed, retry_after_seconds)."""
        ...


class MemoryRateLimiter:
    """In-memory sliding window rate limiter."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._records: dict[str, collections.deque[float]] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        async with self._lock:
            dq = self._records.setdefault(key, collections.deque())
            threshold = now - self.window_seconds
            while dq and dq[0] <= threshold:
                dq.popleft()

            if len(dq) >= self.limit:
                earliest = dq[0]
                retry_after = max(1, int(math.ceil(earliest + self.window_seconds - now)))
                return False, retry_after

            dq.append(now)
            return True, 0


LUA_SLIDING_WINDOW = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local clear_before = now - window

redis.call('ZREMRANGEBYSCORE', key, 0, clear_before)
local current_requests = redis.call('ZCARD', key)

if current_requests < limit then
    redis.call('ZADD', key, now, now)
    redis.call('EXPIRE', key, math.ceil(window))
    return {1, 0}
else
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_after = 1
    if oldest and oldest[2] then
        retry_after = math.ceil(tonumber(oldest[2]) + window - now)
    end
    if retry_after < 1 then retry_after = 1 end
    return {0, retry_after}
end
"""


class RedisRateLimiter:
    """Distributed Redis sliding window rate limiter with fail-open fallback."""

    def __init__(self, redis_client, limit: int, window_seconds: int) -> None:
        self.redis = redis_client
        self.limit = limit
        self.window_seconds = window_seconds
        self._script = None

    async def check(self, key: str) -> tuple[bool, int]:
        try:
            now = time.time()
            redis_key = f"gateway:ratelimit:{key}"
            if self._script is None:
                self._script = self.redis.register_script(LUA_SLIDING_WINDOW)
            result = await self._script(
                keys=[redis_key],
                args=[now, self.window_seconds, self.limit],
            )
            allowed = bool(result[0] == 1)
            retry_after = int(result[1])
            return allowed, retry_after
        except Exception as exc:
            logger.warning("Redis rate limiter failed: %s; failing open", exc)
            return True, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limit per client IP with configurable limit, window, and backend."""

    def __init__(self, app, settings: Settings, rate_limiter: RateLimiter | None = None) -> None:
        super().__init__(app)
        self.settings = settings
        self.limiter = rate_limiter

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Exempt health endpoints
        if request.url.path == "/health" or request.url.path.startswith("/health/"):
            return await call_next(request)

        limiter = self.limiter or getattr(request.app.state, "rate_limiter", None)
        if limiter is None:
            return await call_next(request)

        client_ip = get_client_ip(request, self.settings.trust_forwarded_for)
        allowed, retry_after = await limiter.check(client_ip)

        if not allowed:
            logger.warning(
                "Rate limit exceeded for client_ip=%s (retry_after=%ds)",
                client_ip,
                retry_after,
            )
            return rate_limit_exceeded_response(retry_after=retry_after)

        return await call_next(request)

