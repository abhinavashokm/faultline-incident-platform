import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiokafka import AIOKafkaConsumer, TopicPartition

from app.core.config import settings

logger = logging.getLogger(__name__)


class PermanentError(Exception):
    """Raised when an unrecoverable error occurs in a message handler.

    The consumer skips the message and commits the offset to avoid poison-pill loops.
    """


async def run_consumer(
    topic: str,
    group_id: str,
    handler: Callable[[bytes, str, int, int], Awaitable[None]],
    bootstrap_servers: str,
    stop_event: asyncio.Event | None = None,
    consumer: Any | None = None,
) -> None:
    """Run single-message Kafka consumer with retry backoff and offset commit after DB transaction."""
    if stop_event is None:
        stop_event = asyncio.Event()

    created_internally = consumer is None
    if created_internally:
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )

    logger.info(
        "Starting Kafka consumer: topic=%s group_id=%s bootstrap_servers=%s",
        topic,
        group_id,
        bootstrap_servers,
    )
    await consumer.start()
    logger.info("Kafka consumer started successfully")

    try:
        while not stop_event.is_set():
            try:
                msg = await asyncio.wait_for(consumer.getone(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                if stop_event.is_set():
                    break
                logger.error("Error reading from Kafka: %s", exc)
                await asyncio.sleep(0.5)
                continue

            tp = TopicPartition(msg.topic, msg.partition)
            attempt = 0

            while not stop_event.is_set():
                try:
                    await handler(msg.value, msg.topic, msg.partition, msg.offset)
                    # Commit offset only after successful processing
                    try:
                        await consumer.commit({tp: msg.offset + 1})
                    except Exception as commit_exc:
                        logger.warning(
                            "Offset commit failed for topic=%s partition=%d offset=%d: %s",
                            msg.topic,
                            msg.partition,
                            msg.offset + 1,
                            commit_exc,
                        )
                    break
                except PermanentError as exc:
                    logger.warning(
                        "Permanent error processing message on topic=%s partition=%d offset=%d: %s",
                        msg.topic,
                        msg.partition,
                        msg.offset,
                        exc,
                    )
                    # Skip message and commit offset to avoid poison-pill loop
                    try:
                        await consumer.commit({tp: msg.offset + 1})
                    except Exception as commit_exc:
                        logger.warning(
                            "Offset commit failed after PermanentError for topic=%s partition=%d offset=%d: %s",
                            msg.topic,
                            msg.partition,
                            msg.offset + 1,
                            commit_exc,
                        )
                    break
                except Exception as exc:
                    attempt += 1
                    if attempt >= settings.max_retries:
                        logger.error(
                            "Exhausted %d retries for message on topic=%s partition=%d offset=%d: %s. Stopping consumer. "
                            # TODO: Implement Dead-Letter Queue (DLQ) publishing for exhausted messages.
                            "TODO: Dead-letter queue support will be added in a future update.",
                            settings.max_retries,
                            msg.topic,
                            msg.partition,
                            msg.offset,
                            exc,
                        )
                        stop_event.set()
                        break

                    backoff = min(
                        settings.backoff_base * (2 ** (attempt - 1)),
                        settings.backoff_cap,
                    )
                    logger.warning(
                        "Transient error on topic=%s partition=%d offset=%d (attempt %d/%d): %s. Backing off %.2fs",
                        msg.topic,
                        msg.partition,
                        msg.offset,
                        attempt,
                        settings.max_retries,
                        exc,
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                    consumer.seek(tp, msg.offset)
                    try:
                        msg = await consumer.getone()
                    except Exception as refetch_exc:
                        logger.error("Failed to re-fetch message after seek: %s", refetch_exc)
                        stop_event.set()
                        break

    finally:
        logger.info("Stopping Kafka consumer...")
        try:
            await consumer.stop()
        except Exception as exc:
            logger.warning("Error stopping Kafka consumer: %s", exc)
        logger.info("Kafka consumer stopped.")
