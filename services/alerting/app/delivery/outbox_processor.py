import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.delivery.delivery_repository import DeliveryRepository
from app.delivery.email import EmailSender, SMTPEmailSender, mask_email
from app.delivery.senders import ChannelSender, EmailChannelSender

logger = logging.getLogger(__name__)


class OutboxDeliveryService:
    """Processes pending delivery jobs from the outbox."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        senders: dict[str, ChannelSender] | None = None,
    ) -> None:
        self.session_factory = session_factory
        if senders is not None:
            self.senders = senders
        else:
            default_email_sender = SMTPEmailSender()
            self.senders = {
                "email": EmailChannelSender(default_email_sender),
            }

    async def process_batch(self, limit: int = 50) -> int:
        """Process a single batch of pending deliveries.
        
        Returns the number of processed deliveries.
        """
        async with self.session_factory() as session:
            repo = DeliveryRepository(session)
            deliveries = await repo.get_pending_deliveries(limit=limit)

            if not deliveries:
                return 0

            for delivery in deliveries:
                channel = delivery.channel
                if channel is None:
                    await repo.record_attempt(
                        delivery,
                        status="failure",
                        error_message="Notification channel no longer exists",
                    )
                    await session.commit()
                    continue

                sender = self.senders.get(channel.channel_type)
                if sender is None:
                    logger.warning(
                        "No sender registered for channel_type %r (delivery_id=%s)",
                        channel.channel_type,
                        delivery.id,
                    )
                    await repo.record_attempt(
                        delivery,
                        status="failure",
                        error_message=f"Unsupported channel_type: {channel.channel_type}",
                    )
                    await session.commit()
                    continue

                try:
                    await sender.send(channel, delivery)
                    await repo.record_attempt(
                        delivery,
                        status="success",
                        response_summary="Message sent successfully",
                    )
                    await session.commit()
                    logger.info("Delivery %s succeeded", delivery.id)
                except Exception as exc:
                    error_msg = str(exc)
                    logger.error(
                        "Delivery %s failed to channel %s (%s): %s",
                        delivery.id,
                        channel.id,
                        mask_email(channel.destination) if channel.channel_type == "email" else channel.channel_type,
                        error_msg,
                    )
                    await repo.record_attempt(
                        delivery,
                        status="failure",
                        error_message=error_msg,
                    )
                    await session.commit()

            return len(deliveries)
