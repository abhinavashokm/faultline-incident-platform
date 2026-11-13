from typing import Protocol
from uuid import UUID

from faultline_events import IssueCreatedEvent
from app.alerts.models import AlertRule


class RuleMatcher(Protocol):
    """Protocol for evaluating an alert rule against an event."""

    def matches(self, rule: AlertRule, event: IssueCreatedEvent) -> bool:
        """Return True if rule matches the event, False otherwise."""
        ...


class NewIssueMatcher:
    """Matcher for rule_type == 'new_issue'."""

    def matches(self, rule: AlertRule, event: IssueCreatedEvent) -> bool:
        if rule.rule_type != "new_issue":
            return False

        if not rule.enabled:
            return False

        if rule.project_id != event.project_id:
            return False

        payload = event.payload

        # Environment filter: check rule.environment first, then rule.conditions["environment"] if present
        target_env = rule.environment
        if not target_env and isinstance(rule.conditions, dict):
            target_env = rule.conditions.get("environment")

        if target_env:
            if not payload.environment or payload.environment.lower() != target_env.lower():
                return False

        # Level filter: check rule.conditions["level"] if present
        if isinstance(rule.conditions, dict) and "level" in rule.conditions:
            cond_level = rule.conditions["level"]
            if cond_level:
                if isinstance(cond_level, list):
                    if payload.level.lower() not in [l.lower() for l in cond_level]:
                        return False
                elif isinstance(cond_level, str):
                    if payload.level.lower() != cond_level.lower():
                        return False

        return True


MATCHER_REGISTRY: dict[str, RuleMatcher] = {
    "new_issue": NewIssueMatcher(),
}


def get_matcher(rule_type: str) -> RuleMatcher | None:
    """Retrieve rule matcher by rule_type."""
    return MATCHER_REGISTRY.get(rule_type)
