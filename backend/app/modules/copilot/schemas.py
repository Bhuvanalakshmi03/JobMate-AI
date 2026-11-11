"""Pydantic schemas for session-managed Co-Pilot conversations and messages."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.approvals.schemas import ApprovalResponse


class ConversationCreateRequest(BaseModel):
    """Create a new persistent Co-Pilot conversation session."""

    title: str | None = Field(default=None, min_length=1, max_length=200)


class ConversationUpdateRequest(BaseModel):
    """Rename or archive an existing conversation session."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    is_archived: bool | None = None


class ConversationSummary(BaseModel):
    """Conversation metadata displayed in the Co-Pilot sidebar."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    is_archived: bool
    last_message_at: datetime
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    """List of Co-Pilot chat conversations."""

    items: list[ConversationSummary]
    total: int


class ChatMessageResponse(BaseModel):
    """Single chat message with executed tool telemetry and linked approval IDs."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    approval_ids: list[str] = Field(default_factory=list)
    tokens_used: int
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    """Full conversation session including chronological messages."""

    conversation: ConversationSummary
    messages: list[ChatMessageResponse]
    approvals: list[ApprovalResponse] = Field(default_factory=list)


class MessageSendRequest(BaseModel):
    """Send a user message into a Co-Pilot chat session."""

    message: str = Field(min_length=1, max_length=4000)


class ChatTurnResponse(BaseModel):
    """Completed conversational turn including created approvals ready for confirmation."""

    conversation: ConversationSummary
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
    created_approvals: list[ApprovalResponse] = Field(default_factory=list)
