import logging
import re
import secrets
from typing import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.workspaces.models import Workspace, WorkspaceMember
from app.workspaces.repository import WorkspaceRepository

logger = logging.getLogger(__name__)

RESERVED_SLUGS: frozenset[str] = frozenset(
    {
        "api",
        "admin",
        "app",
        "www",
        "login",
        "signup",
        "settings",
        "auth",
        "health",
        "static",
    }
)


def slugify(name: str) -> str:
    """Generate a clean base slug from a name."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    if not s:
        s = "workspace"
    s = s[:100].rstrip("-")
    if not s:
        s = "workspace"
    return s


def _make_candidate_slug(base_slug: str, is_retry: bool) -> str:
    """Generate a candidate slug, appending 4 random hex chars if retrying or reserved."""
    if not is_retry and base_slug not in RESERVED_SLUGS:
        return base_slug

    suffix = f"-{secrets.token_hex(2)}"
    max_len = 100 - len(suffix)
    prefix = base_slug[:max_len].rstrip("-")
    if not prefix:
        prefix = "workspace"
    return f"{prefix}{suffix}"


async def create_personal_workspace(
    session: AsyncSession, user: User
) -> tuple[Workspace, WorkspaceMember]:
    """Bootstrap a personal workspace and owner membership for a user."""
    repo = WorkspaceRepository(session)
    workspace_name = f"{user.full_name}'s workspace"
    base_slug = slugify(workspace_name)

    max_attempts = 5
    for attempt in range(max_attempts):
        candidate_slug = _make_candidate_slug(base_slug, is_retry=(attempt > 0))

        # Check if slug is known to be taken or reserved
        if candidate_slug in RESERVED_SLUGS:
            continue

        existing = await repo.get_by_slug(candidate_slug)
        if existing is not None:
            continue

        try:
            async with session.begin_nested():
                workspace = Workspace(
                    name=workspace_name,
                    slug=candidate_slug,
                    status="active",
                    created_by=user.id,
                )
                await repo.create_workspace(workspace)

                member = WorkspaceMember(
                    workspace_id=workspace.id,
                    user_id=user.id,
                    role="owner",
                    invited_by=None,
                )
                await repo.create_member(member)
                return workspace, member
        except IntegrityError:
            logger.warning(
                "Slug collision for '%s' on attempt %d; retrying",
                candidate_slug,
                attempt + 1,
            )
            continue

    raise RuntimeError(
        f"Failed to create personal workspace for user {user.id} after {max_attempts} attempts"
    )

