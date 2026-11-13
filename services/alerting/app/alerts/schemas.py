from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AlertRuleChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    channel_type: str


class AlertRuleBase(BaseModel):
    name: str = Field(..., max_length=150)
    rule_type: str = Field(..., max_length=50)
    conditions: dict[str, Any] = Field(default_factory=dict)
    recovery_conditions: dict[str, Any] | None = None
    severity: str = Field(default="warning", max_length=30)
    environment: str | None = Field(default=None, max_length=100)
    enabled: bool = True
    minimum_event_count: int | None = None
    window_seconds: int | None = None
    cooldown_seconds: int | None = None


class AlertRuleCreate(AlertRuleBase):
    channel_ids: list[UUID] = Field(default_factory=list)


class AlertRuleUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=150)
    rule_type: str | None = Field(default=None, max_length=50)
    conditions: dict[str, Any] | None = None
    recovery_conditions: dict[str, Any] | None = None
    severity: str | None = Field(default=None, max_length=30)
    environment: str | None = Field(default=None, max_length=100)
    enabled: bool | None = None
    minimum_event_count: int | None = None
    window_seconds: int | None = None
    cooldown_seconds: int | None = None
    channel_ids: list[UUID] | None = None


class AlertRuleResponse(AlertRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    created_by: UUID | None = None
    channels: list[AlertRuleChannelResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime | None = None


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    rule_id: UUID
    state_id: UUID
    title: str
    severity: str
    status: str
    occurrence_count: int
    first_triggered_at: datetime
    last_triggered_at: datetime
    acknowledged_by: UUID | None = None
    acknowledged_at: datetime | None = None
    recovered_at: datetime | None = None
    details: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime | None = None
