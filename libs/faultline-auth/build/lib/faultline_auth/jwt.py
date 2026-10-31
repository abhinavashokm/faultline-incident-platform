import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import jwt

from faultline_auth.context import AuthContext
from faultline_auth.errors import InvalidToken, InvalidWorkspaceClaim, KeysUnavailable
from faultline_auth.keys import KeyProvider

logger = logging.getLogger(__name__)

ALLOWED_ROLES = {"owner", "admin", "member", "viewer"}


class TokenVerifier:
    """Verifies RS256 JWT access tokens against a KeyProvider."""

    def __init__(
        self,
        key_provider: KeyProvider,
        *,
        issuer: str,
        audience: str,
        leeway_seconds: int = 30,
    ) -> None:
        self.key_provider = key_provider
        self.issuer = issuer
        self.audience = audience
        self.leeway_seconds = leeway_seconds

    async def verify(self, token: str) -> AuthContext:
        """Verify an access token and return an AuthContext."""
        # 1. Read unverified header
        try:
            header = jwt.get_unverified_header(token)
        except Exception as exc:
            raise InvalidToken(f"Malformed token header: {exc}") from exc

        alg = header.get("alg")
        kid = header.get("kid")

        if alg != "RS256":
            raise InvalidToken(f"Unsupported algorithm '{alg}': only RS256 is accepted")
        if not kid:
            raise InvalidToken("Token header missing 'kid'")

        # 2. Get key from key provider (KeysUnavailable propagates unchanged)
        key = await self.key_provider.get_key(kid)

        # 3. Decode and verify signature, exp, iss, aud, and required claims
        try:
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=self.issuer,
                audience=self.audience,
                leeway=self.leeway_seconds,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iss": True,
                    "verify_aud": True,
                    "require": ["sub", "exp", "iat", "iss", "aud", "jti", "type"],
                },
            )
        except KeysUnavailable:
            raise
        except jwt.PyJWTError as exc:
            raise InvalidToken(f"JWT verification failed: {exc}") from exc

        # 4. Validate claim values
        if payload.get("type") != "access":
            raise InvalidToken(f"Invalid token type '{payload.get('type')}': must be 'access'")

        try:
            user_id = UUID(str(payload["sub"]))
        except (ValueError, TypeError) as exc:
            raise InvalidToken(f"Invalid sub UUID: {exc}") from exc

        workspace_id: UUID | None = None
        if "workspace_id" in payload and payload["workspace_id"] is not None:
            try:
                workspace_id = UUID(str(payload["workspace_id"]))
            except (ValueError, TypeError) as exc:
                raise InvalidWorkspaceClaim(f"Invalid workspace_id UUID: {exc}") from exc

        session_id: UUID | None = None
        if "sid" in payload and payload["sid"] is not None:
            try:
                session_id = UUID(str(payload["sid"]))
            except (ValueError, TypeError) as exc:
                raise InvalidToken(f"Invalid sid UUID: {exc}") from exc

        role: str | None = None
        if "role" in payload and payload["role"] is not None:
            role_val = str(payload["role"])
            if role_val not in ALLOWED_ROLES:
                raise InvalidToken(
                    f"Invalid role '{role_val}': must be one of {sorted(ALLOWED_ROLES)}"
                )
            role = role_val

        token_id = str(payload["jti"])
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

        return AuthContext(
            user_id=user_id,
            workspace_id=workspace_id,
            role=role,
            session_id=session_id,
            token_id=token_id,
            expires_at=expires_at,
        )

