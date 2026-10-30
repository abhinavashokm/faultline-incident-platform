from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies import get_ingestion_service, get_project_key
from app.schemas.event import ErrorEventIngestRequest, IngestResponse
from app.services.ingestion import IngestionService

router = APIRouter()


@router.post(
    "/events",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestResponse,
)
async def ingest_error_event(
    payload: ErrorEventIngestRequest,
    public_key: Annotated[str | None, Depends(get_project_key)],
    service: Annotated[IngestionService, Depends(get_ingestion_service)],
) -> IngestResponse:
    return await service.ingest_error_event(payload, public_key=public_key)

