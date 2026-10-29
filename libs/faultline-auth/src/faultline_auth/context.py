from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class AuthContext:
    """Authenticated context extracted from a verified access token."""

    user_id: UUID
    workspace_id: UUID | None
    role: str | None
    session_id: UUID | None
    token_id: str
    expires_at: datetime

