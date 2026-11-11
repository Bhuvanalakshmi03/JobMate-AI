"""ORM model for scheduled reminders and notification delivery tracking."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UTCDateTime, UTCTimestampMixin, UUIDPrimaryKeyMixin


class Reminder(UUIDPrimaryKeyMixin, UTCTimestampMixin, Base):
    """Deduplicated user reminder supporting timezone conversion, cancellation, and retries."""

    __tablename__ = "reminders"
    __table_args__ = (
        UniqueConstraint("user_id", "dedup_key", name="uq_reminders_user_dedup"),
        Index("ix_reminders_user_status_sched", "user_id", "status", "scheduled_for"),
        Index("ix_reminders_due_lookup", "status", "scheduled_for"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("applications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    reminder_type: Mapped[str] = mapped_column(String(32), nullable=False, default="custom")
    dedup_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    scheduled_for: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    user_timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="in_app")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SCHEDULED", index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
