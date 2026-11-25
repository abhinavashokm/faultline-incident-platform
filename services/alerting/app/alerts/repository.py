import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, select, tuple_
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

    async def list_by_project(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        limit: int,
        cursor: tuple[datetime, uuid.UUID] | None,
    ) -> Sequence[AlertRule]:
        """Fetch all alert rules for a project ordered by creation date descending,
        eagerly loading channel associations and notification channels.
        """
        query = (
            select(AlertRule)
            .where(
                AlertRule.workspace_id == workspace_id,
                AlertRule.project_id == project_id,
            )
            .options(
                selectinload(AlertRule.channel_associations).selectinload(
                    AlertRuleChannel.channel.and_(
                        NotificationChannel.workspace_id == workspace_id,
                        NotificationChannel.project_id == project_id,
                    )
                )
            )
            .order_by(AlertRule.created_at.desc(), AlertRule.id.desc())
            .limit(limit + 1)
        )
        if cursor is not None:
            query = query.where(tuple_(AlertRule.created_at, AlertRule.id) < cursor)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_id(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        rule_id: uuid.UUID,
    ) -> AlertRule | None:
        """Fetch a specific alert rule by project and rule id."""
        query = (
            select(AlertRule)
            .where(
                AlertRule.workspace_id == workspace_id,
                AlertRule.project_id == project_id,
                AlertRule.id == rule_id,
            )
            .execution_options(populate_existing=True)
            .options(
                selectinload(AlertRule.channel_associations).selectinload(
                    AlertRuleChannel.channel.and_(
                        NotificationChannel.workspace_id == workspace_id,
                        NotificationChannel.project_id == project_id,
                    )
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
        rule: AlertRule,
        channel_ids: list[uuid.UUID],
    ) -> bool:
        """Replace channel associations for an alert rule."""
        requested_ids = set(channel_ids)
        if requested_ids:
            found_ids = await self.session.scalars(
                select(NotificationChannel.id).where(
                    NotificationChannel.workspace_id == rule.workspace_id,
                    NotificationChannel.project_id == rule.project_id,
                    NotificationChannel.id.in_(requested_ids),
                )
            )
            if set(found_ids) != requested_ids:
                return False

        # Delete existing associations
        await self.session.execute(
            delete(AlertRuleChannel).where(AlertRuleChannel.rule_id == rule.id)
        )
        await self.session.flush()

        # Add new associations
        for ch_id in dict.fromkeys(channel_ids):
            assoc = AlertRuleChannel(
                id=uuid.uuid4(),
                rule_id=rule.id,
                channel_id=ch_id,
            )
            self.session.add(assoc)
        await self.session.flush()
        return True

    async def list_enabled_by_project(
        self, workspace_id: uuid.UUID, project_id: uuid.UUID
    ) -> Sequence[AlertRule]:
        """Fetch all enabled alert rules for a project with channels preloaded."""
        query = (
            select(AlertRule)
            .where(
                AlertRule.workspace_id == workspace_id,
                AlertRule.project_id == project_id,
                AlertRule.enabled.is_(True),
            )
            .options(
                selectinload(AlertRule.channel_associations).selectinload(
                    AlertRuleChannel.channel.and_(
                        NotificationChannel.workspace_id == workspace_id,
                        NotificationChannel.project_id == project_id,
                    )
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalars().all()

