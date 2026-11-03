from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from faultline_auth.context import AuthContext


@dataclass(frozen=True)
class Principal:
    """Authenticated principal representing caller identity and active workspace context."""

    user_id: UUID
    workspace_id: UUID
    session_id: UUID | None = None
    role: str | None = None

    @classmethod
    def from_context(cls, ctx: AuthContext) -> Principal:
        """Create a Principal from an AuthContext.

        Raises ValueError if ctx.workspace_id is None.
        """
        if ctx.workspace_id is None:
            raise ValueError("AuthContext missing workspace_id: tenant context is required")
        return cls(
            user_id=ctx.user_id,
            workspace_id=ctx.workspace_id,
            session_id=ctx.session_id,
            role=ctx.role,
        )

