import re
from dataclasses import dataclass, field

from app.core.config import Settings


@dataclass
class RouteEntry:
    """Represents a path prefix mapped to an upstream service."""

    path_prefix: str
    upstream_base_url: str
    service_name: str
    read_timeout: float | None = None

    _regex: re.Pattern = field(init=False, repr=False)
    specificity: tuple[int, int] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.upstream_base_url = self.upstream_base_url.rstrip("/")
        # Compile pattern
        prefix = "/" + self.path_prefix.strip("/") if self.path_prefix.strip("/") else "/"
        segments = [s for s in prefix.split("/") if s]

        regex_parts: list[str] = []
        static_char_count = 0

        for segment in segments:
            if (segment.startswith("{") and segment.endswith("}")) or segment == "*":
                regex_parts.append(r"[^/]+")
            else:
                regex_parts.append(re.escape(segment))
                static_char_count += len(segment)

        if not regex_parts:
            pattern_str = r"^/(?:.*)?$"
        else:
            pattern_str = r"^/" + r"/".join(regex_parts) + r"(?:/.*)?$"

        self._regex = re.compile(pattern_str)
        # Specificity: (segment_count, static_char_count)
        self.specificity = (len(segments), static_char_count)

    def matches(self, path: str) -> bool:
        clean_path = "/" + path.strip("/") if path.strip("/") else "/"
        return bool(self._regex.match(clean_path))


class RouteRegistry:
    """Registry of upstream routes with longest-prefix matching."""

    def __init__(self, routes: list[RouteEntry] | None = None) -> None:
        # Sort routes by specificity (segment count, then static characters, then total prefix length) descending
        self.routes = sorted(
            routes or [],
            key=lambda r: (r.specificity[0], r.specificity[1], len(r.path_prefix)),
            reverse=True,
        )

    def match(self, path: str) -> RouteEntry | None:
        """Find the most specific route matching the given path."""
        clean_path = "/" + path.strip("/") if path.strip("/") else "/"
        for route in self.routes:
            if route.matches(clean_path):
                return route
        return None


def create_registry_from_settings(settings: Settings) -> RouteRegistry:
    """Build the RouteRegistry from active Settings.
    
    Expected mapping based on existing routers:
    - Control Plane:
      - /api/v1/auth
      - /api/v1/workspaces
      - /.well-known/jwks.json
      - /api/v1/projects (project CRUD, settings, and api-key)
    - Processing:
      - /api/v1/projects/{project_id}/issues (and sub-paths: events, issue detail)
    - Ingestion:
      - /api/v1/events (SDK event intake)
    
    Unimplemented future services (commented out / disabled by config):
    - Alerting: /api/v1/projects/{project_id}/alerts
    - Incident: /api/v1/projects/{project_id}/incidents
    - Investigation: /api/v1/projects/{project_id}/investigations
    """
    routes: list[RouteEntry] = [
        # Public JWKS endpoint
        RouteEntry(
            path_prefix="/.well-known/jwks.json",
            upstream_base_url=settings.upstream_control_plane_url,
            service_name="control-plane",
        ),
        # Control Plane user authentication endpoints
        RouteEntry(
            path_prefix="/api/v1/auth",
            upstream_base_url=settings.upstream_control_plane_url,
            service_name="control-plane",
        ),
        # Control Plane workspaces endpoints
        RouteEntry(
            path_prefix="/api/v1/workspaces",
            upstream_base_url=settings.upstream_control_plane_url,
            service_name="control-plane",
        ),
        # Processing service issue endpoints (more specific than /api/v1/projects)
        RouteEntry(
            path_prefix="/api/v1/projects/{project_id}/issues",
            upstream_base_url=settings.upstream_processing_url,
            service_name="processing",
            read_timeout=settings.read_timeout_seconds,
        ),
        # Control Plane project management endpoints
        RouteEntry(
            path_prefix="/api/v1/projects",
            upstream_base_url=settings.upstream_control_plane_url,
            service_name="control-plane",
        ),
        # Ingestion service SDK error events intake
        RouteEntry(
            path_prefix="/api/v1/events",
            upstream_base_url=settings.upstream_ingestion_url,
            service_name="ingestion",
            read_timeout=settings.ingestion_read_timeout_seconds,
        ),
    ]

    # Future / unreleased services (disabled by config)
    if settings.enable_alerting:
        routes.append(
            RouteEntry(
                path_prefix="/api/v1/projects/{project_id}/alerts",
                upstream_base_url=settings.upstream_alerting_url,
                service_name="alerting",
            )
        )

    if settings.enable_incident:
        routes.append(
            RouteEntry(
                path_prefix="/api/v1/projects/{project_id}/incidents",
                upstream_base_url=settings.upstream_incident_url,
                service_name="incident",
            )
        )

    if settings.enable_investigation:
        routes.append(
            RouteEntry(
                path_prefix="/api/v1/projects/{project_id}/investigations",
                upstream_base_url=settings.upstream_investigation_url,
                service_name="investigation",
            )
        )

    return RouteRegistry(routes)

