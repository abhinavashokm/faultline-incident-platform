from pydantic_settings import BaseSettings, SettingsConfigDict


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


settings = Settings()

