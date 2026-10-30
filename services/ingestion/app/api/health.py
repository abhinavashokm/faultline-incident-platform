import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
import redis.asyncio as redis

from app.adapters.kafka import KafkaProducerAdapter
from app.dependencies import get_kafka_producer, get_redis_client

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/healthz", status_code=status.HTTP_200_OK)
async def healthz() -> dict[str, str]:
    """Liveness probe. Checks that process is alive without touching external dependencies."""
    return {"status": "ok"}


@router.get("/readyz", status_code=status.HTTP_200_OK)
async def readyz(
    kafka_producer: Annotated[KafkaProducerAdapter, Depends(get_kafka_producer)],
    redis_client: Annotated[redis.Redis, Depends(get_redis_client)],
) -> dict[str, str]:
    """Readiness probe. Verifies Kafka producer is started and Redis ping succeeds."""
    kafka_ok = False
    redis_ok = False

    try:
        kafka_ok = await kafka_producer.is_healthy()
    except Exception as exc:
        logger.warning("Readiness probe: Kafka check failed: %s", exc)

    try:
        pong = await redis_client.ping()
        redis_ok = bool(pong)
    except Exception as exc:
        logger.warning("Readiness probe: Redis ping failed: %s", exc)

    if kafka_ok and redis_ok:
        return {"status": "ok", "kafka": "ok", "redis": "ok"}

    reasons = []
    if not kafka_ok:
        reasons.append("Kafka producer not running")
    if not redis_ok:
        reasons.append("Redis unavailable")

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Service not ready: {'; '.join(reasons)}",
    )

