import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.alerts.matcher import get_matcher
from app.alerts.models import Alert, AlertRule, AlertState, ProcessedEvent
from app.alerts.repository import AlertRuleRepository
from app.delivery.models import AlertRuleChannel, Delivery, NotificationChannel

logger = logging.getLogger(__name__)


class AlertEvaluationRepository:
    """Repository handling alert evaluation writes, state tracking, and outbox deliveries."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record_processed_event(
        self,
        event_id: UUID,
        project_id: UUID,
        event_type: str,
    ) -> bool:
        """Insert processed event using ON CONFLICT DO NOTHING.
        
        Returns True if inserted (first time seen), False if duplicate.
        """
        stmt = (
            insert(ProcessedEvent)
            .values(
                event_id=event_id,
                project_id=project_id,
                event_type=event_type,
                processed_at=datetime.now(timezone.utc),
            )
            .on_conflict_do_nothing(index_elements=["event_id"])
        )
        result = await self.session.execute(stmt)
        return (result.rowcount or 0) > 0

    async def get_or_create_alert_state(
        self,
        rule_id: UUID,
        project_id: UUID,
        deduplication_key: str,
        now: datetime,
    ) -> AlertState:
        """Fetch or create AlertState for (rule_id, deduplication_key)."""
        query = select(AlertState).where(
            AlertState.rule_id == rule_id,
            AlertState.deduplication_key == deduplication_key,
        )
        result = await self.session.execute(query)
        state = result.scalar_one_or_none()

        if state is None:
            state = AlertState(
                id=uuid.uuid4(),
                project_id=project_id,
                rule_id=rule_id,
                deduplication_key=deduplication_key,
                status="firing",
                first_triggered_at=now,
                last_triggered_at=now,
                last_evaluated_at=now,
            )
            self.session.add(state)
            await self.session.flush()
        else:
            state.last_triggered_at = now
            state.last_evaluated_at = now
            state.status = "firing"
            await self.session.flush()

        return state

    async def create_alert(
        self,
        rule_id: UUID,
        state_id: UUID,
        project_id: UUID,
        title: str,
        severity: str,
        now: datetime,
        details: dict[str, Any] | None = None,
    ) -> Alert:
        """Create and flush an Alert row."""
        alert = Alert(
            id=uuid.uuid4(),
            project_id=project_id,
            rule_id=rule_id,
            state_id=state_id,
            title=title,
            severity=severity,
            status="firing",
            occurrence_count=1,
            first_triggered_at=now,
            last_triggered_at=now,
            details=details,
        )
        self.session.add(alert)
        await self.session.flush()
        return alert

    async def create_delivery_jobs(
        self,
        alert: Alert,
        channels: list[NotificationChannel],
        payload: dict[str, Any],
    ) -> list[Delivery]:
        """Create outbox Delivery rows for each configured channel."""
        deliveries: list[Delivery] = []
        for channel in channels:
            if not channel.enabled:
                continue
            # Idempotency key per alert and channel
            idempotency_key = f"{alert.id}:{channel.id}"
            delivery = Delivery(
                id=uuid.uuid4(),
                project_id=alert.project_id,
                alert_id=alert.id,
                channel_id=channel.id,
                idempotency_key=idempotency_key,
                status="pending",
                attempt_count=0,
                payload=payload,
            )
            self.session.add(delivery)
            deliveries.append(delivery)
        await self.session.flush()
        return deliveries
