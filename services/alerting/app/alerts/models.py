import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.config import settings
from app.core.db import Base
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.delivery.models import AlertRuleChannel

SCHEMA = settings.database_schema


class AlertRule(Base):
    """Configuration rule for triggering alerts."""

    __tablename__ = "alert_rules"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    conditions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    recovery_conditions: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    severity: Mapped[str] = mapped_column(String(30), nullable=False, default="warning")
    environment: Mapped[str | None] = mapped_column(String(100), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    minimum_event_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    window_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cooldown_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True, onupdate=func.now()
    )

    channel_associations: Mapped[list["AlertRuleChannel"]] = relationship(
        "AlertRuleChannel", back_populates="rule", cascade="all, delete-orphan"
    )
    states: Mapped[list["AlertState"]] = relationship("AlertState", back_populates="rule")
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="rule")


class AlertState(Base):
    """Tracks state and deduplication for active alert rules."""

    __tablename__ = "alert_states"
    __table_args__ = (
        UniqueConstraint("rule_id", "deduplication_key", name="uq_alert_states_rule_dedup"),
        Index("ix_alert_states_project_status", "project_id", "status"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.alert_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    deduplication_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="normal")
    first_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    last_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True, onupdate=func.now()
    )

    rule: Mapped["AlertRule"] = relationship("AlertRule", back_populates="states")
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="state")


class Alert(Base):
    """Recorded triggered alert instance."""

    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_project_status_last_triggered", "project_id", "status", "last_triggered_at"),
        Index("ix_alerts_state_id", "state_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.alert_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    state_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.alert_states.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False, default="warning")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="firing")
    occurrence_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    first_triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    last_triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True, onupdate=func.now()
    )

    rule: Mapped["AlertRule"] = relationship("AlertRule", back_populates="alerts")
    state: Mapped["AlertState"] = relationship("AlertState", back_populates="alerts")
