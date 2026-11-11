"""ORM models for persistent Co-Pilot chat sessions and tool-calling message logs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UTCDateTime, UTCTimestampMixin, UUIDPrimaryKeyMixin, utc_now


class CopilotConversation(UUIDPrimaryKeyMixin, UTCTimestampMixin, Base):
    """User-owned multi-turn Co-Pilot chat conversation session."""

    __tablename__ = "copilot_conversations"
    __table_args__ = (
        Index("ix_copilot_conversations_user_recent", "user_id", "last_message_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="New Co-Pilot Chat")
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_message_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, nullable=False
    )


class CopilotMessage(UUIDPrimaryKeyMixin, Base):
    """Single message turn in a Co-Pilot chat session with executed tools & approvals."""

    __tablename__ = "copilot_messages"
    __table_args__ = (
        Index("ix_copilot_messages_conv_created", "conversation_id", "created_at"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("copilot_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    approval_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
