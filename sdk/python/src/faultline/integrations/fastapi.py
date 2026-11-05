from typing import Any

from faultline.client import Client
from faultline.integrations.asgi import FaultlineASGIMiddleware, Scope


class FaultlineFastAPIMiddleware(FaultlineASGIMiddleware):
    """FastAPI-specific ASGI middleware wrapper with route-template normalization.

    Ensures the matched route template (e.g., '/users/{user_id}') is resolved
    rather than the raw request URL path. If no route matches, route_template is None.
    """

    def __init__(self, app: Any, client: Client | None = None) -> None:
        super().__init__(app, client=client)

    def get_route_template(self, scope: Scope) -> str | None:
        """Resolve normalized route path from FastAPI/Starlette router.

        Returns the matched route template (e.g., '/items/{item_id}'),
        never the raw request path (e.g., '/items/42').
        """
        # 1. Starlette router attaches the matched Route to scope['route']
        route = scope.get("route")
        if route is not None and hasattr(route, "path"):
            return getattr(route, "path")

        # 2. If scope['route'] is not set (e.g., exception in early middleware),
        # query the app's router for matching routes
        router = getattr(self.app, "router", None) or getattr(self.app, "routes", None)
        routes = getattr(router, "routes", None) or (router if isinstance(router, list) else [])

        for r in routes:
            if hasattr(r, "matches"):
                try:
                    match, _ = r.matches(scope)
                    # Starlette Match enum: 1 is Match.FULL
                    if match == 1 or getattr(match, "name", None) == "FULL":
                        return getattr(r, "path", None)
                except Exception:
                    continue

        return None

