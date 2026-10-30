import logging
import secrets
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.projects.models import Project, ProjectApiKey, ProjectSettings
from app.projects.repository import ProjectRepository
from app.projects.schemas import (
    ProjectCreateRequest,
    ProjectSettingsUpdateRequest,
    ProjectUpdateRequest,
)
from app.workspaces.models import WorkspaceMember
from app.workspaces.repository import WorkspaceRepository

logger = logging.getLogger(__name__)


class ProjectError(Exception):
    """Base exception for project service errors."""


class ProjectNotFound(ProjectError):
    """Raised when a project is not found or is outside the active workspace or is archived."""


class DuplicateSlugError(ProjectError):
    """Raised when a project slug already exists within the workspace."""


class InsufficientPermissions(ProjectError):
    """Raised when a workspace member does not have permissions to perform a mutation."""


class ApiKeyNotFound(ProjectError):
    """Raised when an active API key is not found for the project."""


class ProjectService:
    """Service owning project business rules and database transactions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = ProjectRepository(session)

    async def _ensure_membership(
        self, user_id: uuid.UUID, workspace_id: uuid.UUID | None
    ) -> WorkspaceMember:
        if workspace_id is None:
            raise ProjectNotFound("Project not found")
        workspace_repo = WorkspaceRepository(self.session)
        membership = await workspace_repo.get_membership(user_id, workspace_id)
        if membership is None:
            raise ProjectNotFound("Project not found")
        member, _ = membership
        return member

    def _ensure_mutation_allowed(self, member: WorkspaceMember) -> None:
        if member.role not in ("owner", "admin"):
            raise InsufficientPermissions("Insufficient permissions")

    def _build_dsn(self, public_key: str, project_id: uuid.UUID) -> str:
        return f"{settings.dsn_scheme}://{public_key}@{settings.dsn_host}/{project_id}"

    async def list_projects(
        self, user_id: uuid.UUID, workspace_id: uuid.UUID | None
    ) -> Sequence[Project]:
        await self._ensure_membership(user_id, workspace_id)
        assert workspace_id is not None
        return await self.repository.list_projects(workspace_id)

    async def create_project(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID | None,
        payload: ProjectCreateRequest,
    ) -> tuple[Project, str]:
        project_id = uuid.uuid4()
        public_key = secrets.token_hex(16)
        now = datetime.now(timezone.utc)

        try:
            async with self.session.begin():
                member = await self._ensure_membership(user_id, workspace_id)
                self._ensure_mutation_allowed(member)
                assert workspace_id is not None

                project = Project(
                    id=project_id,
                    workspace_id=workspace_id,
                    name=payload.name,
                    slug=payload.slug,
                    description=payload.description,
                    platform=payload.platform,
                    status="active",
                    created_by=user_id,
                    created_at=now,
                    updated_at=now,
                )
                await self.repository.create_project(project)

                settings_obj = ProjectSettings(
                    id=uuid.uuid4(),
                    workspace_id=workspace_id,
                    project_id=project_id,
                    retention_days=30,
                    ignored_status_codes=None,
                    version=1,
                    updated_by=user_id,
                    created_at=now,
                    updated_at=now,
                )
                await self.repository.create_settings(settings_obj)

                api_key = ProjectApiKey(
                    id=uuid.uuid4(),
                    workspace_id=workspace_id,
                    project_id=project_id,
                    key_type="ingest",
                    public_key=public_key,
                    key_hash=None,
                    key_prefix=None,
                    created_by=user_id,
                    created_at=now,
                )
                await self.repository.create_api_key(api_key)
        except IntegrityError as exc:
            logger.info("Project creation conflict for slug '%s'", payload.slug)
            raise DuplicateSlugError(
                "A project with this slug already exists in the workspace"
            ) from exc

        dsn = self._build_dsn(public_key, project_id)
        return project, dsn

    async def get_project(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID | None,
        project_id: uuid.UUID,
    ) -> Project:
        await self._ensure_membership(user_id, workspace_id)
        assert workspace_id is not None

        project = await self.repository.get_project(workspace_id, project_id)
        if project is None or project.status != "active":
            raise ProjectNotFound("Project not found")
        return project

    async def update_project(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID | None,
        project_id: uuid.UUID,
        payload: ProjectUpdateRequest,
    ) -> Project:
        async with self.session.begin():
            member = await self._ensure_membership(user_id, workspace_id)
            self._ensure_mutation_allowed(member)
            assert workspace_id is not None

            project = await self.repository.get_project_for_update(workspace_id, project_id)
            if project is None or project.status != "active":
                raise ProjectNotFound("Project not found")

            if payload.name is not None:
                project.name = payload.name
            if "description" in payload.model_fields_set:
                project.description = payload.description

            project.updated_at = datetime.now(timezone.utc)
            await self.session.flush()

        return project

    async def delete_project(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID | None,
        project_id: uuid.UUID,
    ) -> None:
        async with self.session.begin():
            member = await self._ensure_membership(user_id, workspace_id)
            self._ensure_mutation_allowed(member)
            assert workspace_id is not None

            project = await self.repository.get_project_for_update(workspace_id, project_id)
            if project is None or project.status != "active":
                raise ProjectNotFound("Project not found")

            now = datetime.now(timezone.utc)
            project.status = "archived"
            project.archived_at = now
            project.archived_by = user_id
            project.updated_at = now
            await self.session.flush()

    async def get_settings(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID | None,
        project_id: uuid.UUID,
    ) -> ProjectSettings:
        await self._ensure_membership(user_id, workspace_id)
        assert workspace_id is not None

        project = await self.repository.get_project(workspace_id, project_id)
        if project is None or project.status != "active":
            raise ProjectNotFound("Project not found")

        project_settings = await self.repository.get_settings(workspace_id, project_id)
        if project_settings is None:
            raise ProjectNotFound("Project not found")
        return project_settings

    async def update_settings(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID | None,
        project_id: uuid.UUID,
        payload: ProjectSettingsUpdateRequest,
    ) -> ProjectSettings:
        async with self.session.begin():
            member = await self._ensure_membership(user_id, workspace_id)
            self._ensure_mutation_allowed(member)
            assert workspace_id is not None

            project = await self.repository.get_project_for_update(workspace_id, project_id)
            if project is None or project.status != "active":
                raise ProjectNotFound("Project not found")

            update_values: dict[str, Any] = {
                "updated_by": user_id,
                "updated_at": datetime.now(timezone.utc),
            }
            if "retention_days" in payload.model_fields_set:
                update_values["retention_days"] = payload.retention_days
            if "ignored_status_codes" in payload.model_fields_set:
                update_values["ignored_status_codes"] = payload.ignored_status_codes

            updated_settings = await self.repository.update_settings(
                workspace_id, project_id, update_values
            )
            if updated_settings is None:
                raise ProjectNotFound("Project not found")

        return updated_settings

    async def get_api_key(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID | None,
        project_id: uuid.UUID,
    ) -> tuple[ProjectApiKey, str]:
        await self._ensure_membership(user_id, workspace_id)
        assert workspace_id is not None

        project = await self.repository.get_project(workspace_id, project_id)
        if project is None or project.status != "active":
            raise ProjectNotFound("Project not found")

        key = await self.repository.get_active_ingest_key(workspace_id, project_id)
        if key is None or not key.public_key:
            raise ApiKeyNotFound("Project not found")

        dsn = self._build_dsn(key.public_key, project_id)
        return key, dsn

    async def rotate_api_key(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID | None,
        project_id: uuid.UUID,
    ) -> tuple[ProjectApiKey, str]:
        now = datetime.now(timezone.utc)
        new_public_key = secrets.token_hex(16)

        async with self.session.begin():
            member = await self._ensure_membership(user_id, workspace_id)
            self._ensure_mutation_allowed(member)
            assert workspace_id is not None

            project = await self.repository.get_project_for_update(workspace_id, project_id)
            if project is None or project.status != "active":
                raise ProjectNotFound("Project not found")

            # Revoke existing active ingest keys immediately
            await self.repository.revoke_active_ingest_keys(
                workspace_id, project_id, revoked_at=now
            )

            # Insert new ingest key
            new_key = ProjectApiKey(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                project_id=project_id,
                key_type="ingest",
                public_key=new_public_key,
                key_hash=None,
                key_prefix=None,
                created_by=user_id,
                created_at=now,
            )
            await self.repository.create_api_key(new_key)

        dsn = self._build_dsn(new_public_key, project_id)
        return new_key, dsn

        dsn = self._build_dsn(new_public_key, project_id)
        return new_key, dsn

