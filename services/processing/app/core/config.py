from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Every value can be overridden with an environment variable
    prefixed with PROCESSING_, e.g. PROCESSING_DATABASE_URL.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PROCESSING_",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str = Field(
        default="postgresql+asyncpg://faultline:faultline@localhost:5432/processing",
        validation_alias=AliasChoices("database_url", "db_url"),
        description="Async PostgreSQL database URL",
    )
    database_schema: str = Field(
        default="processing",
        validation_alias=AliasChoices("database_schema", "schema_name", "schema"),
        description="Database schema name",
    )

    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        validation_alias=AliasChoices("kafka_bootstrap_servers", "bootstrap_servers"),
        description="Kafka bootstrap servers",
    )
    error_events_topic: str = Field(
        default="error-events",
        validation_alias=AliasChoices("error_events_topic", "topic", "kafka_topic_error_events"),
        description="Kafka topic for error events",
    )
    errors_consumer_group: str = Field(
        default="processing-errors",
        validation_alias=AliasChoices("errors_consumer_group", "consumer_group_id", "consumer_group"),
        description="Kafka consumer group ID for errors module",
    )

    max_retries: int = Field(
        default=3,
        validation_alias=AliasChoices("max_retries"),
        description="Max retries for transient processing failures",
    )
    backoff_base: float = Field(
        default=0.5,
        validation_alias=AliasChoices("backoff_base", "backoff_base_seconds"),
        description="Initial backoff base in seconds",
    )
    backoff_cap: float = Field(
        default=10.0,
        validation_alias=AliasChoices("backoff_cap", "backoff_cap_seconds"),
        description="Maximum backoff cap in seconds",
    )
    context_byte_cap: int = Field(
        default=16384,
        validation_alias=AliasChoices("context_byte_cap"),
        description="Maximum serialized context size in bytes before truncation (16 KB)",
    )
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("log_level"),
        description="Logging level",
    )


settings = Settings()
