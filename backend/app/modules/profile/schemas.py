"""Pydantic schemas for user career profiles and skills."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

WorkMode = Literal["remote", "hybrid", "onsite"]
ExperienceLevel = Literal["student", "intern", "entry_level", "junior", "mid_level", "senior"]
SkillCategory = Literal["technical", "soft", "tool", "language", "framework"]
SkillProficiency = Literal["beginner", "intermediate", "advanced", "expert"]


def _validate_http_url(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    parsed = urlparse(trimmed)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("URL must start with http:// or https:// and include a valid host")
    return trimmed


def _clean_string_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for item in values:
        stripped = item.strip()
        if not stripped:
            continue
        key = stripped.lower()
        if key not in seen:
            seen.add(key)
            cleaned.append(stripped)
    return cleaned


class ProfilePayloadBase(BaseModel):
    """Shared validated fields for creating or updating a student career profile."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    headline: str | None = Field(default=None, max_length=255)
    summary: str | None = Field(default=None, max_length=4000)
    phone: str | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=255)
    university: str | None = Field(default=None, max_length=255)
    degree: str | None = Field(default=None, max_length=255)
    graduation_year: int | None = Field(default=None, ge=1970, le=2050)
    experience_level: ExperienceLevel | None = None
    years_of_experience: float | None = Field(default=None, ge=0.0, le=60.0)
    target_roles: list[str] = Field(default_factory=list, max_length=25)
    preferred_locations: list[str] = Field(default_factory=list, max_length=25)
    work_mode_preferences: list[WorkMode] = Field(default_factory=list, max_length=3)
    linkedin_url: str | None = Field(default=None, max_length=512)
    github_url: str | None = Field(default=None, max_length=512)
    portfolio_url: str | None = Field(default=None, max_length=512)
    ai_consent_given: bool = False
    notification_consent: bool = False

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        try:
            ZoneInfo(trimmed)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unsupported IANA timezone: {trimmed}") from exc
        return trimmed

    @field_validator("linkedin_url", "github_url", "portfolio_url")
    @classmethod
    def validate_urls(cls, value: str | None) -> str | None:
        return _validate_http_url(value)

    @field_validator("target_roles", "preferred_locations")
    @classmethod
    def normalize_string_lists(cls, value: list[str]) -> list[str]:
        return _clean_string_list(value)

    @field_validator("work_mode_preferences")
    @classmethod
    def deduplicate_work_modes(cls, value: list[WorkMode]) -> list[WorkMode]:
        seen: set[WorkMode] = set()
        deduped: list[WorkMode] = []
        for mode in value:
            if mode not in seen:
                seen.add(mode)
                deduped.append(mode)
        return deduped


class ProfileCreateRequest(ProfilePayloadBase):
    """Create initial career profile."""


class ProfileUpdateRequest(ProfilePayloadBase):
    """Full update/upsert payload for career profile."""


class ProfileResponse(BaseModel):
    """Career profile response including owner metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    email: str
    timezone: str
    headline: str | None = None
    summary: str | None = None
    phone: str | None = None
    location: str | None = None
    university: str | None = None
    degree: str | None = None
    graduation_year: int | None = None
    experience_level: str | None = None
    years_of_experience: float | None = None
    target_roles: list[str]
    preferred_locations: list[str]
    work_mode_preferences: list[str]
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    ai_consent_given: bool
    notification_consent: bool
    profile_verified: bool
    created_at: datetime
    updated_at: datetime


class SkillItemInput(BaseModel):
    """Single skill input item."""

    name: str = Field(min_length=1, max_length=120)
    category: SkillCategory = "technical"
    proficiency: SkillProficiency = "intermediate"
    years_experience: float | None = Field(default=None, ge=0.0, le=50.0)
    is_verified: bool = True

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Skill name cannot be blank")
        return cleaned


class SkillsUpdateRequest(BaseModel):
    """Payload to replace user's skills list."""

    skills: list[SkillItemInput] = Field(default_factory=list, max_length=100)


class UserSkillResponse(BaseModel):
    """Skill representation returned by API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    normalized_name: str
    category: str
    proficiency: str
    years_experience: float | None = None
    is_verified: bool
    source: str
    created_at: datetime
    updated_at: datetime


class SkillsListResponse(BaseModel):
    """Container response for user skills."""

    skills: list[UserSkillResponse]
    total: int

