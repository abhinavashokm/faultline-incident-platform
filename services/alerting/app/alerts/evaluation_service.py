import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from faultline_events import IssueCreatedEvent
from app.alerts.evaluation_repository import AlertEvaluationRepository
from app.alerts.matcher import get_matcher
from app.alerts.repository import AlertRuleRepository

logger = logging.getLogger(__name__)


class AlertEvaluationService:
    """Service for evaluating rules against consumed events and creating alerts & delivery jobs in outbox."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def handle_issue_created(self, event: IssueCreatedEvent) -> bool:
        """Evaluate rules for issue.created event in a single database transaction.
        
        Returns True if event was processed, False if it was already processed (duplicate).
        """
        async with self.session_factory() as session:
            async with session.begin():
                eval_repo = AlertEvaluationRepository(session)
                rule_repo = AlertRuleRepository(session)

                # 1. Idempotency check via processed_events table
                inserted = await eval_repo.record_processed_event(
                    event_id=event.event_id,
                    project_id=event.project_id,
                    event_type=event.event_type,
                )
                if not inserted:
                    logger.info(
                        "Duplicate event skipped (already processed): event_id=%s project_id=%s",
                        event.event_id,
                        event.project_id,
                    )
                    return False

                # 2. Fetch enabled rules for the project
                rules = await rule_repo.list_enabled_by_project(event.project_id)
                now = datetime.now(timezone.utc)
                payload = event.payload

                for rule in rules:
                    matcher = get_matcher(rule.rule_type)
                    if not matcher or not matcher.matches(rule, event):
                        continue

                    logger.info(
                        "Alert rule matched: rule_id=%s rule_name=%s issue_id=%s",
                        rule.id,
                        rule.name,
                        payload.issue_id,
                    )

                    # Deduplication key per issue and rule
                    dedup_key = f"issue:{payload.issue_id}"

                    # 3. Alert state
                    state = await eval_repo.get_or_create_alert_state(
                        rule_id=rule.id,
                        project_id=rule.project_id,
                        deduplication_key=dedup_key,
                        now=now,
                    )

                    # 4. Create Alert row
                    alert_title = f"New issue: {payload.title}"
                    alert = await eval_repo.create_alert(
                        rule_id=rule.id,
                        state_id=state.id,
                        project_id=rule.project_id,
                        title=alert_title,
                        severity=rule.severity,
                        now=now,
                        details={
                            "issue_id": str(payload.issue_id),
                            "title": payload.title,
                            "level": payload.level,
                            "environment": payload.environment,
                            "release": payload.release,
                            "first_seen": payload.first_seen.isoformat(),
                        },
                    )

                    # 5. Create Delivery outbox jobs for rule's channels
                    channels = [
                        assoc.channel
                        for assoc in rule.channel_associations
                        if assoc.channel is not None
                    ]

                    delivery_payload: dict[str, Any] = {
                        "event_type": event.event_type,
                        "issue_id": str(payload.issue_id),
                        "project_id": str(event.project_id),
                        "workspace_id": str(event.workspace_id),
                        "title": payload.title,
                        "level": payload.level,
                        "environment": payload.environment,
                        "release": payload.release,
                        "first_seen": payload.first_seen.isoformat(),
                        "alert_id": str(alert.id),
                        "rule_name": rule.name,
                    }

                    deliveries = await eval_repo.create_delivery_jobs(
                        alert=alert,
                        channels=channels,
                        payload=delivery_payload,
                    )
                    logger.info(
                        "Created %d delivery job(s) for alert_id=%s",
                        len(deliveries),
                        alert.id,
                    )

        return True
