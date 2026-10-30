from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


@lru_cache
def _read_key_file(path_str: str) -> str:
    """Read a key file from disk and cache the contents."""
    path = Path(path_str)
    return path.read_text(encoding="utf-8")


class Settings(BaseSettings):
    """Every value can be overridden with an environment variable
    prefixed with CONTROL_PLANE_, e.g. CONTROL_PLANE_DATABASE_URL.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CONTROL_PLANE_",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+asyncpg://faultline:faultline@localhost:5432/control_plane"
    )
    log_level: str = "INFO"

    jwt_private_key_path: str = "keys/private.pem"
    jwt_public_key_path: str = "keys/public.pem"
    jwt_key_id: str = "dev-1"
    jwt_issuer: str = "faultline-control-plane"
    jwt_audience: str = "faultline"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7
    jwks_cache_max_age_seconds: int = 300

    dsn_host: str = "errors.example.com"
    dsn_scheme: str = "https"
    retention_days_max: int = 90

    internal_service_secret: str = Field(
        default="",
        validation_alias=AliasChoices(
            "control_plane_internal_service_secret",
            "control_plane_service_token",
            "internal_service_secret",
            "service_token",
        ),
        description="Shared secret for internal service-to-service communication",
    )

    def get_jwt_private_key(self) -> str:
        return _read_key_file(self.jwt_private_key_path)

    def get_jwt_public_key(self) -> str:
        return _read_key_file(self.jwt_public_key_path)


settings = Settings()
