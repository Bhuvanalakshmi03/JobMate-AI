"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AuthConfigResponse(BaseModel):
    """Public authentication capability flags exposed to the login screen."""

    google_oauth_enabled: bool
    dev_auth_enabled: bool


class AuthUrlResponse(BaseModel):
    """Authorization URL returned when initiating OAuth in JSON mode."""

    authorization_url: str
    state: str


class UserResponse(BaseModel):
    """Authenticated user account projection."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    avatar_url: str | None = None
    oauth_provider: str
    timezone: str
    last_login_at: datetime | None = None
    created_at: datetime
    is_demo_auth: bool = False


class AuthSessionResponse(BaseModel):
    """Session login response returned to API clients."""

    user: UserResponse
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105
    expires_at: datetime
    is_demo_auth: bool = False


class DevLoginRequest(BaseModel):
    """Development-only login request (disabled in staging and production)."""

    email: str = Field(default="student@careerpilot.local", min_length=5, max_length=320)
    full_name: str = Field(default="Demo Student", min_length=1, max_length=255)
    timezone: str = Field(default="UTC", min_length=1, max_length=64)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if "@" not in cleaned or "." not in cleaned.split("@", 1)[-1]:
            raise ValueError("A valid email address is required")
        return cleaned


class LogoutResponse(BaseModel):
    """Logout acknowledgement."""

    logged_out: bool = True
    message: str = "Session terminated successfully."
