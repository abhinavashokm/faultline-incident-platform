from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T", bound=Any)


class EventEnvelope(BaseModel, Generic[T]):
    """Versioned Kafka event envelope for inter-service event communication."""

    schema_version: int = Field(default=1, description="Event envelope schema version")
    event_id: UUID = Field(..., description="Unique event identifier")
    workspace_id: UUID = Field(..., description="Tenant workspace identifier")
    project_id: UUID = Field(..., description="Project identifier")
    received_at: datetime = Field(..., description="UTC timestamp when the server received the event")
    payload: T = Field(..., description="Normalized event payload")

