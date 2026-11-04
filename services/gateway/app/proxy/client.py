import httpx

from app.core.config import Settings


def create_http_client(settings: Settings) -> httpx.AsyncClient:
    """Create a shared httpx.AsyncClient with configured connection pool limits and timeouts."""
    limits = httpx.Limits(
        max_connections=settings.pool_max_connections,
        max_keepalive_connections=settings.pool_max_keepalive_connections,
    )
    timeout = httpx.Timeout(
        connect=settings.connect_timeout_seconds,
        read=settings.read_timeout_seconds,
        write=settings.read_timeout_seconds,
        pool=settings.connect_timeout_seconds,
    )
    return httpx.AsyncClient(
        limits=limits,
        timeout=timeout,
        follow_redirects=False,
    )

