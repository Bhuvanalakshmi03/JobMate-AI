"""Shared LangGraph workflow state schema and serializable snapshot helpers."""

from __future__ import annotations

from typing import Any, Protocol, TypedDict


class AgentNodeProtocol(Protocol):
    """Async LangGraph node protocol matching LangGraph's named `state` parameter."""

    async def __call__(self, state: CareerPilotAgentState) -> dict[str, Any]: ...


class CareerPilotAgentState(TypedDict):
    """Typed workflow state shared across all LangGraph specialist nodes."""

    user_id: str
    workflow_id: str
    requested_task: str
    requested_task_type: str
    task_category: str
    verified_profile_ref: dict[str, Any]
    job_id: str | None
    resume_id: str | None
    application_id: str | None
    search_query: str | None
    search_location: str | None
    current_stage: str
    rag_context: list[dict[str, Any]]
    agent_outputs: dict[str, Any]
    validation_results: dict[str, Any]
    pending_approval_id: str | None
    approval_decision: str | None
    execution_status: str
    execution_trace: list[dict[str, Any]]
    total_tokens_used: int
    step_count: int
    error_details: str | None


def create_initial_agent_state(
    *,
    user_id: str,
    workflow_id: str,
    requested_task: str,
    requested_task_type: str = "auto",
    job_id: str | None = None,
    resume_id: str | None = None,
    application_id: str | None = None,
    search_query: str | None = None,
    search_location: str | None = None,
) -> CareerPilotAgentState:
    """Create a fully populated initial typed workflow state."""
    return CareerPilotAgentState(
        user_id=user_id,
        workflow_id=workflow_id,
        requested_task=requested_task,
        requested_task_type=requested_task_type,
        task_category=requested_task_type if requested_task_type != "auto" else "",
        verified_profile_ref={},
        job_id=job_id,
        resume_id=resume_id,
        application_id=application_id,
        search_query=search_query,
        search_location=search_location,
        current_stage="initialized",
        rag_context=[],
        agent_outputs={},
        validation_results={},
        pending_approval_id=None,
        approval_decision=None,
        execution_status="RUNNING",
        execution_trace=[],
        total_tokens_used=0,
        step_count=0,
        error_details=None,
    )


def serialize_state_snapshot(state: CareerPilotAgentState) -> dict[str, Any]:
    """Return a clean JSON-serializable state checkpoint dictionary."""
    return dict(state)
