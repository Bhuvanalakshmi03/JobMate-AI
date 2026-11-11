"""Pydantic schemas for deduplicated reminders and notification dispatch."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

ReminderType = Literal["deadline", "follow_up", "interview", "study_plan", "custom"]
ReminderChannel = Literal["in_app", "email_digest"]
ReminderStatus = Literal["SCHEDULED", "SENT", "FAILED", "CANCELLED", "DISMISSED"]


def _validate_iana_timezone(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        ZoneInfo(cleaned)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown IANA timezone '{cleaned}'.") from exc
    return cleaned


class ReminderCreateRequest(BaseModel):
    """Schedule a timezone-aware reminder with optional deduplication key."""

    title: str = Field(min_length=2, max_length=255)
    message: str | None = Field(default=None, max_length=2000)
    reminder_type: ReminderType = "custom"
    application_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    dedup_key: str | None = Field(default=None, max_length=160)
    scheduled_for: datetime
    timezone: str | None = Field(default=None, max_length=64)
    channel: ReminderChannel = "in_app"

    @field_validator("timezone")
    @classmethod
    def check_timezone(cls, value: str | None) -> str | None:
        return _validate_iana_timezone(value)


class ReminderUpdateRequest(BaseModel):
    """Update a reminder title, message, or scheduled timestamp."""

    title: str | None = Field(default=None, min_length=2, max_length=255)
    message: str | None = Field(default=None, max_length=2000)
    scheduled_for: datetime | None = None
    timezone: str | None = Field(default=None, max_length=64)

    @field_validator("timezone")
    @classmethod
    def check_timezone(cls, value: str | None) -> str | None:
        return _validate_iana_timezone(value)


class ReminderResponse(BaseModel):
    """Serialized reminder with UTC timestamp and user timezone."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    application_id: uuid.UUID | None
    job_id: uuid.UUID | None
    title: str
    message: str | None
    reminder_type: str
    dedup_key: str | None
    scheduled_for: datetime
    user_timezone: str
    channel: str
    status: str
    attempts: int
    max_attempts: int
    last_error: str | None
    sent_at: datetime | None
    next_retry_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReminderListResponse(BaseModel):
    """List of reminders with scheduled and due-notification counters."""

    items: list[ReminderResponse]
    total: int
    due_notifications_count: int


class ReminderDispatchSummary(BaseModel):
    """Result summary from a reminder dispatch run."""

    processed: int
    sent: int
    failed: int
    retried_scheduled: int
