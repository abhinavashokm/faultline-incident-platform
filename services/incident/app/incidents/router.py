from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from faultline_auth import Principal, get_principal, http_bearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.incidents.schemas import (
    CreatedIncident,
    CreateIncidentRequest,
    IncidentDetail,
    IncidentListItem,
    UpdateIncidentDetailsRequest,
)
from app.incidents.service import IncidentService

router = APIRouter(tags=["incidents"])


@router.get("/projects/{project_id}/incidents", response_model=list[IncidentListItem])
async def list_incidents(
    project_id: UUID,
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[IncidentListItem]:
    service = IncidentService(
        session, request.app.state.http_client, request.app.state.settings
    )
    return await service.list_for_project(project_id, principal, credentials.credentials)


@router.post(
    "/projects/{project_id}/incidents",
    response_model=CreatedIncident,
    status_code=status.HTTP_201_CREATED,
)
async def create_incident(
    project_id: UUID,
    payload: CreateIncidentRequest,
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CreatedIncident:
    service = IncidentService(
        session, request.app.state.http_client, request.app.state.settings
    )
    return await service.create(project_id, payload, principal, credentials.credentials)


@router.get("/projects/{project_id}/incidents/{incident_id}", response_model=IncidentDetail)
async def get_incident(
    project_id: UUID,
    incident_id: UUID,
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> IncidentDetail:
    service = IncidentService(
        session, request.app.state.http_client, request.app.state.settings
    )
    return await service.get_detail(project_id, incident_id, principal, credentials.credentials)


@router.patch(
    "/projects/{project_id}/incidents/{incident_id}/details",
    response_model=CreatedIncident,
)
async def update_incident_details(
    project_id: UUID,
    incident_id: UUID,
    payload: UpdateIncidentDetailsRequest,
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CreatedIncident:
    service = IncidentService(
        session, request.app.state.http_client, request.app.state.settings
    )
    return await service.update_details(
        project_id, incident_id, payload, principal, credentials.credentials
    )


@router.delete(
    "/projects/{project_id}/incidents/{incident_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_incident(
    project_id: UUID,
    incident_id: UUID,
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    service = IncidentService(
        session, request.app.state.http_client, request.app.state.settings
    )
    await service.delete_incident(project_id, incident_id, principal, credentials.credentials)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
