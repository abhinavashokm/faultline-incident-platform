from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Severity = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]


class CreateIncidentRequest(BaseModel):
    title: Title
    severity: Severity
    description: str | None = None
    related_issue_ids: list[UUID] = Field(default_factory=list)
    assignee_id: UUID | None = None


class CreatedIncident(BaseModel):
    id: UUID
    title: str
    severity: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class IssueSnapshot(BaseModel):
    id: UUID
    title: str
    exception_type: str | None = None
    first_seen: datetime
    last_seen: datetime
    occurrence_count: int
