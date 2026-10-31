import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.errors.router import router as errors_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application for the Processing HTTP API."""
    app = FastAPI(
        title="Faultline Processing Service",
        version="0.1.0",
    )

    # Standardize validation error responses to {"detail": ...}
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()},
        )

    # Unauthenticated health check endpoint
    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # Include errors module routers
    app.include_router(errors_router, prefix="/api/v1")

    return app


app = create_app()
