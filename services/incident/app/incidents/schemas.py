from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_serializer

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Severity = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]


class CreateIncidentRequest(BaseModel):
    title: Title
    severity: Severity
    description: str | None = None
    related_issue_ids: list[UUID] = Field(default_factory=list)
    assignee_id: UUID | None = None


class UpdateIncidentDetailsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title
    severity: Severity
    description: str | None
    related_issue_ids: list[UUID] | None = None


class CreatedIncident(BaseModel):
    id: UUID
    title: str
    severity: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class IncidentListItem(CreatedIncident):
    assignee_id: UUID | None = Field(validation_alias="assigned_to")
    started_at: datetime

    @field_serializer("started_at")
    def serialize_started_at(self, value: datetime) -> str:
        return utc_isoformat(value)


def utc_isoformat(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


class RelatedIssue(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    issue_id: UUID
    issue_title: str | None
    error_type: str | None
    occurrence_count: int | None


class TimelineEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    message: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return utc_isoformat(value)


class IncidentDetail(IncidentListItem):
    description: str | None
    related_issues: list[RelatedIssue]
    timeline: list[TimelineEntry]


class IssueSnapshot(BaseModel):
    id: UUID
    title: str
    exception_type: str | None = None
    first_seen: datetime
    last_seen: datetime
    occurrence_count: int
