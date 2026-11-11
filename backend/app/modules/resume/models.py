"""ORM models for uploaded resumes and extracted verifiable career facts."""

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
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UTCDateTime, UTCTimestampMixin, UUIDPrimaryKeyMixin


class Resume(UUIDPrimaryKeyMixin, UTCTimestampMixin, Base):
    """Metadata, parsed text, and evaluation summary for an uploaded student resume."""

    __tablename__ = "resumes"
    __table_args__ = (
        Index("ix_resumes_user_created", "user_id", "created_at"),
        Index("ix_resumes_user_sha256", "user_id", "sha256_hash"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(16), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="uploaded", index=True
    )
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    completeness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    analysis_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    analyzed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class ResumeFact(UUIDPrimaryKeyMixin, UTCTimestampMixin, Base):
    """Structured fact extracted from a resume awaiting or holding user verification."""

    __tablename__ = "resume_facts"
    __table_args__ = (
        Index("ix_resume_facts_resume_type", "resume_id", "fact_type"),
        Index("ix_resume_facts_user_verified", "user_id", "is_verified"),
    )

    resume_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fact_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    source_section: Mapped[str | None] = mapped_column(String(100), nullable=True)
    evidence_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    verified_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
