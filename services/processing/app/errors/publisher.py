import asyncio
import logging
from typing import Protocol
from uuid import UUID

from aiokafka import AIOKafkaProducer
from faultline_events import IssueCreatedEvent, TOPIC_ISSUE_EVENTS

from app.core.config import settings

logger = logging.getLogger(__name__)


class IssueEventPublisher(Protocol):
    """Interface for publishing issue events."""

    async def publish_issue_created(self, event: IssueCreatedEvent) -> None:
        """Publish an issue.created event to the issue-events topic."""
        ...


class AIOKafkaIssueEventPublisher:
    """aiokafka-backed issue event publisher with retry and backoff."""

    def __init__(
        self,
        bootstrap_servers: str | None = None,
        topic: str | None = None,
        max_retries: int | None = None,
        backoff_base: float | None = None,
        backoff_cap: float | None = None,
        producer: AIOKafkaProducer | None = None,
    ) -> None:
        self.bootstrap_servers = bootstrap_servers or settings.kafka_bootstrap_servers
        self.topic = topic or settings.issue_events_topic or TOPIC_ISSUE_EVENTS
        self.max_retries = max_retries if max_retries is not None else settings.max_retries
        self.backoff_base = backoff_base if backoff_base is not None else settings.backoff_base
        self.backoff_cap = backoff_cap if backoff_cap is not None else settings.backoff_cap
        self._producer = producer
        self._started = False
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._lock:
            if not self._started:
                if self._producer is None:
                    self._producer = AIOKafkaProducer(
                        bootstrap_servers=self.bootstrap_servers,
                        acks="all",
                        enable_idempotence=True,
                    )
                await self._producer.start()
                self._started = True
                logger.info("AIOKafkaIssueEventPublisher started for topic %s", self.topic)

    async def stop(self) -> None:
        async with self._lock:
            if self._started and self._producer:
                await self._producer.stop()
                self._started = False
                logger.info("AIOKafkaIssueEventPublisher stopped")

    async def publish_issue_created(self, event: IssueCreatedEvent) -> None:
        """Publish issue.created with retry and exponential backoff.
        
        The message key is issue_id as a string. event_id is preserved on retries.
        """
        if not self._started:
            await self.start()

        assert self._producer is not None
        key = str(event.payload.issue_id).encode("utf-8")
        value = event.model_dump_json().encode("utf-8")

        attempt = 0
        while True:
            try:
                await self._producer.send_and_wait(
                    topic=self.topic,
                    key=key,
                    value=value,
                )
                logger.info(
                    "Published issue.created event: event_id=%s issue_id=%s project_id=%s",
                    event.event_id,
                    event.payload.issue_id,
                    event.project_id,
                )
                return
            except Exception as exc:
                attempt += 1
                if attempt > self.max_retries:
                    logger.error(
                        "Failed to publish issue.created event after %d attempts: event_id=%s issue_id=%s: %s",
                        self.max_retries,
                        event.event_id,
                        event.payload.issue_id,
                        exc,
                    )
                    raise
                backoff = min(self.backoff_base * (2 ** (attempt - 1)), self.backoff_cap)
                logger.warning(
                    "Transient publish error (attempt %d/%d), retrying in %.2fs: event_id=%s issue_id=%s: %s",
                    attempt,
                    self.max_retries,
                    backoff,
                    event.event_id,
                    event.payload.issue_id,
                    exc,
                )
                await asyncio.sleep(backoff)
