from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Every value can be overridden with an environment variable
    prefixed with PROCESSING_, e.g. PROCESSING_DATABASE_URL.

    NOTE: when validation_alias is set, pydantic-settings ignores env_prefix
    for that field, so each alias list includes the explicit "processing_*" name.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PROCESSING_",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str = Field(
        default="postgresql+asyncpg://faultline:faultline@localhost:5432/processing",
        validation_alias=AliasChoices("processing_database_url", "database_url", "db_url"),
        description="Async PostgreSQL database URL",
    )
    database_schema: str = Field(
        default="processing",
        validation_alias=AliasChoices(
            "processing_database_schema", "database_schema", "schema_name", "schema"
        ),
        description="Database schema name",
    )

    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        validation_alias=AliasChoices(
            "processing_kafka_bootstrap_servers", "kafka_bootstrap_servers", "bootstrap_servers"
        ),
        description="Kafka bootstrap servers",
    )
    error_events_topic: str = Field(
        default="error-events",
        validation_alias=AliasChoices(
            "processing_error_events_topic", "error_events_topic", "topic", "kafka_topic_error_events"
        ),
        description="Kafka topic for error events",
    )
    errors_consumer_group: str = Field(
        default="processing-errors",
        validation_alias=AliasChoices(
            "processing_errors_consumer_group", "errors_consumer_group", "consumer_group_id", "consumer_group"
        ),
        description="Kafka consumer group ID for errors module",
    )
    performance_metrics_topic: str = Field(
        default="performance-metrics",
        validation_alias=AliasChoices(
            "processing_performance_metrics_topic",
            "performance_metrics_topic",
            "perf_metrics_topic",
            "kafka_topic_performance_metrics",
        ),
        description="Kafka topic for performance metrics",
    )
    perf_consumer_group: str = Field(
        default="processing-perf",
        validation_alias=AliasChoices(
            "processing_perf_consumer_group",
            "perf_consumer_group",
            "performance_consumer_group",
        ),
        description="Kafka consumer group ID for performance module",
    )

    max_retries: int = Field(
        default=3,
        validation_alias=AliasChoices("processing_max_retries", "max_retries"),
        description="Max retries for transient processing failures",
    )
    backoff_base: float = Field(
        default=0.5,
        validation_alias=AliasChoices("processing_backoff_base", "backoff_base", "backoff_base_seconds"),
        description="Initial backoff base in seconds",
    )
    backoff_cap: float = Field(
        default=10.0,
        validation_alias=AliasChoices("processing_backoff_cap", "backoff_cap", "backoff_cap_seconds"),
        description="Maximum backoff cap in seconds",
    )
    context_byte_cap: int = Field(
        default=16384,
        validation_alias=AliasChoices("processing_context_byte_cap", "context_byte_cap"),
        description="Maximum serialized context size in bytes before truncation (16 KB)",
    )
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("processing_log_level", "log_level"),
        description="Logging level",
    )


settings = Settings()