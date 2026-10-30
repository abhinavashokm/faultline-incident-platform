import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.internal.repository import InternalKeyRepository
from app.internal.schemas import ProjectKeyResolutionResponse

logger = logging.getLogger(__name__)


def mask_key(key: str | None) -> str:
    """Mask a public key for safe logging, displaying at most a short prefix."""
    if not key:
        return "<none>"
    if len(key) <= 6:
        return key[:2] + "..."
    return key[:6] + "..."


class InternalKeyService:
    """Service owning business rules for internal project key resolution.
    Kept free of HTTP concepts so it can be called by REST or future gRPC handlers.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = InternalKeyRepository(session)

    async def resolve_ingest_key(
        self, public_key: str
    ) -> ProjectKeyResolutionResponse | None:
        cleaned_key = public_key.strip()
        if not cleaned_key:
            return None

        key_masked = mask_key(cleaned_key)
        logger.debug("Resolving ingest key=%s", key_masked)

        record = await self.repository.get_key_with_project_and_workspace(cleaned_key)
        if record is None:
            logger.info("Ingest key resolution failed: key=%s not found", key_masked)
            return None

        api_key, project, workspace = record

        # Rule 1: Key must not be revoked
        if api_key.revoked_at is not None:
            logger.info("Ingest key resolution failed: key=%s is revoked", key_masked)
            return None

        # Rule 2: Project must be active
        if project.status != "active":
            logger.info(
                "Ingest key resolution failed: key=%s project status is %s",
                key_masked,
                project.status,
            )
            return None

        # Rule 3: Workspace must be active
        if workspace.status != "active":
            logger.info(
                "Ingest key resolution failed: key=%s workspace status is %s",
                key_masked,
                workspace.status,
            )
            return None

        return ProjectKeyResolutionResponse(
            workspace_id=api_key.workspace_id,
            project_id=api_key.project_id,
            key_type="ingest",
            active=True,
        )

