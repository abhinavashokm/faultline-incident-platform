import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.internal.dependencies import verify_internal_service_secret
from app.internal.schemas import ProjectKeyResolutionResponse
from app.internal.service import InternalKeyService, mask_key

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_internal_service_secret)])


@router.get(
    "/project-keys/{public_key}",
    status_code=status.HTTP_200_OK,
    response_model=ProjectKeyResolutionResponse,
)
async def resolve_project_key(
    public_key: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectKeyResolutionResponse:
    """Internal endpoint for Ingestion service to resolve an ingest public key."""
    service = InternalKeyService(session)
    result = await service.resolve_ingest_key(public_key)
    if result is None:
        logger.debug(
            "Returning 404 for unresolved ingest key=%s",
            mask_key(public_key),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project key not found",
        )
    return result

