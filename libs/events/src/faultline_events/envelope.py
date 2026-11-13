from datetime import datetime, timezone
from typing import Annotated, Any, Generic, Literal, TypeVar, Union
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T", bound=Any)


class EventEnvelope(BaseModel, Generic[T]):
    """Generic event envelope for backwards compatibility with existing producers."""

    schema_version: int = Field(default=1, description="Event envelope schema version")
    event_id: UUID = Field(..., description="Unique event identifier")
    workspace_id: UUID = Field(..., description="Tenant workspace identifier")
    project_id: UUID = Field(..., description="Project identifier")
    received_at: datetime | None = Field(default=None, description="UTC timestamp when the server received the event")
    occurred_at: datetime | None = Field(default=None, description="UTC timestamp when the event occurred")
    event_type: str | None = Field(default=None, description="Event type name")
    payload: T = Field(..., description="Normalized event payload")


class IssueCreatedPayload(BaseModel):
    """Payload for issue.created event."""

    issue_id: UUID = Field(..., description="Unique issue identifier")
    title: str = Field(..., description="Issue title")
    level: str = Field(..., description="Issue level (error, warning, fatal)")
    environment: str | None = Field(default=None, description="Environment where the issue occurred")
    release: str | None = Field(default=None, description="Release/version string")
    first_seen: datetime = Field(..., description="UTC timestamp when the issue was first seen")


class IssueCreatedEvent(BaseModel):
    """Typed event envelope for issue.created."""

    event_id: UUID = Field(..., description="Unique event identifier")
    event_type: Literal["issue.created"] = Field(default="issue.created", description="Event type")
    schema_version: int = Field(default=1, description="Event envelope schema version")
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp")
    workspace_id: UUID = Field(..., description="Tenant workspace identifier")
    project_id: UUID = Field(..., description="Project identifier")
    payload: IssueCreatedPayload = Field(..., description="issue.created payload")


# Discriminated union of all issue events
IssueEvent = Annotated[
    Union[IssueCreatedEvent],
    Field(discriminator="event_type"),
]


# Kafka topic constants
TOPIC_ISSUE_EVENTS = "issue-events"
TOPIC_ERROR_EVENTS = "error-events"
TOPIC_PERF_METRICS = "perf-metrics"
