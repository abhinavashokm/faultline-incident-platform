import asyncio
import logging
from typing import Protocol
from aiokafka import AIOKafkaProducer

from app.core.config import settings

logger = logging.getLogger(__name__)


class KafkaPublishError(Exception):
    """Raised when publishing to Kafka fails or times out."""


class KafkaProducerAdapter(Protocol):
    async def start(self) -> None:
        ...

    async def stop(self) -> None:
        ...

    async def publish(self, topic: str, key: bytes, value: bytes) -> None:
        ...

    async def is_healthy(self) -> bool:
        ...


class AIOKafkaProducerAdapter:
    def __init__(
        self,
        bootstrap_servers: str | None = None,
        timeout_seconds: float | None = None,
        compression_type: str | None = None,
    ) -> None:
        self.bootstrap_servers = bootstrap_servers or settings.kafka_bootstrap_servers
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.kafka_producer_timeout_seconds
        )
        self.compression_type = (
            compression_type
            if compression_type is not None
            else settings.kafka_compression_type
        )
        if self.compression_type == "none":
            self.compression_type = None

        self._producer: AIOKafkaProducer | None = None
        self._started = False

    async def start(self) -> None:
        if self._started and self._producer is not None:
            return

        logger.info(
            "Starting AIOKafkaProducer with bootstrap_servers=%s, acks=all, idempotence=True",
            self.bootstrap_servers,
        )
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            acks="all",
            enable_idempotence=True,
            request_timeout_ms=int(self.timeout_seconds * 1000),
            compression_type=self.compression_type,
        )
        await self._producer.start()
        self._started = True

    async def stop(self) -> None:
        if self._producer is not None and self._started:
            logger.info("Stopping AIOKafkaProducer")
            await self._producer.stop()
            self._started = False
            self._producer = None

    async def publish(self, topic: str, key: bytes, value: bytes) -> None:
        if not self._started or self._producer is None:
            raise KafkaPublishError("Kafka producer is not running")

        try:
            await asyncio.wait_for(
                self._producer.send_and_wait(topic, value=value, key=key),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            logger.error("Kafka send_and_wait timed out after %.2fs", self.timeout_seconds)
            raise KafkaPublishError("Kafka send timed out") from exc
        except Exception as exc:
            logger.error("Kafka publish error: %s", exc)
            raise KafkaPublishError(f"Kafka publish failed: {exc}") from exc

    async def is_healthy(self) -> bool:
        return self._started and self._producer is not None


class FakeKafkaProducer:
    """In-memory fake Kafka producer for unit and integration testing."""

    def __init__(self) -> None:
        self.published_messages: list[tuple[str, bytes, bytes]] = []
        self._started = False
        self.should_fail = False
        self.failure_exception: Exception | None = None

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        self._started = False

    async def publish(self, topic: str, key: bytes, value: bytes) -> None:
        if not self._started:
            raise KafkaPublishError("Producer is not started")
        if self.should_fail:
            exc = self.failure_exception or KafkaPublishError("Simulated Kafka failure")
            raise exc
        self.published_messages.append((topic, key, value))

    async def is_healthy(self) -> bool:
        return self._started and not self.should_fail

