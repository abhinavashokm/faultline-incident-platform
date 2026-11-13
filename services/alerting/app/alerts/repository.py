import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.alerts.models import AlertRule
from app.delivery.models import AlertRuleChannel, NotificationChannel


class AlertRuleRepository:
    """Repository for alert rules data access.
    Queries and flushes only; never commits transactions.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_project(self, project_id: uuid.UUID) -> Sequence[AlertRule]:
        """Fetch all alert rules for a project ordered by creation date descending,
        eagerly loading channel associations and notification channels.
        """
        query = (
            select(AlertRule)
            .where(AlertRule.project_id == project_id)
            .options(
                selectinload(AlertRule.channel_associations).selectinload(
                    AlertRuleChannel.channel
                )
            )
            .order_by(AlertRule.created_at.desc(), AlertRule.id.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_id(
        self,
        project_id: uuid.UUID,
        rule_id: uuid.UUID,
    ) -> AlertRule | None:
        """Fetch a specific alert rule by project and rule id."""
        query = (
            select(AlertRule)
            .where(AlertRule.project_id == project_id, AlertRule.id == rule_id)
            .options(
                selectinload(AlertRule.channel_associations).selectinload(
                    AlertRuleChannel.channel
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, rule: AlertRule) -> AlertRule:
        """Add and flush an AlertRule."""
        self.session.add(rule)
        await self.session.flush()
        return rule

    async def delete(self, rule: AlertRule) -> None:
        """Delete an AlertRule."""
        await self.session.delete(rule)
        await self.session.flush()

    async def set_channels(
        self,
        rule_id: uuid.UUID,
        channel_ids: list[uuid.UUID],
    ) -> None:
        """Replace channel associations for an alert rule."""
        # Delete existing associations
        await self.session.execute(
            delete(AlertRuleChannel).where(AlertRuleChannel.rule_id == rule_id)
        )
        await self.session.flush()

        # Add new associations
        for ch_id in channel_ids:
            assoc = AlertRuleChannel(
                id=uuid.uuid4(),
                rule_id=rule_id,
                channel_id=ch_id,
            )
            self.session.add(assoc)
        await self.session.flush()

    async def list_enabled_by_project(self, project_id: uuid.UUID) -> Sequence[AlertRule]:
        """Fetch all enabled alert rules for a project with channels preloaded."""
        query = (
            select(AlertRule)
            .where(AlertRule.project_id == project_id, AlertRule.enabled.is_(True))
            .options(
                selectinload(AlertRule.channel_associations).selectinload(
                    AlertRuleChannel.channel
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalars().all()

