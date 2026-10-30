from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.projects.models import Project, ProjectApiKey
from app.workspaces.models import Workspace


class InternalKeyRepository:
    """Repository for internal project key lookups.
    Contains database queries only; never commits transactions.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_key_with_project_and_workspace(
        self, public_key: str
    ) -> tuple[ProjectApiKey, Project, Workspace] | None:
        query = (
            select(ProjectApiKey, Project, Workspace)
            .join(Project, ProjectApiKey.project_id == Project.id)
            .join(Workspace, Project.workspace_id == Workspace.id)
            .where(
                ProjectApiKey.public_key == public_key,
                ProjectApiKey.key_type == "ingest",
            )
        )
        result = await self.session.execute(query)
        row = result.first()
        if row is None:
            return None
        return row[0], row[1], row[2]

