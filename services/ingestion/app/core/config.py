from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Kafka configuration
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Comma-separated Kafka bootstrap servers",
    )
    kafka_topic_error_events: str = Field(
        default="error-events",
        description="Kafka topic for error events",
    )
    kafka_producer_timeout_seconds: float = Field(
        default=3.0,
        description="Timeout in seconds for Kafka acknowledgment",
    )
    kafka_compression_type: str = Field(
        default="gzip",
        description="Compression algorithm for Kafka producer (gzip, none)",
    )

    # Redis configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    redis_timeout_seconds: float = Field(
        default=1.0,
        description="Redis socket and operation timeout in seconds",
    )

    # Rate limiting
    rate_limit_requests: int = Field(
        default=120,
        description="Max requests per project within the rate limit window",
    )
    rate_limit_window_seconds: int = Field(
        default=60,
        description="Rate limit window in seconds",
    )

    # Control Plane Key Resolution
    control_plane_internal_url: str = Field(
        default="http://localhost:8000",
        description="Base URL for Control Plane internal service endpoints",
    )
    control_plane_service_token: str = Field(
        ...,
        validation_alias=AliasChoices(
            "control_plane_service_token",
            "control_plane_internal_service_secret",
            "internal_service_secret",
            "service_token",
        ),
        description="Service-to-service secret token for internal API authentication",
    )
    control_plane_timeout_seconds: float = Field(
        default=2.0,
        description="HTTP timeout when calling Control Plane internal endpoint",
    )

    # Caching
    key_cache_ttl_seconds: int = Field(
        default=300,
        description="TTL for cached valid project keys in seconds",
    )
    key_negative_cache_ttl_seconds: int = Field(
        default=60,
        description="TTL for negative caching (unknown/revoked keys) in seconds",
    )

    # Limits and backpressure
    max_request_body_bytes: int = Field(
        default=200 * 1024,
        description="Maximum request body size in bytes (200 KB default)",
    )
    max_stack_frames: int = Field(
        default=100,
        description="Maximum number of stack frames accepted",
    )
    max_context_bytes: int = Field(
        default=64 * 1024,
        description="Maximum serialized size in bytes for context payload (64 KB default)",
    )
    max_in_flight_publishes: int = Field(
        default=100,
        description="Concurrency limit for in-flight Kafka publishes",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Application logging level",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()

