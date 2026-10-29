import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.workspaces.models import Workspace, WorkspaceMember


class WorkspaceRepository:
    """Repository for workspace and membership data access. Queries only, never commits."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_workspace(self, workspace: Workspace) -> Workspace:
        self.session.add(workspace)
        await self.session.flush()
        return workspace

    async def create_member(self, member: WorkspaceMember) -> WorkspaceMember:
        self.session.add(member)
        await self.session.flush()
        return member

    async def get_by_slug(self, slug: str) -> Workspace | None:
        query = select(Workspace).where(Workspace.slug == slug)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_memberships(
        self, user_id: uuid.UUID
    ) -> Sequence[tuple[WorkspaceMember, Workspace]]:
        query = (
            select(WorkspaceMember, Workspace)
            .join(Workspace, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(WorkspaceMember.created_at.asc())
        )
        result = await self.session.execute(query)
        return [(row[0], row[1]) for row in result.all()]

    async def get_membership(
        self, user_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> tuple[WorkspaceMember, Workspace] | None:
        query = (
            select(WorkspaceMember, Workspace)
            .join(Workspace, WorkspaceMember.workspace_id == Workspace.id)
            .where(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.workspace_id == workspace_id,
            )
        )
        result = await self.session.execute(query)
        row = result.first()
        return (row[0], row[1]) if row is not None else None
