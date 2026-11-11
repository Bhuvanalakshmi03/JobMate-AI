"""Pydantic schemas for multi-agent workflow orchestration and RAG endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

WorkflowTaskType = Literal["auto", "job_discovery", "application_prep", "career_advisory"]


class WorkflowCreateRequest(BaseModel):
    """Trigger a CareerPilot LangGraph multi-agent workflow."""

    requested_task: str = Field(min_length=3, max_length=2000)
    task_type: WorkflowTaskType = "auto"
    job_id: uuid.UUID | None = None
    resume_id: uuid.UUID | None = None
    application_id: uuid.UUID | None = None
    search_query: str | None = Field(default=None, max_length=255)
    search_location: str | None = Field(default=None, max_length=255)


class TraceEntryResponse(BaseModel):
    """Execution telemetry entry for a single specialist node."""

    node: str
    status: str
    attempts: int
    duration_ms: float
    tokens_used: int = 0
    detail: str | None = None
    timestamp: str


class WorkflowRunResponse(BaseModel):
    """Persisted multi-agent workflow run state, outputs, and execution trace."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID | None = None
    application_id: uuid.UUID | None = None
    task_type: str
    user_request: str
    current_stage: str
    status: str
    agent_outputs: dict[str, Any]
    validation_results: dict[str, Any]
    pending_approval_id: uuid.UUID | None = None
    execution_trace: list[dict[str, Any]]
    total_tokens_used: int
    error_detail: str | None = None
    created_at: datetime
    updated_at: datetime


class WorkflowListResponse(BaseModel):
    """Paginated list of user workflow runs."""

    items: list[WorkflowRunResponse]
    total: int


class RAGSyncResponse(BaseModel):
    """Telemetry returned after indexing user career context into vector storage."""

    indexed_chunks: int
    skipped_duplicates: int
    source_counts: dict[str, int]


class RAGQueryRequest(BaseModel):
    """Semantic query over user-isolated career context."""

    query: str = Field(min_length=2, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)
    source_types: list[str] | None = None


class RAGHitResponse(BaseModel):
    """Sanitized retrieved RAG chunk."""

    chunk_id: str
    score: float
    source_type: str | None = None
    label: str | None = None
    text: str


class RAGQueryResponse(BaseModel):
    """Semantic retrieval response strictly scoped to authenticated user."""

    query: str
    hits: list[RAGHitResponse]
