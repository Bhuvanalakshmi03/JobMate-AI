"""Pydantic schemas for Career Memory CRUD and user privacy consent controls."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MemoryCategory = Literal["preference", "goal", "strength", "weakness", "note"]
MemorySource = Literal["user_manual", "copilot_proposed", "interview_feedback"]


class MemoryConsentUpdateRequest(BaseModel):
    """Explicit consent flags controlling Career Memory and notification delivery."""

    ai_consent_given: bool
    notification_consent: bool | None = None


class MemoryConsentResponse(BaseModel):
    """Current privacy consent status for the authenticated user."""

    ai_consent_given: bool
    notification_consent: bool


class CareerMemoryCreateRequest(BaseModel):
    """Create or upsert a user-approved Career Memory entry."""

    category: MemoryCategory = "preference"
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=3, max_length=3000)
    source: MemorySource = "user_manual"
    memory_key: str | None = Field(default=None, max_length=120)
    is_approved: bool = True


class CareerMemoryUpdateRequest(BaseModel):
    """Update an existing Career Memory item or toggle approval/active state."""

    category: MemoryCategory | None = None
    title: str | None = Field(default=None, min_length=2, max_length=200)
    content: str | None = Field(default=None, min_length=3, max_length=3000)
    is_approved: bool | None = None
    is_active: bool | None = None


class CareerMemoryResponse(BaseModel):
    """Serialized Career Memory entry."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    category: str
    title: str
    content: str
    source: str
    memory_key: str | None
    is_approved: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CareerMemoryListResponse(BaseModel):
    """List of Career Memory items paired with the user's consent flags."""

    consent: MemoryConsentResponse
    items: list[CareerMemoryResponse]
    total: int
