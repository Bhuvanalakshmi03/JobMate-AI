"""ORM model for consent-gated persistent career memory."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UTCTimestampMixin, UUIDPrimaryKeyMixin


class CareerMemory(UUIDPrimaryKeyMixin, UTCTimestampMixin, Base):
    """User-approved career preference, goal, strength, or working note."""

    __tablename__ = "career_memory"
    __table_args__ = (
        UniqueConstraint("user_id", "memory_key", name="uq_career_memory_user_key"),
        Index("ix_career_memory_user_active", "user_id", "is_active"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="preference")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="user_manual")
    memory_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
