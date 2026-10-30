import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from cryptography.hazmat.primitives import serialization
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from jwt.algorithms import RSAAlgorithm
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import router as auth_router
from app.internal.router import router as internal_router
from app.projects.router import router as projects_router
from app.core.config import settings
from app.core.db import engine, get_session

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(title="Faultline Control Plane", version="0.1.0", lifespan=lifespan)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(projects_router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(internal_router, prefix="/api/v1/internal", tags=["internal"])


@app.get("/.well-known/jwks.json")
async def jwks() -> JSONResponse:
    """Public JWKS endpoint for token verification."""
    public_pem = settings.get_jwt_public_key()
    pub_key = serialization.load_pem_public_key(public_pem.encode("utf-8"))
    raw_jwk = json.loads(RSAAlgorithm.to_jwk(pub_key))

    key_dict = {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": settings.jwt_key_id,
        "n": raw_jwk["n"],
        "e": raw_jwk["e"],
    }

    return JSONResponse(
        content={"keys": [key_dict]},
        headers={
            "Cache-Control": f"public, max-age={settings.jwks_cache_max_age_seconds}"
        },
    )


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz(
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        logger.error("Readiness check failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )
