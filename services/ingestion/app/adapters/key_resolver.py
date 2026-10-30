import json
import logging
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import httpx
import redis.asyncio as redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.logging import mask_key

logger = logging.getLogger(__name__)


class InvalidKeyError(Exception):
    """Raised when public key is invalid, not found, or revoked (401)."""


class KeyResolverUnavailableError(Exception):
    """Raised when Control Plane is unreachable and key is not in cache (503)."""


@dataclass(frozen=True)
class ResolvedKey:
    project_id: UUID
    workspace_id: UUID
    revoked: bool = False


class ProjectKeyResolver(Protocol):
    async def resolve(self, public_key: str) -> ResolvedKey:
        ...


class CachedHttpProjectKeyResolver:
    """Resolves project public keys via Redis cache with fallback to Control Plane internal HTTP endpoint."""

    def __init__(
        self,
        redis_client: redis.Redis,
        http_client: httpx.AsyncClient | None = None,
        control_plane_url: str | None = None,
        service_token: str | None = None,
        cache_ttl: int | None = None,
        negative_cache_ttl: int | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.redis = redis_client
        self.http_client = http_client or httpx.AsyncClient()
        self._owns_http_client = http_client is None
        self.control_plane_url = (
            control_plane_url or settings.control_plane_internal_url
        ).rstrip("/")
        self.service_token = (
            service_token if service_token is not None else settings.control_plane_service_token
        )
        self.cache_ttl = cache_ttl or settings.key_cache_ttl_seconds
        self.negative_cache_ttl = (
            negative_cache_ttl or settings.key_negative_cache_ttl_seconds
        )
        self.timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else settings.control_plane_timeout_seconds
        )

    def _cache_key(self, public_key: str) -> str:
        return f"cache:project_key:{public_key}"

    async def _check_cache(self, public_key: str) -> ResolvedKey | None:
        try:
            val = await self.redis.get(self._cache_key(public_key))
            if not val:
                return None
            data = json.loads(val)
            status = data.get("status")
            if status == "valid":
                return ResolvedKey(
                    project_id=UUID(data["project_id"]),
                    workspace_id=UUID(data["workspace_id"]),
                    revoked=False,
                )
            elif status == "revoked":
                raise InvalidKeyError("Project key is revoked")
            elif status == "not_found":
                raise InvalidKeyError("Invalid project key")
        except InvalidKeyError:
            raise
        except (RedisError, ConnectionError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning(
                "Redis key cache lookup failed for key=%s: %s",
                mask_key(public_key),
                exc,
            )
            return None
        return None

    async def _write_cache(self, public_key: str, data: dict, ttl: int) -> None:
        try:
            await self.redis.set(
                self._cache_key(public_key),
                json.dumps(data),
                ex=ttl,
            )
        except (RedisError, ConnectionError, TimeoutError) as exc:
            logger.warning(
                "Redis key cache write failed for key=%s: %s",
                mask_key(public_key),
                exc,
            )

    async def resolve(self, public_key: str) -> ResolvedKey:
        if not public_key or not public_key.strip():
            raise InvalidKeyError("Public key is required")

        public_key = public_key.strip()
        key_masked = mask_key(public_key)

        # 1. Check Redis cache first
        cached = await self._check_cache(public_key)
        if cached is not None:
            return cached

        # 2. Call Control Plane internal endpoint on cache miss
        url = f"{self.control_plane_url}/api/v1/internal/project-keys/{public_key}"
        headers = {}
        if self.service_token:
            headers["X-Service-Token"] = self.service_token

        logger.debug("Resolving key=%s via Control Plane at %s", key_masked, url)

        try:
            response = await self.http_client.get(
                url,
                headers=headers,
                timeout=self.timeout_seconds,
            )
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            logger.error(
                "Control Plane unreachable for key=%s: %s",
                key_masked,
                exc,
            )
            raise KeyResolverUnavailableError(
                "Key resolution service unavailable"
            ) from exc

        if response.status_code == 200:
            try:
                res_data = response.json()
                is_revoked = bool(res_data.get("revoked", False))
                if is_revoked:
                    await self._write_cache(
                        public_key,
                        {"status": "revoked"},
                        self.negative_cache_ttl,
                    )
                    raise InvalidKeyError("Project key is revoked")

                proj_id = UUID(res_data["project_id"])
                ws_id = UUID(res_data["workspace_id"])

                await self._write_cache(
                    public_key,
                    {
                        "status": "valid",
                        "project_id": str(proj_id),
                        "workspace_id": str(ws_id),
                    },
                    self.cache_ttl,
                )
                return ResolvedKey(project_id=proj_id, workspace_id=ws_id, revoked=False)
            except (KeyError, ValueError) as exc:
                logger.error("Control plane response parsing error for key=%s: %s", key_masked, exc)
                raise KeyResolverUnavailableError("Invalid response from key resolution service") from exc

        elif response.status_code in (404, 401, 403):
            # Unknown or invalid key: negative-cache it
            await self._write_cache(
                public_key,
                {"status": "not_found"},
                self.negative_cache_ttl,
            )
            raise InvalidKeyError("Invalid project key")

        else:
            logger.error(
                "Control Plane returned unexpected status=%d for key=%s",
                response.status_code,
                key_masked,
            )
            raise KeyResolverUnavailableError("Key resolution service unavailable")


class FakeProjectKeyResolver:
    """In-memory fake resolver for tests."""

    def __init__(self) -> None:
        self.keys: dict[str, ResolvedKey] = {}
        self.simulate_unreachable = False

    def add_key(self, public_key: str, project_id: UUID, workspace_id: UUID, revoked: bool = False) -> None:
        self.keys[public_key] = ResolvedKey(
            project_id=project_id,
            workspace_id=workspace_id,
            revoked=revoked,
        )

    async def resolve(self, public_key: str) -> ResolvedKey:
        if self.simulate_unreachable:
            raise KeyResolverUnavailableError("Simulated Control Plane outage")

        if not public_key or public_key not in self.keys:
            raise InvalidKeyError("Invalid project key")

        resolved = self.keys[public_key]
        if resolved.revoked:
            raise InvalidKeyError("Project key is revoked")
        return resolved

