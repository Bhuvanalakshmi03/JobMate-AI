"""ORM models for job application tracking and status transition history."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UTCDateTime, UTCTimestampMixin, UUIDPrimaryKeyMixin, utc_now


class Application(UUIDPrimaryKeyMixin, UTCTimestampMixin, Base):
    """Tracked student job application tied to a normalized job and tailored documents."""

    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_applications_user_job"),
        Index("ix_applications_user_status", "user_id", "status"),
        Index("ix_applications_user_deadline", "user_id", "deadline_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tailored_resume_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("generated_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    cover_letter_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("generated_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_title: Mapped[str] = mapped_column(String(255), nullable=False)
    job_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SAVED", index=True)
    applied_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True, index=True)
    follow_up_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ApplicationHistory(UUIDPrimaryKeyMixin, Base):
    """Immutable audit timeline of application status transitions."""

    __tablename__ = "application_history"
    __table_args__ = (
        Index("ix_app_history_app_changed", "application_id", "changed_at"),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
