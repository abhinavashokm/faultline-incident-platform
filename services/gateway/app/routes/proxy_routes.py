from fastapi import APIRouter, Request
from starlette.responses import Response

from app.errors import not_found_response
from app.proxy.forward import forward_request
from app.routes.registry import RouteRegistry

router = APIRouter()

STANDARD_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]


@router.api_route("/{path:path}", methods=STANDARD_METHODS)
async def catch_all_proxy(path: str, request: Request) -> Response:
    """Catch-all proxy route that resolves upstream via the registry."""
    registry: RouteRegistry = request.app.state.registry
    target_path = request.url.path

    route = registry.match(target_path)
    if route is None:
        return not_found_response()

    request.state.upstream_name = route.service_name
    client = request.app.state.http_client
    settings = request.app.state.settings

    return await forward_request(request, route, client, settings)

