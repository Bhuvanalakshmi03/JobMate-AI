"""ORM model for encrypted per-user Google Calendar OAuth tokens."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UTCDateTime, UTCTimestampMixin, UUIDPrimaryKeyMixin


class GoogleCalendarConnection(UUIDPrimaryKeyMixin, UTCTimestampMixin, Base):
    """Stores Fernet-encrypted OAuth credentials for one user's Google Calendar."""

    __tablename__ = "google_calendar_connections"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    google_email: Mapped[str] = mapped_column(String(320), nullable=False)
    encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    scopes: Mapped[str] = mapped_column(String(512), nullable=False, default="")
