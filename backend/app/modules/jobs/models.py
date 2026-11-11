"""ORM models for normalized discovered job listings and user-saved jobs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UTCDateTime, UTCTimestampMixin, UUIDPrimaryKeyMixin, utc_now


class Job(UUIDPrimaryKeyMixin, UTCTimestampMixin, Base):
    """Normalized external job posting discovered via authorized search providers."""

    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_active_posted", "is_active", "posted_at"),
        Index("ix_jobs_work_exp", "work_mode", "experience_level"),
    )

    source_provider: Mapped[str] = mapped_column(
        String(64), nullable=False, default="openai_web_search"
    )
    canonical_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    work_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    experience_level: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    employment_type: Mapped[str] = mapped_column(String(50), nullable=False, default="full_time")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    requirements_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    preferred_skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    education_requirements: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    min_years_experience: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_range: Mapped[str | None] = mapped_column(String(120), nullable=True)
    external_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    embedding_vector: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    raw_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class SavedJob(UUIDPrimaryKeyMixin, Base):
    """Bookmarks linking an authenticated user to saved jobs."""

    __tablename__ = "saved_jobs"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_saved_jobs_user_job"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
