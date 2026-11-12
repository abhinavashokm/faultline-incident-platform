from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from app.perf.histograms import HISTOGRAM_BUCKETS

T = TypeVar("T")


class EventEnvelope(BaseModel, Generic[T]):
    schema_version: int = Field(default=1)
    event_id: UUID
    workspace_id: UUID
    project_id: UUID
    received_at: datetime
    payload: T

    model_config = ConfigDict(extra="ignore")


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
    histogram_version: int = Field(..., description="Histogram version defining bucket boundaries")
    latency_histogram: list[int] = Field(
        ...,
        description="Latency histogram bucket counts matching the histogram version boundaries",
    )

    model_config = ConfigDict(extra="ignore")

    @field_validator("method")
    @classmethod
    def normalize_method(cls, v: str) -> str:
        v = v.strip().upper()
        if len(v) > 10:
            raise PydanticCustomError("value_error", "method must be at most 10 characters")
        return v

    @field_validator("route")
    @classmethod
    def normalize_route(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise PydanticCustomError("value_error", "route cannot be empty")
        return v

    @field_validator("status_counts")
    @classmethod
    def validate_status_counts(cls, v: dict[str, int]) -> dict[str, int]:
        for code, count in v.items():
            if count < 0:
                raise PydanticCustomError(
                    "value_error", f"status count for {code} cannot be negative"
                )
        return v

    @field_validator("histogram_version")
    @classmethod
    def validate_histogram_version(cls, v: int) -> int:
        if v not in HISTOGRAM_BUCKETS:
            raise PydanticCustomError(
                "value_error",
                f"Unknown histogram_version {v}. Supported versions: {sorted(HISTOGRAM_BUCKETS.keys())}",
            )
        return v

    @field_validator("latency_histogram")
    @classmethod
    def validate_latency_histogram_counts(cls, v: list[int]) -> list[int]:
        for count in v:
            if count < 0:
                raise PydanticCustomError(
                    "value_error", f"Histogram count cannot be negative: {count}"
                )
        return v

    @model_validator(mode="after")
    def validate_histogram_buckets(self) -> "RouteMetric":
        version = self.histogram_version
        if version not in HISTOGRAM_BUCKETS:
            raise PydanticCustomError(
                "value_error",
                f"Unknown histogram_version {version}. Supported versions: {sorted(HISTOGRAM_BUCKETS.keys())}",
            )
        expected_len = len(HISTOGRAM_BUCKETS[version])
        actual_len = len(self.latency_histogram)
        if actual_len != expected_len:
            raise PydanticCustomError(
                "value_error",
                f"latency_histogram length ({actual_len}) does not match expected length ({expected_len}) for histogram_version {version}",
            )
        return self


class NormalizedPerformanceBatch(BaseModel):
    """Normalized performance batch payload packaged inside EventEnvelope from Kafka."""

    batch_id: UUID
    environment: str = Field(default="production", max_length=100)
    release: str = Field(default="unknown", max_length=150)
    interval_start: datetime
    interval_end: datetime
    metrics: list[RouteMetric] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")

    @field_validator("environment")
    @classmethod
    def normalize_environment(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            return "production"
        if len(v) > 100:
            raise PydanticCustomError("value_error", "environment must be at most 100 characters")
        return v

    @field_validator("release")
    @classmethod
    def normalize_release(cls, v: str) -> str:
        v = v.strip()
        if not v:
            return "unknown"
        if len(v) > 150:
            raise PydanticCustomError("value_error", "release must be at most 150 characters")
        return v
