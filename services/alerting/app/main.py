import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from faultline_auth import configure_auth

from app.alerts.router import router as alerts_router
from app.delivery.router import router as delivery_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for Alerting service.

    Configures authentication at boot so misconfiguration fails fast.
    """
    logger.info("Configuring auth for Alerting service...")
    configure_auth()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application for Alerting & Notification HTTP API."""
    app = FastAPI(
        title="Faultline Alerting Service",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()},
        )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # Include alerts module routes
    app.include_router(alerts_router, prefix="/api/v1")

    # Include delivery module routes
    app.include_router(delivery_router, prefix="/api/v1")

    return app


app = create_app()
