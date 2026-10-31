from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal, get_principal
from app.core.db import get_session
from app.errors.schemas import (
    EventDetail,
    EventListItem,
    IssueDetail,
    IssueListItem,
    PaginatedResponse,
    UpdateIssueStatusRequest,
)
from app.errors.service import ErrorsHttpService

router = APIRouter(tags=["issues"])


@router.get(
    "/projects/{project_id}/issues",
    response_model=PaginatedResponse[IssueListItem],
)
async def list_issues(
    project_id: UUID,
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: Annotated[str | None, Query()] = None,
    status: Annotated[Literal["unresolved", "resolved", "ignored"] | None, Query()] = None,
) -> PaginatedResponse[IssueListItem]:
    service = ErrorsHttpService(session)
    return await service.list_issues(
        workspace_id=principal.workspace_id,
        project_id=project_id,
        status_filter=status,
        limit=limit,
        cursor_str=cursor,
    )


@router.get(
    "/projects/{project_id}/issues/{issue_id}",
    response_model=IssueDetail,
)
async def get_issue_details(
    project_id: UUID,
    issue_id: UUID,
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> IssueDetail:
    service = ErrorsHttpService(session)
    return await service.get_issue_detail(
        workspace_id=principal.workspace_id,
        project_id=project_id,
        issue_id=issue_id,
    )


@router.get(
    "/projects/{project_id}/issues/{issue_id}/events",
    response_model=PaginatedResponse[EventListItem],
)
async def list_issue_events(
    project_id: UUID,
    issue_id: UUID,
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: Annotated[str | None, Query()] = None,
) -> PaginatedResponse[EventListItem]:
    service = ErrorsHttpService(session)
    return await service.list_issue_events(
        workspace_id=principal.workspace_id,
        project_id=project_id,
        issue_id=issue_id,
        limit=limit,
        cursor_str=cursor,
    )


@router.get(
    "/projects/{project_id}/issues/{issue_id}/events/{event_id}",
    response_model=EventDetail,
)
async def get_event_details(
    project_id: UUID,
    issue_id: UUID,
    event_id: UUID,
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EventDetail:
    service = ErrorsHttpService(session)
    return await service.get_event_detail(
        workspace_id=principal.workspace_id,
        project_id=project_id,
        issue_id=issue_id,
        event_id=event_id,
    )


@router.patch(
    "/projects/{project_id}/issues/{issue_id}",
    response_model=IssueDetail,
)
async def update_issue_status(
    project_id: UUID,
    issue_id: UUID,
    body: UpdateIssueStatusRequest,
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> IssueDetail:
    service = ErrorsHttpService(session)
    return await service.update_issue_status(
        workspace_id=principal.workspace_id,
        project_id=project_id,
        issue_id=issue_id,
        body=body,
        user_id=principal.user_id,
    )

