from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Method regex pattern or uppercase validator
HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


class RouteMetric(BaseModel):
    """Metric item for an endpoint within a performance batch interval."""

    route: str = Field(..., max_length=500, description="Normalized route template")
    method: str = Field(..., description="HTTP method")
    request_count: int = Field(..., ge=0, description="Total requests within the interval")
    error_count: int = Field(..., ge=0, description="Total errors within the interval")
    status_counts: dict[str, int] = Field(
        default_factory=dict,
        description="HTTP status code counts, e.g. {'200': 90, '500': 5}",
    )
    latency_histogram: dict[str, int] = Field(
        default_factory=dict,
        description="Latency histogram counts, e.g. {'le_100ms': 20, 'gt_1s': 5}",
    )

    model_config = ConfigDict(extra="ignore")

    @field_validator("method")
    @classmethod
    def normalize_method(cls, v: str) -> str:
        v = v.strip().upper()
        if len(v) > 10:
            raise ValueError("method must be at most 10 characters")
        return v

    @field_validator("route")
    @classmethod
    def normalize_route(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("route cannot be empty")
        return v

    @field_validator("status_counts")
    @classmethod
    def validate_status_counts(cls, v: dict[str, int]) -> dict[str, int]:
        for code, count in v.items():
            if count < 0:
                raise ValueError(f"status count for {code} cannot be negative")
        return v

    @field_validator("latency_histogram")
    @classmethod
    def validate_latency_histogram(cls, v: dict[str, int]) -> dict[str, int]:
        for bucket, count in v.items():
            if count < 0:
                raise ValueError(f"histogram count for {bucket} cannot be negative")
        return v


class PerformanceBatchIngestRequest(BaseModel):
    """Client request schema for performance batch ingestion."""

    batch_id: UUID = Field(..., description="Unique client/SDK generated batch identifier")
    environment: str = Field(default="production", max_length=100)
    release: str = Field(default="unknown", max_length=150)
    interval_start: datetime = Field(..., description="Start of interval in UTC")
    interval_end: datetime = Field(..., description="End of interval in UTC")
    metrics: list[RouteMetric] = Field(
        default_factory=list,
        description="Aggregated route metrics collected during the interval",
    )

    model_config = ConfigDict(extra="ignore")

    @field_validator("environment")
    @classmethod
    def normalize_environment(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            return "production"
        if len(v) > 100:
            raise ValueError("environment must be at most 100 characters")
        return v

    @field_validator("release")
    @classmethod
    def normalize_release(cls, v: str) -> str:
        v = v.strip()
        if not v:
            return "unknown"
        if len(v) > 150:
            raise ValueError("release must be at most 150 characters")
        return v


class PerformanceIngestResponse(BaseModel):
    """SDK response schema for accepted performance batches."""

    accepted: bool = True
    batch_id: UUID
