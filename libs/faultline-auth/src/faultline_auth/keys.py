import asyncio
import logging
import time
from typing import Any, Protocol

import httpx
from jwt.algorithms import RSAAlgorithm

from faultline_auth.errors import InvalidToken, KeysUnavailable

logger = logging.getLogger(__name__)


class KeyProvider(Protocol):
    """Protocol for asynchronous JWT key providers."""

    async def get_key(self, kid: str) -> Any:
        ...


class StaticKeyProvider:
    """Key provider using a static PEM-encoded public key and kid."""

    def __init__(self, public_key_pem: str, kid: str) -> None:
        self.public_key_pem = public_key_pem
        self.kid = kid

    async def get_key(self, kid: str) -> Any:
        if kid != self.kid:
            raise InvalidToken(f"Unknown key ID: {kid}")
        return self.public_key_pem


class JwksKeyProvider:
    """Key provider that fetches and caches JWKS keys with TTL and refetch cooldown."""

    def __init__(
        self,
        jwks_url: str,
        *,
        cache_ttl_seconds: int = 300,
        refetch_cooldown_seconds: int = 30,
        timeout_seconds: float = 3.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.jwks_url = jwks_url
        self.cache_ttl_seconds = cache_ttl_seconds
        self.refetch_cooldown_seconds = refetch_cooldown_seconds
        self.timeout_seconds = timeout_seconds
        self._client = client
        self._keys: dict[str, Any] = {}
        self._last_fetched_at: float = 0.0
        self._last_fetch_attempt_at: float = 0.0
        self._lock = asyncio.Lock()

    async def _fetch_jwks(self) -> dict[str, Any]:
        """Fetch and parse JWKS from the remote endpoint."""
        now = time.monotonic()
        self._last_fetch_attempt_at = now
        try:
            if self._client is not None:
                resp = await self._client.get(self.jwks_url, timeout=self.timeout_seconds)
            else:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    resp = await client.get(self.jwks_url)
            resp.raise_for_status()
            jwks = resp.json()
        except Exception as exc:
            logger.warning("Failed to fetch JWKS from %s: %s", self.jwks_url, exc)
            raise

        new_keys: dict[str, Any] = {}
        for key_dict in jwks.get("keys", []):
            kid = key_dict.get("kid")
            if kid and key_dict.get("kty") == "RSA":
                try:
                    new_keys[kid] = RSAAlgorithm.from_jwk(key_dict)
                except Exception as exc:
                    logger.warning("Failed to parse JWK with kid %s: %s", kid, exc)

        self._keys = new_keys
        self._last_fetched_at = now
        return self._keys

    async def get_key(self, kid: str) -> Any:
        now = time.monotonic()

        # Check if kid is already in cache
        if kid in self._keys:
            if now - self._last_fetched_at <= self.cache_ttl_seconds:
                return self._keys[kid]

            # Cache is expired, attempt refresh
            async with self._lock:
                now_in_lock = time.monotonic()
                if now_in_lock - self._last_fetched_at <= self.cache_ttl_seconds:
                    return self._keys.get(kid)

                try:
                    await self._fetch_jwks()
                except Exception:
                    logger.warning(
                        "JWKS refresh failed; continuing to use last-known-good cached keys"
                    )

                if kid in self._keys:
                    return self._keys[kid]
                raise InvalidToken(f"Key ID {kid} not found in JWKS")

        # Key is not in cache (unknown kid or cache empty)
        async with self._lock:
            if kid in self._keys:
                return self._keys[kid]

            now_in_lock = time.monotonic()
            cooldown_active = (
                self._last_fetch_attempt_at > 0
                and (now_in_lock - self._last_fetch_attempt_at) < self.refetch_cooldown_seconds
            )

            if cooldown_active:
                if not self._keys:
                    raise KeysUnavailable("JWKS unavailable and refetch cooldown active")
                raise InvalidToken(f"Key ID {kid} not found in cached JWKS")

            try:
                await self._fetch_jwks()
            except Exception as exc:
                if not self._keys:
                    raise KeysUnavailable(f"Failed to fetch JWKS and no cached keys: {exc}") from exc
                raise KeysUnavailable(
                    f"Key ID {kid} not cached and JWKS fetch failed: {exc}"
                ) from exc

            if kid in self._keys:
                return self._keys[kid]
            raise InvalidToken(f"Key ID {kid} not found in JWKS")

