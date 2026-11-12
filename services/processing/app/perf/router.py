import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from faultline_auth import Principal, get_principal
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.perf.schemas import EndpointDetailResponse, EndpointsListResponse
from app.perf.service import PerfService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["performance"])


def validate_time_range(from_time: datetime, to_time: datetime) -> tuple[datetime, datetime]:
    """Validate ISO 8601 UTC time range:

    - Must be timezone-aware (converted to UTC)
    - from < to
    - Range <= 7 days
    """
    if from_time.tzinfo is None or to_time.tzinfo is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[{
                "field": "from" if from_time.tzinfo is None else "to",
                "message": "Timestamp must be timezone-aware ISO 8601 UTC",
            }],
        )

    from_utc = from_time.astimezone(timezone.utc)
    to_utc = to_time.astimezone(timezone.utc)

    if from_utc >= to_utc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[{
                "field": "to",
                "message": "to must be greater than from",
            }],
        )

    if (to_utc - from_utc) > timedelta(days=7):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[{
                "field": "to",
                "message": "Time range must not exceed 7 days",
            }],
        )

    return from_utc, to_utc


@router.get(
    "/projects/{project_id}/performance/endpoints",
    response_model=EndpointsListResponse,
)
async def list_endpoints(
    project_id: UUID,
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
    from_time: Annotated[datetime, Query(alias="from", description="ISO 8601 UTC, inclusive")],
    to_time: Annotated[datetime, Query(alias="to", description="ISO 8601 UTC, exclusive")],
    environment: Annotated[str | None, Query(description="Optional environment filter")] = None,
    release: Annotated[str | None, Query(description="Optional release filter")] = None,
) -> EndpointsListResponse:
    from_utc, to_utc = validate_time_range(from_time, to_time)
    service = PerfService(session)
    return await service.list_endpoints(
        workspace_id=principal.workspace_id,
        project_id=project_id,
        from_time=from_utc,
        to_time=to_utc,
        environment=environment,
        release=release,
    )


@router.get(
    "/projects/{project_id}/performance/endpoint-detail",
    response_model=EndpointDetailResponse,
)
async def get_endpoint_detail(
    project_id: UUID,
    route: Annotated[str, Query(description="Normalized route template")],
    method: Annotated[str, Query(description="HTTP method")],
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
    from_time: Annotated[datetime, Query(alias="from", description="ISO 8601 UTC, inclusive")],
    to_time: Annotated[datetime, Query(alias="to", description="ISO 8601 UTC, exclusive")],
    environment: Annotated[str | None, Query(description="Optional environment filter")] = None,
    release: Annotated[str | None, Query(description="Optional release filter")] = None,
) -> EndpointDetailResponse:
    from_utc, to_utc = validate_time_range(from_time, to_time)
    service = PerfService(session)
    return await service.get_endpoint_detail(
        workspace_id=principal.workspace_id,
        project_id=project_id,
        route=route,
        method=method.strip().upper(),
        from_time=from_utc,
        to_time=to_utc,
        environment=environment,
        release=release,
    )
