import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.alerts.models import Alert, AlertRule
from app.core.config import settings
from app.core.db import Base

SCHEMA = settings.database_schema


class NotificationChannel(Base):
    """External destination where alerts are delivered."""

    __tablename__ = "notification_channels"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    channel_type: Mapped[str] = mapped_column(String(30), nullable=False)
    destination: Mapped[str] = mapped_column(Text, nullable=False)
    credentials_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    secret_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=func.now()
    )

    rule_associations: Mapped[list["AlertRuleChannel"]] = relationship(
        "AlertRuleChannel", back_populates="channel"
    )
    deliveries: Mapped[list["Delivery"]] = relationship(
        "Delivery", back_populates="channel"
    )


class AlertRuleChannel(Base):
    """Many-to-many relationship linking AlertRules to NotificationChannels."""

    __tablename__ = "alert_rule_channels"
    __table_args__ = (
        UniqueConstraint("rule_id", "channel_id", name="uq_alert_rule_channels"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.alert_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.notification_channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    rule: Mapped["AlertRule"] = relationship("AlertRule")
    channel: Mapped["NotificationChannel"] = relationship(
        "NotificationChannel", back_populates="rule_associations"
    )


class Delivery(Base):
    """Outbox table for notification jobs."""

    __tablename__ = "deliveries"
    __table_args__ = (
        Index("ix_deliveries_status_next_attempt", "status", "next_attempt_at"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.alerts.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.notification_channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True, onupdate=func.now()
    )

    alert: Mapped["Alert"] = relationship("Alert")
    channel: Mapped["NotificationChannel"] = relationship("NotificationChannel", back_populates="deliveries")
    attempts: Mapped[list["DeliveryAttempt"]] = relationship(
        "DeliveryAttempt", back_populates="delivery", cascade="all, delete-orphan"
    )


class DeliveryAttempt(Base):
    """Log of individual delivery attempts for a delivery job."""

    __tablename__ = "delivery_attempts"
    __table_args__ = (
        UniqueConstraint("delivery_id", "attempt_number", name="uq_delivery_attempt_number"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    delivery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.deliveries.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    http_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    delivery: Mapped["Delivery"] = relationship("Delivery", back_populates="attempts")
