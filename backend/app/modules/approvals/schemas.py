"""Pydantic schemas for Human Approval System endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ApprovalActionType = Literal[
    "submit_application",
    "send_recruiter_email",
    "upload_external_resume",
    "send_application_message",
]

ApprovalStatus = Literal[
    "PENDING",
    "APPROVED",
    "REJECTED",
    "EXECUTED",
    "FAILED",
    "CANCELLED",
]


class ApprovalCreateRequest(BaseModel):
    """Request preparation of a user-gated external action approval."""

    action_type: ApprovalActionType = "submit_application"
    application_id: uuid.UUID | None = None
    target_destination: str = Field(min_length=1, max_length=1024)
    title: str = Field(min_length=2, max_length=255)
    payload: dict[str, Any] = Field(default_factory=dict)


class ApprovalDecisionRequest(BaseModel):
    """Explicit user confirmation or rejection note for a pending approval."""

    note: str | None = Field(default=None, max_length=2000)


class ApprovalResponse(BaseModel):
    """Serialized human approval record including prepared payload and execution status."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    workflow_run_id: uuid.UUID | None = None
    application_id: uuid.UUID | None = None
    action_type: str
    target_destination: str
    title: str
    payload: dict[str, Any]
    status: str
    decision_note: str | None = None
    decided_at: datetime | None = None
    executed_at: datetime | None = None
    execution_result: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class ApprovalListResponse(BaseModel):
    """Paginated list of human approval requests."""

    items: list[ApprovalResponse]
    total: int
    pending_count: int
