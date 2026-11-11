"""Pydantic schemas for Google Calendar status, events, and event creation."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CalendarStatusResponse(BaseModel):
    """Indicates whether the current user has authorized Google Calendar access."""

    connected: bool
    google_email: str | None = None
    scopes: list[str] = Field(default_factory=list)
    token_expires_at: datetime | None = None


class CalendarEventItem(BaseModel):
    """Normalized Google Calendar event entry."""

    event_id: str
    summary: str
    start_iso: str
    end_iso: str
    location: str | None = None
    description: str | None = None
    html_link: str | None = None
    status: str = "confirmed"


class CalendarEventsResponse(BaseModel):
    """Upcoming Google Calendar events response."""

    connected: bool
    items: list[CalendarEventItem] = Field(default_factory=list)


class CalendarEventCreateRequest(BaseModel):
    """Request payload for creating a Google Calendar event."""

    summary: str = Field(min_length=1, max_length=250)
    start_iso: str = Field(min_length=10, max_length=64)
    end_iso: str = Field(min_length=10, max_length=64)
    description: str | None = Field(default=None, max_length=4000)
    location: str | None = Field(default=None, max_length=500)
    timezone: str | None = Field(default=None, max_length=64)
