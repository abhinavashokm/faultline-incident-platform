from __future__ import annotations

import logging

from faultline_auth.errors import AuthConfigurationError
from faultline_auth.jwt import TokenVerifier
from faultline_auth.keys import JwksKeyProvider, KeyProvider, StaticKeyProvider
from faultline_auth.settings import AuthSettings

logger = logging.getLogger(__name__)

_token_verifier: TokenVerifier | None = None


def build_token_verifier(settings: AuthSettings) -> TokenVerifier:
    """Build a TokenVerifier from AuthSettings.

    Raises AuthConfigurationError on configuration or file read errors to fail closed.
    """
    key_provider: KeyProvider

    if settings.provider == "static":
        if not settings.public_key_path:
            raise AuthConfigurationError("public_key_path is required when provider is 'static'")
        if not settings.jwt_key_id:
            raise AuthConfigurationError("jwt_key_id is required when provider is 'static'")

        try:
            with open(settings.public_key_path, "r", encoding="utf-8") as f:
                public_pem = f.read()
        except FileNotFoundError as exc:
            raise AuthConfigurationError(
                f"Public key file not found: {settings.public_key_path}"
            ) from exc
        except Exception as exc:
            raise AuthConfigurationError(
                f"Failed to read public key from {settings.public_key_path}: {exc}"
            ) from exc

        if not public_pem.strip():
            raise AuthConfigurationError(
                f"Public key file is empty: {settings.public_key_path}"
            )

        key_provider = StaticKeyProvider(
            public_key_pem=public_pem,
            kid=settings.jwt_key_id,
        )

    elif settings.provider == "jwks":
        if not settings.jwks_url:
            raise AuthConfigurationError("jwks_url is required when provider is 'jwks'")

        key_provider = JwksKeyProvider(
            jwks_url=settings.jwks_url,
            cache_ttl_seconds=settings.jwks_cache_ttl_seconds,
            refetch_cooldown_seconds=settings.jwks_refetch_cooldown_seconds,
            timeout_seconds=settings.jwks_timeout_seconds,
        )

    else:
        raise AuthConfigurationError(f"Unsupported auth provider: '{settings.provider}'")

    return TokenVerifier(
        key_provider=key_provider,
        issuer=settings.issuer,
        audience=settings.audience,
        leeway_seconds=settings.leeway_seconds,
    )


def configure_auth(settings: AuthSettings | None = None) -> TokenVerifier:
    """Explicitly build and cache the process-wide TokenVerifier (e.g. at application startup).

    Raises AuthConfigurationError if configuration is missing or invalid.
    """
    global _token_verifier
    if settings is None:
        settings = AuthSettings.from_env()
    _token_verifier = build_token_verifier(settings)
    return _token_verifier


def get_token_verifier() -> TokenVerifier:
    """Retrieve the process-wide cached TokenVerifier, lazily building it from environment on first call."""
    global _token_verifier
    if _token_verifier is None:
        settings = AuthSettings.from_env()
        _token_verifier = build_token_verifier(settings)
    return _token_verifier


def reset_auth_cache() -> None:
    """Clear the cached TokenVerifier instance (useful for tests and reloads)."""
    global _token_verifier
    _token_verifier = None

