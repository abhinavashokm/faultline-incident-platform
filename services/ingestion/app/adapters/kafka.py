import asyncio
from enum import Enum
import logging
import time
from typing import Protocol
from aiokafka import AIOKafkaProducer

from app.core.config import settings

logger = logging.getLogger(__name__)


class ProducerState(str, Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    FAILED = "FAILED"


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
        connect_timeout_seconds: float | None = None,
        reconnect_cooldown_seconds: float | None = None,
        compression_type: str | None = None,
    ) -> None:
        self.bootstrap_servers = bootstrap_servers or settings.kafka_bootstrap_servers
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.kafka_producer_timeout_seconds
        )
        self.connect_timeout_seconds = (
            connect_timeout_seconds
            if connect_timeout_seconds is not None
            else settings.kafka_connect_timeout_seconds
        )
        self.reconnect_cooldown_seconds = (
            reconnect_cooldown_seconds
            if reconnect_cooldown_seconds is not None
            else settings.kafka_reconnect_cooldown_seconds
        )
        self.compression_type = (
            compression_type
            if compression_type is not None
            else settings.kafka_compression_type
        )
        if self.compression_type == "none":
            self.compression_type = None

        self._producer: AIOKafkaProducer | None = None
        self._state: ProducerState = ProducerState.STOPPED
        self._lock = asyncio.Lock()
        self._last_failure_time: float = 0.0

    @property
    def _started(self) -> bool:
        return self._state == ProducerState.RUNNING

    async def _cleanup_producer(self) -> None:
        """Safely stops and discards any current producer instance."""
        if self._producer is not None:
            try:
                await self._producer.stop()
            except Exception as exc:
                logger.debug("Error stopping stale producer instance: %s", exc)
            finally:
                self._producer = None

    async def start(self) -> None:
        """Connects the producer if not already running. Thread/coroutine-safe."""
        if self._state == ProducerState.RUNNING and self._producer is not None:
            return

        async with self._lock:
            if self._state == ProducerState.RUNNING and self._producer is not None:
                return

            now = time.monotonic()
            elapsed_since_failure = now - self._last_failure_time
            if self._state == ProducerState.FAILED and elapsed_since_failure < self.reconnect_cooldown_seconds:
                remaining = self.reconnect_cooldown_seconds - elapsed_since_failure
                raise KafkaPublishError(
                    f"Kafka producer reconnect cooldown active (retry in {remaining:.1f}s)"
                )

            previous_state = self._state
            self._state = ProducerState.STARTING
            logger.info(
                "Starting AIOKafkaProducer (state: %s -> %s) bootstrap_servers=%s",
                previous_state.value,
                self._state.value,
                self.bootstrap_servers,
            )

            await self._cleanup_producer()

            try:
                producer = AIOKafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    acks="all",
                    enable_idempotence=True,
                    request_timeout_ms=int(self.timeout_seconds * 1000),
                    compression_type=self.compression_type,
                )
                await asyncio.wait_for(producer.start(), timeout=self.connect_timeout_seconds)
                self._producer = producer
                self._state = ProducerState.RUNNING
                logger.info("AIOKafkaProducer started successfully (state: RUNNING)")
            except Exception as exc:
                self._state = ProducerState.FAILED
                self._last_failure_time = time.monotonic()
                await self._cleanup_producer()
                logger.warning(
                    "AIOKafkaProducer failed to start (state: FAILED): %s",
                    exc,
                )
                raise KafkaPublishError(f"Kafka producer failed to start: {exc}") from exc

    async def stop(self) -> None:
        """Safely stops the producer and releases resources."""
        async with self._lock:
            logger.info("Stopping AIOKafkaProducer (current state: %s)", self._state.value)
            await self._cleanup_producer()
            self._state = ProducerState.STOPPED

    async def publish(self, topic: str, key: bytes, value: bytes) -> None:
        """Publishes a message to Kafka, lazy-starting the producer if necessary."""
        if self._state != ProducerState.RUNNING or self._producer is None:
            await self.start()

        if self._producer is None or self._state != ProducerState.RUNNING:
            raise KafkaPublishError("Kafka producer is not running")

        try:
            await asyncio.wait_for(
                self._producer.send_and_wait(topic, value=value, key=key),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            logger.error("Kafka send_and_wait timed out after %.2fs", self.timeout_seconds)
            self._state = ProducerState.FAILED
            self._last_failure_time = time.monotonic()
            raise KafkaPublishError("Kafka send timed out") from exc
        except Exception as exc:
            logger.error("Kafka publish error: %s", exc)
            self._state = ProducerState.FAILED
            self._last_failure_time = time.monotonic()
            raise KafkaPublishError(f"Kafka publish failed: {exc}") from exc

    async def is_healthy(self) -> bool:
        return self._state == ProducerState.RUNNING and self._producer is not None


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

