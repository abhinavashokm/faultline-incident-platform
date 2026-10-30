import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.config import settings

SLUG_REGEX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class ProjectCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=150)
    slug: str = Field(..., min_length=1, max_length=100)
    platform: Literal["python", "fastapi", "django"] | None = None
    description: str | None = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not SLUG_REGEX.match(v):
            raise ValueError("Invalid slug format. Must match ^[a-z0-9]+(-[a-z0-9]+)*$")
        return v


class ProjectUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None

    @model_validator(mode="before")
    @classmethod
    def check_non_empty(cls, data: object) -> object:
        if not isinstance(data, dict) or not data:
            raise ValueError("Request body cannot be empty")
        return data


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    platform: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class ProjectCreateResponse(ProjectResponse):
    dsn: str


class ProjectSettingsResponse(BaseModel):
    project_id: uuid.UUID
    retention_days: int
    ignored_status_codes: list[int]
    version: int
    updated_at: datetime

    @field_validator("ignored_status_codes", mode="before")
    @classmethod
    def default_ignored_status_codes(cls, v: list[int] | None) -> list[int]:
        return v if v is not None else []


class ProjectSettingsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retention_days: int | None = None
    ignored_status_codes: list[int] | None = None

    @model_validator(mode="before")
    @classmethod
    def check_non_empty(cls, data: object) -> object:
        if not isinstance(data, dict) or not data:
            raise ValueError("Request body cannot be empty")
        return data

    @field_validator("retention_days")
    @classmethod
    def validate_retention_days(cls, v: int | None) -> int | None:
        if v is not None:
            if v < 1 or v > settings.retention_days_max:
                raise ValueError(
                    f"retention_days must be between 1 and {settings.retention_days_max}"
                )
        return v

    @field_validator("ignored_status_codes")
    @classmethod
    def validate_ignored_status_codes(cls, codes: list[int] | None) -> list[int] | None:
        if codes is not None:
            deduped: list[int] = []
            seen: set[int] = set()
            for code in codes:
                if not (100 <= code <= 599):
                    raise ValueError(
                        f"HTTP status code {code} must be between 100 and 599"
                    )
                if code not in seen:
                    seen.add(code)
                    deduped.append(code)
            if len(deduped) > 50:
                raise ValueError("ignored_status_codes cannot contain more than 50 items")
            return deduped
        return codes


class ProjectApiKeyResponse(BaseModel):
    id: uuid.UUID
    key_type: str
    dsn: str
    last_used_at: datetime | None = None
    created_at: datetime

