import asyncio
from typing import Annotated

from fastapi import Depends, Header, Request
import redis.asyncio as redis

from app.adapters.kafka import KafkaProducerAdapter
from app.adapters.key_resolver import ProjectKeyResolver
from app.adapters.redis_limiter import RateLimiter
from app.core.config import settings
from app.services.ingestion import IngestionService


def get_project_key(
    x_faultline_key: Annotated[str | None, Header(alias="X-Faultline-Key")] = None,
    x_project_key: Annotated[str | None, Header(alias="X-Project-Key")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> str | None:
    """Extract project ingest public key from headers.
    Prefers X-Faultline-Key, with fallback to X-Project-Key or Bearer token.
    """
    if x_faultline_key and x_faultline_key.strip():
        return x_faultline_key.strip()
    if x_project_key and x_project_key.strip():
        return x_project_key.strip()
    if authorization and authorization.strip():
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
    return None


def get_kafka_producer(request: Request) -> KafkaProducerAdapter:
    return getattr(request.app.state, "kafka_producer", None)


def get_redis_client(request: Request) -> redis.Redis:
    return getattr(request.app.state, "redis_client", None)


def get_rate_limiter(request: Request) -> RateLimiter:
    return getattr(request.app.state, "rate_limiter", None)


def get_key_resolver(request: Request) -> ProjectKeyResolver:
    return getattr(request.app.state, "key_resolver", None)


def get_concurrency_semaphore(request: Request) -> asyncio.Semaphore:
    if hasattr(request.app.state, "concurrency_semaphore") and request.app.state.concurrency_semaphore is not None:
        return request.app.state.concurrency_semaphore
    return asyncio.Semaphore(settings.max_in_flight_publishes)


def get_ingestion_service(
    key_resolver: Annotated[ProjectKeyResolver, Depends(get_key_resolver)],
    rate_limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    kafka_producer: Annotated[KafkaProducerAdapter, Depends(get_kafka_producer)],
    semaphore: Annotated[asyncio.Semaphore, Depends(get_concurrency_semaphore)],
) -> IngestionService:
    return IngestionService(
        key_resolver=key_resolver,
        rate_limiter=rate_limiter,
        kafka_producer=kafka_producer,
        concurrency_semaphore=semaphore,
    )
