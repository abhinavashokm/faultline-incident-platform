from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from faultline_auth.errors import AuthConfigurationError


@dataclass(frozen=True)
class AuthSettings:
    """Authentication and JWT verification settings.

    Reads configuration from environment variables prefixed with AUTH_
    (falls back to PROCESSING_AUTH_ for backwards compatibility).
    """

    provider: str
    issuer: str
    audience: str
    jwks_url: str | None = None
    public_key_path: str | None = None
    jwt_key_id: str | None = None
    leeway_seconds: int = 30
    jwks_cache_ttl_seconds: int = 300
    jwks_refetch_cooldown_seconds: int = 30
    jwks_timeout_seconds: float = 3.0

    def __post_init__(self) -> None:
        if not self.provider or not str(self.provider).strip():
            raise AuthConfigurationError("Auth provider is required and must be 'jwks' or 'static'")

        norm_provider = str(self.provider).strip().lower()
        if norm_provider not in ("jwks", "static"):
            raise AuthConfigurationError(
                f"Unsupported auth provider: '{self.provider}'. Must be 'jwks' or 'static'"
            )
        object.__setattr__(self, "provider", norm_provider)

        if not self.issuer or not str(self.issuer).strip():
            raise AuthConfigurationError("Auth issuer is required")

        if not self.audience or not str(self.audience).strip():
            raise AuthConfigurationError("Auth audience is required")

        if norm_provider == "jwks":
            if not self.jwks_url or not str(self.jwks_url).strip():
                raise AuthConfigurationError("jwks_url is required when auth provider is 'jwks'")
        elif norm_provider == "static":
            if not self.public_key_path or not str(self.public_key_path).strip():
                raise AuthConfigurationError(
                    "public_key_path is required when auth provider is 'static'"
                )
            if not self.jwt_key_id or not str(self.jwt_key_id).strip():
                raise AuthConfigurationError(
                    "jwt_key_id is required when auth provider is 'static'"
                )

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> AuthSettings:
        """Construct AuthSettings from environment variables.

        Prefix: AUTH_ (e.g. AUTH_PROVIDER, AUTH_ISSUER).
        Falls back to PROCESSING_AUTH_ prefix if AUTH_ is absent.
        """
        source = os.environ if env is None else env

        def _get(key: str) -> str | None:
            val = source.get(f"AUTH_{key}")
            if val is None or val == "":
                val = source.get(f"PROCESSING_AUTH_{key}")
            return val if (val is not None and val != "") else None

        provider = _get("PROVIDER") or ""
        issuer = _get("ISSUER") or ""
        audience = _get("AUDIENCE") or ""
        jwks_url = _get("JWKS_URL")
        public_key_path = _get("PUBLIC_KEY_PATH")
        jwt_key_id = _get("JWT_KEY_ID")

        leeway_str = _get("LEEWAY_SECONDS")
        if leeway_str is not None:
            try:
                leeway_seconds = int(leeway_str)
            except ValueError as exc:
                raise AuthConfigurationError(
                    f"Invalid integer for AUTH_LEEWAY_SECONDS: '{leeway_str}'"
                ) from exc
        else:
            leeway_seconds = 30

        ttl_str = _get("JWKS_CACHE_TTL_SECONDS")
        if ttl_str is not None:
            try:
                jwks_cache_ttl_seconds = int(ttl_str)
            except ValueError as exc:
                raise AuthConfigurationError(
                    f"Invalid integer for AUTH_JWKS_CACHE_TTL_SECONDS: '{ttl_str}'"
                ) from exc
        else:
            jwks_cache_ttl_seconds = 300

        cooldown_str = _get("JWKS_REFETCH_COOLDOWN_SECONDS")
        if cooldown_str is not None:
            try:
                jwks_refetch_cooldown_seconds = int(cooldown_str)
            except ValueError as exc:
                raise AuthConfigurationError(
                    f"Invalid integer for AUTH_JWKS_REFETCH_COOLDOWN_SECONDS: '{cooldown_str}'"
                ) from exc
        else:
            jwks_refetch_cooldown_seconds = 30

        timeout_str = _get("JWKS_TIMEOUT_SECONDS")
        if timeout_str is not None:
            try:
                jwks_timeout_seconds = float(timeout_str)
            except ValueError as exc:
                raise AuthConfigurationError(
                    f"Invalid float for AUTH_JWKS_TIMEOUT_SECONDS: '{timeout_str}'"
                ) from exc
        else:
            jwks_timeout_seconds = 3.0

        return cls(
            provider=provider,
            issuer=issuer,
            audience=audience,
            jwks_url=jwks_url,
            public_key_path=public_key_path,
            jwt_key_id=jwt_key_id,
            leeway_seconds=leeway_seconds,
            jwks_cache_ttl_seconds=jwks_cache_ttl_seconds,
            jwks_refetch_cooldown_seconds=jwks_refetch_cooldown_seconds,
            jwks_timeout_seconds=jwks_timeout_seconds,
        )

