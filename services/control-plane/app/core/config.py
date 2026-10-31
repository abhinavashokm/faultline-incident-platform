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

    smtp_host: str = Field(
        default="localhost",
        validation_alias=AliasChoices("control_plane_smtp_host", "smtp_host"),
        description="SMTP server host",
    )
    smtp_port: int = Field(
        default=1025,
        validation_alias=AliasChoices("control_plane_smtp_port", "smtp_port"),
        description="SMTP server port",
    )
    smtp_from: str = Field(
        default="noreply@faultline.dev",
        validation_alias=AliasChoices("control_plane_smtp_from", "smtp_from"),
        description="From address for outgoing emails",
    )
    otp_hmac_secret: str = Field(
        default="dev-otp-hmac-secret-change-in-prod",
        validation_alias=AliasChoices(
            "control_plane_otp_hmac_secret", "otp_hmac_secret"
        ),
        description="Secret key for HMAC-SHA256 hashing of verification codes",
    )
    otp_ttl_seconds: int = Field(
        default=600,
        validation_alias=AliasChoices(
            "control_plane_otp_ttl_seconds", "otp_ttl_seconds"
        ),
        description="Time-to-live for email verification codes in seconds",
    )
    otp_max_attempts: int = Field(
        default=5,
        validation_alias=AliasChoices(
            "control_plane_otp_max_attempts", "otp_max_attempts"
        ),
        description="Maximum failed verification attempts allowed before code invalidation",
    )
    otp_resend_cooldown_seconds: int = Field(
        default=60,
        validation_alias=AliasChoices(
            "control_plane_otp_resend_cooldown_seconds",
            "otp_resend_cooldown_seconds",
        ),
        description="Cooldown period in seconds before requesting a new code",
    )
    otp_resend_hourly_cap: int = Field(
        default=5,
        validation_alias=AliasChoices(
            "control_plane_otp_resend_hourly_cap", "otp_resend_hourly_cap"
        ),
        description="Maximum number of verification codes that can be requested per hour",
    )

    internal_service_secret: str = Field(
        ...,
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
