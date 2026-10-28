from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Every value can be overridden with an environment variable
    prefixed with PROCESSING_, e.g. PROCESSING_DATABASE_URL."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PROCESSING_",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://faultline:faultline@localhost:5432/processing"

    kafka_bootstrap_servers: str = "localhost:9092"
    error_events_topic: str = "error-events"
    error_events_dlq_topic: str = "error-events-dlq"
    errors_consumer_group: str = "processing-errors"

    log_level: str = "INFO"


settings = Settings()