from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for Alerting & Notification service.

    Every value can be overridden with an environment variable prefixed with
    ALERTING_, e.g. ALERTING_DATABASE_URL.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ALERTING_",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str = Field(
        default="postgresql+asyncpg://faultline:faultline@localhost:5432/alerting",
        validation_alias=AliasChoices("alerting_database_url", "database_url", "db_url"),
        description="Async PostgreSQL database URL",
    )
    database_schema: str = Field(
        default="alerting",
        validation_alias=AliasChoices(
            "alerting_database_schema", "database_schema", "schema_name", "schema"
        ),
        description="Database schema name",
    )

    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        validation_alias=AliasChoices(
            "alerting_kafka_bootstrap_servers", "kafka_bootstrap_servers", "bootstrap_servers"
        ),
        description="Kafka bootstrap servers",
    )
    issue_events_topic: str = Field(
        default="issue-events",
        validation_alias=AliasChoices(
            "alerting_issue_events_topic", "issue_events_topic", "topic_issue_events"
        ),
        description="Kafka topic for issue events",
    )
    regression_events_topic: str = Field(
        default="regression-events",
        validation_alias=AliasChoices(
            "alerting_regression_events_topic", "regression_events_topic", "topic_regression_events"
        ),
        description="Kafka topic for regression events",
    )
    alerts_consumer_group: str = Field(
        default="alerting-alerts",
        validation_alias=AliasChoices(
            "alerting_alerts_consumer_group", "alerts_consumer_group", "consumer_group_id"
        ),
        description="Kafka consumer group ID for alerts evaluation module",
    )

    role: str = Field(
        default="alerts",
        validation_alias=AliasChoices("alerting_role", "role"),
        description="Worker role when running worker_main ('alerts' or 'delivery')",
    )

    max_retries: int = Field(
        default=3,
        validation_alias=AliasChoices("alerting_max_retries", "max_retries"),
        description="Max retries for transient failures",
    )
    backoff_base: float = Field(
        default=0.5,
        validation_alias=AliasChoices("alerting_backoff_base", "backoff_base", "backoff_base_seconds"),
        description="Initial backoff base in seconds",
    )
    backoff_cap: float = Field(
        default=10.0,
        validation_alias=AliasChoices("alerting_backoff_cap", "backoff_cap", "backoff_cap_seconds"),
        description="Maximum backoff cap in seconds",
    )
    delivery_poll_interval_seconds: float = Field(
        default=1.0,
        validation_alias=AliasChoices("alerting_delivery_poll_interval_seconds", "delivery_poll_interval"),
        description="Poll interval for delivery outbox worker",
    )

    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("alerting_log_level", "log_level"),
        description="Logging level",
    )

    # SMTP Configuration (Mailpit by default in dev)
    smtp_host: str = Field(
        default="localhost",
        validation_alias=AliasChoices("alerting_smtp_host", "smtp_host"),
        description="SMTP server host",
    )
    smtp_port: int = Field(
        default=1025,
        validation_alias=AliasChoices("alerting_smtp_port", "smtp_port"),
        description="SMTP server port",
    )
    smtp_username: str = Field(
        default="",
        validation_alias=AliasChoices("alerting_smtp_username", "smtp_username"),
        description="SMTP username (empty for no auth)",
    )
    smtp_password: str = Field(
        default="",
        validation_alias=AliasChoices("alerting_smtp_password", "smtp_password"),
        description="SMTP password",
    )
    smtp_use_tls: bool = Field(
        default=False,
        validation_alias=AliasChoices("alerting_smtp_use_tls", "smtp_use_tls", "smtp_starttls"),
        description="Whether to use STARTTLS for SMTP",
    )
    email_from: str = Field(
        default="no-reply@faultline.local",
        validation_alias=AliasChoices("alerting_email_from", "email_from", "smtp_from"),
        description="From address for outgoing emails",
    )


settings = Settings()
