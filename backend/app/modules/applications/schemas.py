"""Pydantic schemas for application tracking, controlled transitions, and analytics."""

from __future__ import annotations

import uuid
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.applications.state_machine import ApplicationStatus


def _validate_optional_http_url(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    parsed = urlparse(trimmed)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("job_url must start with http:// or https://")
    return trimmed


class ApplicationCreateRequest(BaseModel):
    """Create a tracked job application from a discovered job or custom entry."""

    job_id: uuid.UUID | None = None
    company_name: str | None = Field(default=None, min_length=1, max_length=255)
    role_title: str | None = Field(default=None, min_length=1, max_length=255)
    job_url: str | None = Field(default=None, max_length=1024)
    location: str | None = Field(default=None, max_length=255)
    tailored_resume_id: uuid.UUID | None = None
    cover_letter_id: uuid.UUID | None = None
    deadline_at: datetime | None = None
    follow_up_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("job_url")
    @classmethod
    def validate_job_url(cls, value: str | None) -> str | None:
        return _validate_optional_http_url(value)


class ApplicationUpdateRequest(BaseModel):
    """Update mutable application metadata (status must change only via /transition)."""

    company_name: str | None = Field(default=None, min_length=1, max_length=255)
    role_title: str | None = Field(default=None, min_length=1, max_length=255)
    job_url: str | None = Field(default=None, max_length=1024)
    location: str | None = Field(default=None, max_length=255)
    tailored_resume_id: uuid.UUID | None = None
    cover_letter_id: uuid.UUID | None = None
    deadline_at: datetime | None = None
    follow_up_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("job_url")
    @classmethod
    def validate_job_url(cls, value: str | None) -> str | None:
        return _validate_optional_http_url(value)


class ApplicationTransitionRequest(BaseModel):
    """Explicit controlled status transition payload."""

    target_status: ApplicationStatus
    note: str | None = Field(default=None, max_length=2000)


class ApplicationHistoryItem(BaseModel):
    """Single historical status transition entry."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    from_status: str | None = None
    to_status: str
    note: str | None = None
    changed_at: datetime


class ApplicationResponse(BaseModel):
    """Application summary and allowed next transitions."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID | None = None
    tailored_resume_id: uuid.UUID | None = None
    cover_letter_id: uuid.UUID | None = None
    company_name: str
    role_title: str
    job_url: str | None = None
    location: str | None = None
    status: str
    allowed_next_statuses: list[ApplicationStatus] = Field(default_factory=list)
    applied_at: datetime | None = None
    deadline_at: datetime | None = None
    follow_up_at: datetime | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ApplicationDetailResponse(ApplicationResponse):
    """Application details including full transition timeline."""

    history: list[ApplicationHistoryItem] = Field(default_factory=list)


class ApplicationListResponse(BaseModel):
    """Paginated list of tracked applications."""

    items: list[ApplicationResponse]
    total: int


class ApplicationSummaryResponse(BaseModel):
    """Dashboard summary counts by status and upcoming deadlines."""

    total_applications: int
    counts_by_status: dict[str, int]
    upcoming_deadlines: list[ApplicationResponse]
