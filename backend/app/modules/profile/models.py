"""ORM models for structured student career profiles and verified skills."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UTCTimestampMixin, UUIDPrimaryKeyMixin


class UserProfile(UUIDPrimaryKeyMixin, UTCTimestampMixin, Base):
    """Structured career profile, job preferences, and consent settings per user."""

    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    headline: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    university: Mapped[str | None] = mapped_column(String(255), nullable=True)
    degree: Mapped[str | None] = mapped_column(String(255), nullable=True)
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    experience_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    years_of_experience: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_roles: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    preferred_locations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    work_mode_preferences: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    linkedin_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ai_consent_given: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notification_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    profile_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    extra_preferences: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class UserSkill(UUIDPrimaryKeyMixin, UTCTimestampMixin, Base):
    """Normalized technical and soft skills owned by a user."""

    __tablename__ = "user_skills"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "normalized_name",
            "category",
            name="uq_user_skills_user_name_category",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="technical")
    proficiency: Mapped[str] = mapped_column(String(50), nullable=False, default="intermediate")
    years_experience: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")

