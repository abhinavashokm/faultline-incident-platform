from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for API Gateway edge service.
    
    Every value can be overridden with an environment variable prefixed with GATEWAY_,
    e.g. GATEWAY_UPSTREAM_CONTROL_PLANE_URL.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="GATEWAY_",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Upstream base URLs ────────────────────────────────────────────────────
    upstream_control_plane_url: str = Field(
        default="http://control-plane:8000",
        description="Base URL for Control Plane service",
    )
    upstream_ingestion_url: str = Field(
        default="http://ingestion:8001",
        description="Base URL for Ingestion service",
    )
    upstream_processing_url: str = Field(
        default="http://processing-api:8002",
        description="Base URL for Processing service",
    )
    # Future / unreleased services (disabled by default)
    upstream_alerting_url: str = Field(
        default="http://alerting:8003",
        description="Base URL for Alerting service",
    )
    upstream_incident_url: str = Field(
        default="http://incident:8004",
        description="Base URL for Incident service",
    )
    upstream_investigation_url: str = Field(
        default="http://investigation:8005",
        description="Base URL for Investigation service",
    )
    enable_incident: bool = Field(
        default=False,
        description="Enable routing to Incident service",
    )
    enable_investigation: bool = Field(
        default=False,
        description="Enable routing to Investigation service",
    )

    # ── CORS Settings ─────────────────────────────────────────────────────────
    cors_origins: list[str] | str = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins (comma-separated or list)",
    )

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    rate_limit_requests: int = Field(
        default=120,
        description="Max requests allowed per rate limit window",
    )
    rate_limit_window_seconds: int = Field(
        default=60,
        description="Rate limit window in seconds",
    )
    rate_limit_strategy: Literal["auto", "redis", "memory"] = Field(
        default="auto",
        description="Rate limit backend strategy ('auto', 'redis', or 'memory')",
    )
    redis_url: str | None = Field(
        default="redis://redis:6379/0",
        description="Redis connection URL for distributed rate limiting",
    )
    redis_timeout_seconds: float = Field(
        default=2.0,
        description="Redis socket/command timeout in seconds",
    )

    # ── Timeouts & Limits ─────────────────────────────────────────────────────
    connect_timeout_seconds: float = Field(
        default=3.0,
        description="Timeout for establishing upstream TCP connections",
    )
    read_timeout_seconds: float = Field(
        default=30.0,
        description="Default upstream read timeout in seconds",
    )
    ingestion_read_timeout_seconds: float = Field(
        default=30.0,
        description="Specific read timeout for Ingestion upstream in seconds",
    )
    max_request_body_bytes: int = Field(
        default=5 * 1024 * 1024,  # 5 MB
        description="Maximum request body size in bytes before returning 413",
    )
    trust_forwarded_for: bool = Field(
        default=False,
        description="Whether to trust incoming X-Forwarded-For headers for client IP",
    )

    # ── Connection Pool ───────────────────────────────────────────────────────
    pool_max_connections: int = Field(
        default=100,
        description="Max connections in shared HTTP client pool",
    )
    pool_max_keepalive_connections: int = Field(
        default=20,
        description="Max keepalive connections in shared HTTP client pool",
    )

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [orig.strip() for orig in value.split(",") if orig.strip()]
        return value

    @field_validator(
        "connect_timeout_seconds",
        "read_timeout_seconds",
        "ingestion_read_timeout_seconds",
        "redis_timeout_seconds",
    )
    @classmethod
    def validate_positive_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Timeout must be strictly positive")
        return value

    @field_validator("rate_limit_requests", "rate_limit_window_seconds", "max_request_body_bytes")
    @classmethod
    def validate_positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Must be strictly positive")
        return value

    @field_validator("upstream_control_plane_url", "upstream_ingestion_url", "upstream_processing_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith(("http://", "https://")):
            raise ValueError(f"Upstream URL must start with http:// or https://: {value}")
        return value.rstrip("/")


settings = Settings()
