"""Shared API v1 schemas for health, pagination, async tasks, and error envelopes."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Consistent structured error detail returned on failures."""

    code: str
    message: str
    details: dict[str, Any] | list[Any] | None = None
    request_id: str | None = None
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Top-level error envelope."""

    error: ErrorDetail


class PaginationMeta(BaseModel):
    """Pagination metadata for list endpoints."""

    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated list response."""

    items: list[T]
    meta: PaginationMeta


class TaskStatusResponse(BaseModel):
    """Asynchronous background job acknowledgement schema."""

    task_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    message: str


class DependencyStatus(BaseModel):
    """Individual dependency readiness check status."""

    status: Literal["healthy", "unavailable", "unhealthy"]
    detail: str | None = None


class HealthResponse(BaseModel):
    """Process liveness response."""

    status: Literal["ok"]
    service: str
    version: str
    environment: str
    timestamp: datetime


class ReadinessResponse(BaseModel):
    """Dependency readiness response."""

    status: Literal["ready", "degraded", "unavailable"]
    service: str
    version: str
    environment: str
    timestamp: datetime
    dependencies: dict[str, DependencyStatus]

