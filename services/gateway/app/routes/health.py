import asyncio
import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import httpx

from app.core.config import Settings
from app.routes.registry import RouteRegistry

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Gateway liveness probe. Fast local response without calling any upstream services."""
    return {"status": "ok"}


@router.get("/health/upstreams")
async def health_upstreams(request: Request) -> JSONResponse:
    """Optional deep health check probing configured upstreams.
    
    Never reveals upstream URLs or error exceptions.
    """
    settings: Settings = request.app.state.settings
    client: httpx.AsyncClient = request.app.state.http_client

    checks = {
        "control-plane": f"{settings.upstream_control_plane_url}/healthz",
        "ingestion": f"{settings.upstream_ingestion_url}/healthz",
        "processing": f"{settings.upstream_processing_url}/health",
    }

    results: dict[str, str] = {}
    is_all_healthy = True

    async def probe(service_name: str, url: str) -> None:
        nonlocal is_all_healthy
        try:
            resp = await client.get(url, timeout=1.5)
            if resp.status_code == 200:
                results[service_name] = "ok"
                return
        except Exception as exc:
            logger.warning("Upstream probe failed for [%s]: %s", service_name, exc)
        results[service_name] = "unavailable"
        is_all_healthy = False

    await asyncio.gather(*(probe(name, url) for name, url in checks.items()))

    overall_status = "ok" if is_all_healthy else "degraded"
    return JSONResponse(
        status_code=200 if is_all_healthy else 503,
        content={"status": overall_status, "upstreams": results},
    )

