from typing import Any

from faultline_auth import AuthContext, AuthDependencies, StaticKeyProvider, TokenVerifier
from faultline_auth.errors import InvalidToken

from app.core.config import settings


class _ControlPlaneKeyProvider(StaticKeyProvider):
    """StaticKeyProvider that lazily retrieves settings public key to support runtime configuration."""

    def __init__(self) -> None:
        pass

    @property
    def public_key_pem(self) -> str:  # type: ignore[override]
        return settings.get_jwt_public_key()

    @property
    def kid(self) -> str:  # type: ignore[override]
        return settings.jwt_key_id

    async def get_key(self, kid: str) -> Any:
        if kid != self.kid:
            raise InvalidToken(f"Unknown key ID: {kid}")
        return self.public_key_pem


def build_auth_dependencies() -> AuthDependencies:
    """Build the AuthDependencies instance configured for the Control Plane."""
    provider = _ControlPlaneKeyProvider()
    verifier = TokenVerifier(
        provider,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    return AuthDependencies(verifier)


auth_dependencies = build_auth_dependencies()
current_user = auth_dependencies.current_user()

__all__ = ["auth_dependencies", "current_user", "AuthContext"]
