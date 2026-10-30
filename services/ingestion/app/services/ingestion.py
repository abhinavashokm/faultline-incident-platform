import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from faultline_events import EventEnvelope

from app.adapters.kafka import KafkaProducerAdapter, KafkaPublishError
from app.adapters.key_resolver import (
    InvalidKeyError,
    KeyResolverUnavailableError,
    ProjectKeyResolver,
    ResolvedKey,
)
from app.adapters.redis_limiter import RateLimiter
from app.core.config import settings
from app.core.logging import (
    log_event_accepted,
    log_event_rejected,
    log_kafka_failure,
    mask_key,
)
from app.schemas.event import (
    ErrorEventIngestRequest,
    IngestResponse,
    NormalizedErrorEvent,
)

logger = logging.getLogger(__name__)


class IngestionError(Exception):
    def __init__(
        self,
        detail: str,
        status_code: int,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.retry_after = retry_after


class AuthenticationError(IngestionError):
    def __init__(self, detail: str = "Invalid or revoked project key") -> None:
        super().__init__(detail=detail, status_code=401)


class RateLimitExceededError(IngestionError):
    def __init__(self, retry_after: int = 60, detail: str = "Rate limit exceeded") -> None:
        super().__init__(
            detail=detail,
            status_code=429,
            retry_after=retry_after,
        )


class ServiceUnavailableError(IngestionError):
    def __init__(
        self,
        detail: str = "Service unavailable",
        retry_after: int | None = 5,
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=503,
            retry_after=retry_after,
        )


class IngestionService:
    def __init__(
        self,
        key_resolver: ProjectKeyResolver,
        rate_limiter: RateLimiter,
        kafka_producer: KafkaProducerAdapter,
        concurrency_semaphore: asyncio.Semaphore | None = None,
        topic: str | None = None,
    ) -> None:
        self.key_resolver = key_resolver
        self.rate_limiter = rate_limiter
        self.kafka_producer = kafka_producer
        self.semaphore = concurrency_semaphore or asyncio.Semaphore(
            settings.max_in_flight_publishes
        )
        self.topic = topic or settings.kafka_topic_error_events

    async def ingest_error_event(
        self,
        request: ErrorEventIngestRequest,
        public_key: str | None,
    ) -> IngestResponse:
        key_prefix = mask_key(public_key)

        # 1. Authenticate via public key
        if not public_key or not public_key.strip():
            log_event_rejected(
                logger,
                reason="missing_api_key",
                status_code=401,
                key_prefix=key_prefix,
            )
            raise AuthenticationError("Missing project key header")

        try:
            resolved: ResolvedKey = await self.key_resolver.resolve(public_key)
        except InvalidKeyError as exc:
            log_event_rejected(
                logger,
                reason="invalid_or_revoked_key",
                status_code=401,
                key_prefix=key_prefix,
                details=str(exc),
            )
            raise AuthenticationError("Invalid or revoked project key") from exc
        except KeyResolverUnavailableError as exc:
            log_event_rejected(
                logger,
                reason="key_resolver_unavailable",
                status_code=503,
                key_prefix=key_prefix,
                details=str(exc),
            )
            raise ServiceUnavailableError(
                detail="Key resolution service unavailable",
                retry_after=5,
            ) from exc

        # 2. Rate limiting check (per project)
        allowed, retry_after = await self.rate_limiter.is_allowed(resolved.project_id)
        if not allowed:
            log_event_rejected(
                logger,
                reason="rate_limit_exceeded",
                status_code=429,
                key_prefix=key_prefix,
                details=f"project_id={resolved.project_id} retry_after={retry_after}",
            )
            raise RateLimitExceededError(
                retry_after=retry_after,
                detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
            )

        # 3. Bounded in-flight concurrency (backpressure)
        # Try to acquire semaphore without blocking indefinitely
        try:
            acquired = self.semaphore.locked() is False
            if acquired:
                await self.semaphore.acquire()
            else:
                # If currently locked or saturated, fail fast with 503
                log_event_rejected(
                    logger,
                    reason="backpressure_saturation",
                    status_code=503,
                    key_prefix=key_prefix,
                    details=f"in_flight_publishes_saturated project_id={resolved.project_id}",
                )
                raise ServiceUnavailableError(
                    detail="Server is handling maximum concurrent requests",
                    retry_after=1,
                )
        except IngestionError:
            raise
        except Exception as exc:
            raise ServiceUnavailableError("Server busy", retry_after=1) from exc

        try:
            # 4. Construct server-derived metadata & normalized envelope
            received_at = datetime.now(timezone.utc)
            normalized_payload = NormalizedErrorEvent(
                event_id=request.event_id,
                occurred_at=request.occurred_at,
                exception_type=request.exception_type,
                message=request.message,
                stack_frames=request.stack_frames,
                event_type=request.event_type,
                level=request.level,
                service=request.service,
                route_template=request.route_template,
                http_method=request.http_method,
                status_code=request.status_code,
                environment=request.environment,
                release=request.release,
                user_hash=request.user_hash,
                context=request.context,
            )

            envelope = EventEnvelope[NormalizedErrorEvent](
                schema_version=1,
                event_id=request.event_id,
                workspace_id=resolved.workspace_id,
                project_id=resolved.project_id,
                received_at=received_at,
                payload=normalized_payload,
            )

            envelope_bytes = envelope.model_dump_json().encode("utf-8")
            partition_key = str(resolved.project_id).encode("utf-8")

            # 5. Publish to Kafka and await acknowledgment
            await self.kafka_producer.publish(
                topic=self.topic,
                key=partition_key,
                value=envelope_bytes,
            )

            log_event_accepted(
                logger,
                event_id=str(request.event_id),
                project_id=str(resolved.project_id),
                workspace_id=str(resolved.workspace_id),
            )

            return IngestResponse(
                event_id=request.event_id,
                status="accepted",
            )

        except KafkaPublishError as exc:
            log_kafka_failure(
                logger,
                event_id=str(request.event_id),
                project_id=str(resolved.project_id),
                error=exc,
            )
            raise ServiceUnavailableError(
                detail="Event could not be queued",
                retry_after=5,
            ) from exc
        except Exception as exc:
            log_kafka_failure(
                logger,
                event_id=str(request.event_id),
                project_id=str(resolved.project_id),
                error=exc,
            )
            raise ServiceUnavailableError(
                detail="Event could not be processed",
                retry_after=5,
            ) from exc
        finally:
            self.semaphore.release()

