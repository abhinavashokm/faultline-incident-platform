import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import redis.asyncio as redis

from app.adapters.kafka import AIOKafkaProducerAdapter
from app.adapters.key_resolver import CachedHttpProjectKeyResolver
from app.adapters.redis_limiter import RedisRateLimiter
from app.api.events import router as events_router
from app.api.health import router as health_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import MaxBodySizeMiddleware, RequestIDMiddleware
from app.services.ingestion import IngestionError

setup_logging(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Initializing Ingestion Service resources...")

    # 1. Initialize Redis connection pool
    redis_client = redis.from_url(
        settings.redis_url,
        socket_timeout=settings.redis_timeout_seconds,
        decode_responses=True,
    )

    # 2. Initialize HTTP client for Control Plane calls
    http_client = httpx.AsyncClient()

    # 3. Initialize Kafka producer
    kafka_producer = AIOKafkaProducerAdapter(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        timeout_seconds=settings.kafka_producer_timeout_seconds,
        compression_type=settings.kafka_compression_type,
    )

    # 4. Initialize adapters
    rate_limiter = RedisRateLimiter(
        redis_client=redis_client,
        limit=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )
    key_resolver = CachedHttpProjectKeyResolver(
        redis_client=redis_client,
        http_client=http_client,
        control_plane_url=settings.control_plane_internal_url,
        service_token=settings.control_plane_service_token,
        cache_ttl=settings.key_cache_ttl_seconds,
        negative_cache_ttl=settings.key_negative_cache_ttl_seconds,
        timeout_seconds=settings.control_plane_timeout_seconds,
    )
    semaphore = asyncio.Semaphore(settings.max_in_flight_publishes)

    try:
        await kafka_producer.start()
    except Exception as exc:
        logger.warning("Kafka producer failed to start during app lifespan: %s", exc)

    # Set state on app for dependency injection
    app.state.redis_client = redis_client
    app.state.http_client = http_client
    app.state.kafka_producer = kafka_producer
    app.state.rate_limiter = rate_limiter
    app.state.key_resolver = key_resolver
    app.state.concurrency_semaphore = semaphore

    logger.info("Ingestion Service started successfully")

    yield

    logger.info("Shutting down Ingestion Service resources...")
    try:
        await kafka_producer.stop()
    except Exception as exc:
        logger.warning("Error stopping Kafka producer: %s", exc)

    try:
        await http_client.aclose()
    except Exception as exc:
        logger.warning("Error closing HTTP client: %s", exc)

    try:
        await redis_client.aclose()
    except Exception as exc:
        logger.warning("Error closing Redis client: %s", exc)

    logger.info("Ingestion Service shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Faultline Ingestion Service",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Middlewares (order: outermost executed first)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(MaxBodySizeMiddleware, max_body_bytes=settings.max_request_body_bytes)

    # Exception handler for domain errors
    @app.exception_handler(IngestionError)
    async def ingestion_error_handler(request: Request, exc: IngestionError) -> JSONResponse:
        headers = {}
        if exc.retry_after is not None:
            headers["Retry-After"] = str(exc.retry_after)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=headers,
        )

    # Standardize validation errors to {"detail": ...}
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()},
        )

    # Routers
    app.include_router(health_router)
    app.include_router(events_router, prefix="/api/v1")

    return app


app = create_app()
