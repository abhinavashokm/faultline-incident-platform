import logging
import uuid
from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.models import AlertRule
from app.alerts.repository import AlertRuleRepository
from app.alerts.schemas import (
    AlertRuleChannelResponse,
    AlertRuleCreate,
    AlertRuleResponse,
    AlertRuleUpdate,
)
from app.core.uuid7 import uuid7

logger = logging.getLogger(__name__)


def map_rule_to_response(rule: AlertRule) -> AlertRuleResponse:
    channels = []
    if hasattr(rule, "channel_associations") and rule.channel_associations:
        for assoc in rule.channel_associations:
            if assoc.channel:
                channels.append(
                    AlertRuleChannelResponse(
                        id=assoc.channel.id,
                        name=assoc.channel.name,
                        channel_type=assoc.channel.channel_type,
                    )
                )

    return AlertRuleResponse(
        id=rule.id,
        project_id=rule.project_id,
        name=rule.name,
        rule_type=rule.rule_type,
        conditions=rule.conditions or {},
        recovery_conditions=rule.recovery_conditions,
        severity=rule.severity,
        environment=rule.environment,
        enabled=rule.enabled,
        minimum_event_count=rule.minimum_event_count,
        window_seconds=rule.window_seconds,
        cooldown_seconds=rule.cooldown_seconds,
        created_by=rule.created_by,
        channels=channels,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


class AlertRuleService:
    """Service owning business rules and transaction boundaries for alert rules."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = AlertRuleRepository(session)

    async def list_rules(self, project_id: uuid.UUID) -> list[AlertRuleResponse]:
        rules = await self.repository.list_by_project(project_id)
        return [map_rule_to_response(r) for r in rules]

    async def get_rule(
        self,
        project_id: uuid.UUID,
        rule_id: uuid.UUID,
    ) -> AlertRuleResponse:
        rule = await self.repository.get_by_id(project_id, rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert rule {rule_id} not found in project {project_id}",
            )
        return map_rule_to_response(rule)

    async def create_rule(
        self,
        project_id: uuid.UUID,
        rule_in: AlertRuleCreate,
        created_by: uuid.UUID | None = None,
    ) -> AlertRuleResponse:
        rule_id = uuid7()
        rule = AlertRule(
            id=rule_id,
            project_id=project_id,
            name=rule_in.name,
            rule_type=rule_in.rule_type,
            conditions=rule_in.conditions,
            recovery_conditions=rule_in.recovery_conditions,
            severity=rule_in.severity,
            environment=rule_in.environment,
            enabled=rule_in.enabled,
            minimum_event_count=rule_in.minimum_event_count,
            window_seconds=rule_in.window_seconds,
            cooldown_seconds=rule_in.cooldown_seconds,
            created_by=created_by,
        )

        await self.repository.create(rule)
        if rule_in.channel_ids:
            await self.repository.set_channels(rule_id, rule_in.channel_ids)

        await self.session.commit()

        # Re-fetch with loaded channels
        fresh_rule = await self.repository.get_by_id(project_id, rule_id)
        assert fresh_rule is not None
        logger.info(
            "Created alert rule id=%s project_id=%s rule_type=%s",
            rule_id,
            project_id,
            rule_in.rule_type,
        )
        return map_rule_to_response(fresh_rule)

    async def update_rule(
        self,
        project_id: uuid.UUID,
        rule_id: uuid.UUID,
        rule_in: AlertRuleUpdate,
    ) -> AlertRuleResponse:
        rule = await self.repository.get_by_id(project_id, rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert rule {rule_id} not found in project {project_id}",
            )

        update_data = rule_in.model_dump(exclude_unset=True)
        channel_ids = update_data.pop("channel_ids", None)

        for key, value in update_data.items():
            setattr(rule, key, value)

        if channel_ids is not None:
            await self.repository.set_channels(rule_id, channel_ids)

        await self.session.commit()

        fresh_rule = await self.repository.get_by_id(project_id, rule_id)
        assert fresh_rule is not None
        logger.info("Updated alert rule id=%s project_id=%s", rule_id, project_id)
        return map_rule_to_response(fresh_rule)

    async def delete_rule(
        self,
        project_id: uuid.UUID,
        rule_id: uuid.UUID,
    ) -> None:
        rule = await self.repository.get_by_id(project_id, rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert rule {rule_id} not found in project {project_id}",
            )

        await self.repository.delete(rule)
        await self.session.commit()
        logger.info("Deleted alert rule id=%s project_id=%s", rule_id, project_id)

