from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies import get_ingestion_service, get_project_key
from app.schemas.performance import (
    PerformanceBatchIngestRequest,
    PerformanceIngestResponse,
)
from app.services.ingestion import IngestionService

router = APIRouter()


@router.post(
    "/ingest/performance",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=PerformanceIngestResponse,
)
async def ingest_performance_batch(
    payload: PerformanceBatchIngestRequest,
    project_api_key: Annotated[str | None, Depends(get_project_key)],
    service: Annotated[IngestionService, Depends(get_ingestion_service)],
) -> PerformanceIngestResponse:
    return await service.ingest_performance_batch(payload, project_api_key=project_api_key)
