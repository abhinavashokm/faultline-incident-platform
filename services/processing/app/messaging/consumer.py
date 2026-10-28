import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiokafka import AIOKafkaConsumer

logger = logging.getLogger(__name__)


class PermanentError(Exception):
    """Raised when an unrecoverable error occurs in a message handler.

    The consumer skips the message and commits the offset to avoid poison-pill loops.
    """


async def run_consumer(
    topic: str,
    group_id: str,
    handler: Callable[[bytes], Awaitable[Any]],
    bootstrap_servers: str,
) -> None:
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id=group_id,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )
    await consumer.start()
    logger.info("Kafka consumer started: topic=%s, group_id=%s", topic, group_id)
    try:
        async for msg in consumer:
            try:
                await handler(msg.value)
            except PermanentError as exc:
                logger.warning(
                    "Permanent error processing message at offset %s: %s",
                    msg.offset,
                    exc,
                )
            await consumer.commit()
    finally:
        logger.info("Stopping Kafka consumer...")
        await consumer.stop()
        logger.info("Kafka consumer stopped.")

