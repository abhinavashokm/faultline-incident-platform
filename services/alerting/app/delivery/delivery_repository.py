import logging
import uuid
from datetime import datetime
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.delivery.models import Delivery, DeliveryAttempt, NotificationChannel

logger = logging.getLogger(__name__)


class DeliveryRepository:
    """Repository for querying and updating deliveries outbox and attempts."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_pending_deliveries(self, limit: int = 50) -> Sequence[Delivery]:
        """Fetch pending deliveries with channel preloaded, ordered by created_at."""
        query = (
            select(Delivery)
            .where(Delivery.status == "pending")
            .options(selectinload(Delivery.channel))
            .order_by(Delivery.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def record_attempt(
        self,
        delivery: Delivery,
        status: str,
        error_message: str | None = None,
        response_summary: str | None = None,
    ) -> None:
        """Record attempt in delivery_attempts and update delivery status."""
        delivery.attempt_count += 1
        now = datetime.utcnow()

        attempt = DeliveryAttempt(
            id=uuid.uuid4(),
            delivery_id=delivery.id,
            attempt_number=delivery.attempt_count,
            status=status,
            response_summary=response_summary,
            error_message=error_message,
            started_at=now,
            finished_at=now,
        )
        self.session.add(attempt)

        if status == "success":
            delivery.status = "delivered"
            delivery.delivered_at = now
            delivery.last_error = None
        else:
            delivery.status = "failed"
            delivery.last_error = error_message

        await self.session.flush()
