from dataclasses import dataclass, field
import os
from typing import Any

from faultline.dsn import Dsn, parse_dsn
from faultline.event import normalize_environment


@dataclass
class Config:
    """SDK configuration settings."""
    dsn: Dsn
    release: str | None = None
    environment: str = "production"
    service: str | None = None
    max_queue_size: int = 1000
    max_retries: int = 3
    timeout: float = 5.0
    flush_timeout: float = 2.0
    max_payload_bytes: int = 65536
    max_retry_after: float = 10.0
    performance_flush_interval: float = 10.0

    @classmethod
    def from_options(
        cls,
        dsn: str,
        release: str | None = None,
        environment: str = "production",
        service: str | None = None,
        **kwargs: Any,
    ) -> "Config":
        parsed_dsn = parse_dsn(dsn)

        # If release is not passed, read from APP_RELEASE environment variable
        resolved_release = release or os.environ.get("APP_RELEASE")
        resolved_env = normalize_environment(environment) or "production"

        return cls(
            dsn=parsed_dsn,
            release=resolved_release,
            environment=resolved_env,
            service=service,
            max_queue_size=kwargs.get("max_queue_size", 1000),
            max_retries=kwargs.get("max_retries", 3),
            timeout=kwargs.get("timeout", 5.0),
            flush_timeout=kwargs.get("flush_timeout", 2.0),
            max_payload_bytes=kwargs.get("max_payload_bytes", 65536),
            max_retry_after=kwargs.get("max_retry_after", 10.0),
            performance_flush_interval=kwargs.get("performance_flush_interval", 10.0),
        )

