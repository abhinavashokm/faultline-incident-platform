import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AuthContext, current_user
from app.core.db import get_session
from app.projects.schemas import (
    ProjectApiKeyResponse,
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectResponse,
    ProjectSettingsResponse,
    ProjectSettingsUpdateRequest,
    ProjectUpdateRequest,
)
from app.projects.service import (
    ApiKeyNotFound,
    DuplicateSlugError,
    InsufficientPermissions,
    ProjectNotFound,
    ProjectService,
)

router = APIRouter()


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=list[ProjectResponse],
)
async def list_projects(
    user: Annotated[AuthContext, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ProjectResponse]:
    service = ProjectService(session)
    try:
        projects = await service.list_projects(
            user_id=user.user_id,
            workspace_id=user.workspace_id,
        )
        return [
            ProjectResponse(
                id=p.id,
                name=p.name,
                slug=p.slug,
                description=p.description,
                platform=p.platform,
                status=p.status,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in projects
        ]
    except ProjectNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        ) from exc


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ProjectCreateResponse,
)
async def create_project(
    payload: ProjectCreateRequest,
    user: Annotated[AuthContext, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectCreateResponse:
    service = ProjectService(session)
    try:
        project, dsn = await service.create_project(
            user_id=user.user_id,
            workspace_id=user.workspace_id,
            payload=payload,
        )
        return ProjectCreateResponse(
            id=project.id,
            name=project.name,
            slug=project.slug,
            description=project.description,
            platform=project.platform,
            status=project.status,
            created_at=project.created_at,
            updated_at=project.updated_at,
            dsn=dsn,
        )
    except InsufficientPermissions as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        ) from exc
    except DuplicateSlugError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A project with this slug already exists in the workspace",
        ) from exc
    except ProjectNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        ) from exc


@router.get(
    "/{project_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProjectResponse,
)
async def get_project(
    project_id: uuid.UUID,
    user: Annotated[AuthContext, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectResponse:
    service = ProjectService(session)
    try:
        project = await service.get_project(
            user_id=user.user_id,
            workspace_id=user.workspace_id,
            project_id=project_id,
        )
        return ProjectResponse(
            id=project.id,
            name=project.name,
            slug=project.slug,
            description=project.description,
            platform=project.platform,
            status=project.status,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
    except ProjectNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        ) from exc


@router.patch(
    "/{project_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProjectResponse,
)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdateRequest,
    user: Annotated[AuthContext, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectResponse:
    service = ProjectService(session)
    try:
        project = await service.update_project(
            user_id=user.user_id,
            workspace_id=user.workspace_id,
            project_id=project_id,
            payload=payload,
        )
        return ProjectResponse(
            id=project.id,
            name=project.name,
            slug=project.slug,
            description=project.description,
            platform=project.platform,
            status=project.status,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
    except InsufficientPermissions as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        ) from exc
    except ProjectNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        ) from exc


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project(
    project_id: uuid.UUID,
    user: Annotated[AuthContext, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    service = ProjectService(session)
    try:
        await service.delete_project(
            user_id=user.user_id,
            workspace_id=user.workspace_id,
            project_id=project_id,
        )
    except InsufficientPermissions as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        ) from exc
    except ProjectNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        ) from exc


@router.get(
    "/{project_id}/settings",
    status_code=status.HTTP_200_OK,
    response_model=ProjectSettingsResponse,
)
async def get_project_settings(
    project_id: uuid.UUID,
    user: Annotated[AuthContext, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectSettingsResponse:
    service = ProjectService(session)
    try:
        settings_obj = await service.get_settings(
            user_id=user.user_id,
            workspace_id=user.workspace_id,
            project_id=project_id,
        )
        return ProjectSettingsResponse(
            project_id=settings_obj.project_id,
            retention_days=settings_obj.retention_days,
            ignored_status_codes=settings_obj.ignored_status_codes or [],
            version=settings_obj.version,
            updated_at=settings_obj.updated_at,
        )
    except ProjectNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        ) from exc


@router.patch(
    "/{project_id}/settings",
    status_code=status.HTTP_200_OK,
    response_model=ProjectSettingsResponse,
)
async def update_project_settings(
    project_id: uuid.UUID,
    payload: ProjectSettingsUpdateRequest,
    user: Annotated[AuthContext, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectSettingsResponse:
    service = ProjectService(session)
    try:
        settings_obj = await service.update_settings(
            user_id=user.user_id,
            workspace_id=user.workspace_id,
            project_id=project_id,
            payload=payload,
        )
        return ProjectSettingsResponse(
            project_id=settings_obj.project_id,
            retention_days=settings_obj.retention_days,
            ignored_status_codes=settings_obj.ignored_status_codes or [],
            version=settings_obj.version,
            updated_at=settings_obj.updated_at,
        )
    except InsufficientPermissions as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        ) from exc
    except ProjectNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        ) from exc


@router.get(
    "/{project_id}/api-key",
    status_code=status.HTTP_200_OK,
    response_model=ProjectApiKeyResponse,
)
async def get_project_api_key(
    project_id: uuid.UUID,
    user: Annotated[AuthContext, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectApiKeyResponse:
    service = ProjectService(session)
    try:
        key, dsn = await service.get_api_key(
            user_id=user.user_id,
            workspace_id=user.workspace_id,
            project_id=project_id,
        )
        return ProjectApiKeyResponse(
            id=key.id,
            key_type=key.key_type,
            dsn=dsn,
            last_used_at=key.last_used_at,
            created_at=key.created_at,
        )
    except (ProjectNotFound, ApiKeyNotFound) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        ) from exc


@router.post(
    "/{project_id}/api-key/rotate",
    status_code=status.HTTP_200_OK,
    response_model=ProjectApiKeyResponse,
)
async def rotate_project_api_key(
    project_id: uuid.UUID,
    user: Annotated[AuthContext, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectApiKeyResponse:
    service = ProjectService(session)
    try:
        key, dsn = await service.rotate_api_key(
            user_id=user.user_id,
            workspace_id=user.workspace_id,
            project_id=project_id,
        )
        return ProjectApiKeyResponse(
            id=key.id,
            key_type=key.key_type,
            dsn=dsn,
            last_used_at=key.last_used_at,
            created_at=key.created_at,
        )
    except InsufficientPermissions as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        ) from exc
    except ProjectNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        ) from exc

