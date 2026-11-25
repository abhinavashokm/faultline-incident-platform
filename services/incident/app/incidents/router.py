from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from faultline_auth import Principal, get_principal, http_bearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.incidents.schemas import CreatedIncident, CreateIncidentRequest
from app.incidents.service import IncidentService

router = APIRouter(tags=["incidents"])


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
