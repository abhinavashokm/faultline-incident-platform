import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.projects.models import Project, ProjectApiKey, ProjectSettings


class ProjectRepository:
    """Repository for project, project settings and API key data access.
    Queries only; never commits transactions.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_projects(self, workspace_id: uuid.UUID) -> Sequence[Project]:
        query = (
            select(Project)
            .where(
                Project.workspace_id == workspace_id,
                Project.status == "active",
            )
            .order_by(Project.created_at.desc(), Project.id.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_project(
        self, workspace_id: uuid.UUID, project_id: uuid.UUID
    ) -> Project | None:
        query = select(Project).where(
            Project.workspace_id == workspace_id,
            Project.id == project_id,
            Project.status == "active",
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_project_for_update(
        self, workspace_id: uuid.UUID, project_id: uuid.UUID
    ) -> Project | None:
        query = (
            select(Project)
            .where(
                Project.workspace_id == workspace_id,
                Project.id == project_id,
                Project.status == "active",
            )
            .with_for_update()
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_project(self, project: Project) -> Project:
        self.session.add(project)
        await self.session.flush()
        return project

    async def create_settings(self, settings: ProjectSettings) -> ProjectSettings:
        self.session.add(settings)
        await self.session.flush()
        return settings

    async def create_api_key(self, api_key: ProjectApiKey) -> ProjectApiKey:
        self.session.add(api_key)
        await self.session.flush()
        return api_key

    async def get_settings(
        self, workspace_id: uuid.UUID, project_id: uuid.UUID
    ) -> ProjectSettings | None:
        query = select(ProjectSettings).where(
            ProjectSettings.workspace_id == workspace_id,
            ProjectSettings.project_id == project_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_settings(
        self, workspace_id: uuid.UUID, project_id: uuid.UUID, values: dict[str, Any]
    ) -> ProjectSettings | None:
        stmt = (
            update(ProjectSettings)
            .where(
                ProjectSettings.workspace_id == workspace_id,
                ProjectSettings.project_id == project_id,
            )
            .values(
                version=ProjectSettings.version + 1,
                **values,
            )
            .returning(ProjectSettings)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_ingest_key(
        self, workspace_id: uuid.UUID, project_id: uuid.UUID
    ) -> ProjectApiKey | None:
        query = select(ProjectApiKey).where(
            ProjectApiKey.workspace_id == workspace_id,
            ProjectApiKey.project_id == project_id,
            ProjectApiKey.key_type == "ingest",
            ProjectApiKey.revoked_at.is_(None),
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def revoke_active_ingest_keys(
        self, workspace_id: uuid.UUID, project_id: uuid.UUID, revoked_at: datetime
    ) -> int:
        stmt = (
            update(ProjectApiKey)
            .where(
                ProjectApiKey.workspace_id == workspace_id,
                ProjectApiKey.project_id == project_id,
                ProjectApiKey.key_type == "ingest",
                ProjectApiKey.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
        result = await self.session.execute(stmt)
        return int(result.rowcount)  # type: ignore[attr-defined]

