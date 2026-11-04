import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis

from app.core.config import Settings, settings as default_settings
from app.core.logging import setup_logging
from app.middleware.access_log import AccessLogMiddleware
from app.middleware.rate_limit import (
    MemoryRateLimiter,
    RateLimitMiddleware,
    RedisRateLimiter,
)
from app.middleware.request_id import RequestIDMiddleware
from app.proxy.client import create_http_client
from app.routes.health import router as health_router
from app.routes.proxy_routes import router as proxy_router
from app.routes.registry import create_registry_from_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for API Gateway.
    
    Initializes shared HTTP client, route registry, and rate limiter.
    Cleans up all network pools on shutdown.
    """
    settings: Settings = getattr(app.state, "settings", default_settings)
    setup_logging(level=settings.log_level)
    logger.info("Initializing API Gateway resources...")

    # 1. Initialize shared httpx.AsyncClient
    http_client = create_http_client(settings)

    # 2. Initialize route registry
    registry = create_registry_from_settings(settings)

    # 3. Initialize rate limiter backend
    redis_client = None
    rate_limiter = None

    if settings.rate_limit_strategy == "redis" or (
        settings.rate_limit_strategy == "auto" and settings.redis_url
    ):
        try:
            redis_client = redis.from_url(
                settings.redis_url,
                socket_timeout=settings.redis_timeout_seconds,
                decode_responses=True,
            )
            # Verify connectivity
            await redis_client.ping()
            rate_limiter = RedisRateLimiter(
                redis_client=redis_client,
                limit=settings.rate_limit_requests,
                window_seconds=settings.rate_limit_window_seconds,
            )
            logger.info("Connected to Redis for distributed rate limiting")
        except Exception as exc:
            logger.warning(
                "Could not connect to Redis (%s); falling back to in-memory rate limiting",
                exc,
            )
            if redis_client is not None:
                try:
                    await redis_client.aclose()
                except Exception:
                    pass
                redis_client = None
            rate_limiter = MemoryRateLimiter(
                limit=settings.rate_limit_requests,
                window_seconds=settings.rate_limit_window_seconds,
            )
    else:
        logger.info("Using in-memory rate limiting")
        rate_limiter = MemoryRateLimiter(
            limit=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )

    # Attach resources to app.state
    app.state.settings = settings
    app.state.http_client = http_client
    app.state.registry = registry
    app.state.rate_limiter = rate_limiter
    app.state.redis_client = redis_client

    logger.info("API Gateway initialization complete")

    yield

    logger.info("Shutting down API Gateway resources...")
    try:
        await http_client.aclose()
    except Exception as exc:
        logger.warning("Error closing HTTP client: %s", exc)

    if redis_client is not None:
        try:
            await redis_client.aclose()
        except Exception as exc:
            logger.warning("Error closing Redis client: %s", exc)

    logger.info("API Gateway shutdown complete")


def create_app(custom_settings: Settings | None = None) -> FastAPI:
    """Application factory for API Gateway."""
    active_settings = custom_settings or default_settings

    app = FastAPI(
        title="Faultline API Gateway",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = active_settings
    app.state.registry = create_registry_from_settings(active_settings)

    # Middlewares (Starlette applies middlewares in reverse order of addition:
    # RateLimit -> CORS -> AccessLog -> RequestID -> handler)
    app.add_middleware(
        RateLimitMiddleware,
        settings=active_settings,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "X-Faultline-Key",
            "X-Project-Key",
        ],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # Routes
    app.include_router(health_router)
    app.include_router(proxy_router)

    return app


app = create_app()
