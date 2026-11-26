import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.config import settings

SLUG_REGEX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

RESERVED_PROJECT_SLUGS: frozenset[str] = frozenset(
    {
        "overview",
        "issues",
        "projects",
        "settings",
        "alerts",
        "incidents",
        "investigations",
        "performance",
        "members",
        "billing",
        "api",
        "auth",
        "new",
    }
)


class ProjectCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=150)
    slug: str = Field(..., min_length=1, max_length=100)
    platform: Literal["fastapi"] | None = None
    description: str | None = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not SLUG_REGEX.match(v):
            raise ValueError("Invalid slug format. Must match ^[a-z0-9]+(-[a-z0-9]+)*$")
        if v in RESERVED_PROJECT_SLUGS:
            raise ValueError(f"Project slug '{v}' is reserved and cannot be used")
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


class ReleaseKeyCreateResponse(BaseModel):
    id: uuid.UUID
    key_prefix: str
    token: str


class ReleaseKeyStatusResponse(BaseModel):
    key_prefix: str | None


class ReleaseCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(min_length=1, max_length=150)
    commit_sha: str = Field(min_length=1, max_length=64)
    artifact_ref: str | None = Field(default=None, min_length=1, max_length=300)

    @field_validator("version")
    @classmethod
    def validate_release_version(cls, version: str) -> str:
        if any(char.isspace() or char == "\x00" for char in version):
            raise ValueError("Release version cannot contain whitespace or null characters")
        return version

    @field_validator("commit_sha")
    @classmethod
    def validate_commit_sha(cls, commit_sha: str) -> str:
        if re.fullmatch(r"[0-9a-f]+", commit_sha) is None:
            raise ValueError("Commit SHA must contain only lowercase hexadecimal characters")
        return commit_sha

    @field_validator("artifact_ref")
    @classmethod
    def validate_artifact_ref(cls, artifact_ref: str | None) -> str | None:
        if artifact_ref is not None and "\x00" in artifact_ref:
            raise ValueError("Artifact reference cannot contain null characters")
        return artifact_ref


class ReleaseCreateResponse(BaseModel):
    id: uuid.UUID
    version: str
    commit_sha: str | None


class ReleaseDeploymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    environment: str
    kind: str
    status: str
    external_run_id: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class ReleaseListItem(ReleaseCreateResponse):
    artifact_ref: str | None
    created_at: datetime
    deployments: list[ReleaseDeploymentResponse]
