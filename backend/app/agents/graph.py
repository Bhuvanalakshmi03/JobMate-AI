"""Compiled LangGraph multi-agent workflow orchestrator with pause/resume routing."""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.nodes.action_executor import make_action_executor_node
from app.agents.nodes.advisory_responder import make_advisory_responder_node
from app.agents.nodes.approval_gate import make_approval_gate_node
from app.agents.nodes.document_drafter import make_document_drafter_node
from app.agents.nodes.job_matcher import make_job_matcher_node
from app.agents.nodes.job_researcher import make_job_researcher_node
from app.agents.nodes.rag_retriever import make_rag_retriever_node
from app.agents.nodes.request_validator import make_request_validator_node
from app.agents.nodes.task_classifier import make_task_classifier_node
from app.agents.state import CareerPilotAgentState
from app.agents.tools.registry import AgentToolset


def _route_entry(state: CareerPilotAgentState) -> str:
    if state.get("pending_approval_id") and state.get("approval_decision") in (
        "APPROVED",
        "REJECTED",
    ):
        return "action_executor"
    return "request_validator"


def _route_after_validation(state: CareerPilotAgentState) -> str:
    if state.get("execution_status") == "FAILED":
        return END
    return "task_classifier"


def _route_after_classification(state: CareerPilotAgentState) -> str:
    if state.get("execution_status") == "FAILED":
        return END
    return "rag_retriever"


def _route_after_rag(state: CareerPilotAgentState) -> str:
    category = state.get("task_category", "career_advisory")
    if category == "job_discovery":
        return "job_researcher"
    if category == "application_prep":
        if state.get("job_id"):
            return "job_matcher"
        return "job_researcher"
    return "advisory_responder"


def _route_after_research(state: CareerPilotAgentState) -> str:
    if state.get("execution_status") == "FAILED":
        return END
    if state.get("job_id"):
        return "job_matcher"
    return END


def _route_after_match(state: CareerPilotAgentState) -> str:
    if state.get("execution_status") == "FAILED":
        return END
    if state.get("task_category") == "application_prep":
        return "document_drafter"
    return END


def _route_after_draft(state: CareerPilotAgentState) -> str:
    if state.get("execution_status") == "FAILED":
        return END
    return "approval_gate"


def _route_after_approval_gate(state: CareerPilotAgentState) -> str:
    if state.get("execution_status") == "FAILED":
        return END
    if state.get("approval_decision") in ("APPROVED", "REJECTED"):
        return "action_executor"
    return END


def build_careerpilot_graph(
    *,
    toolset: AgentToolset,
    checkpointer: Any | None = None,
) -> Any:
    """Build and compile the CareerPilot LangGraph StateGraph orchestrator."""
    builder: StateGraph[
        CareerPilotAgentState,
        None,
        CareerPilotAgentState,
        CareerPilotAgentState,
    ] = StateGraph(CareerPilotAgentState)

    builder.add_node("request_validator", make_request_validator_node(toolset))
    builder.add_node("task_classifier", make_task_classifier_node(toolset))
    builder.add_node("rag_retriever", make_rag_retriever_node(toolset))
    builder.add_node("job_researcher", make_job_researcher_node(toolset))
    builder.add_node("job_matcher", make_job_matcher_node(toolset))
    builder.add_node("document_drafter", make_document_drafter_node(toolset))
    builder.add_node("approval_gate", make_approval_gate_node(toolset))
    builder.add_node("action_executor", make_action_executor_node(toolset))
    builder.add_node("advisory_responder", make_advisory_responder_node(toolset))

    builder.add_conditional_edges(
        START,
        _route_entry,
        {
            "request_validator": "request_validator",
            "action_executor": "action_executor",
        },
    )
    builder.add_conditional_edges(
        "request_validator",
        _route_after_validation,
        {"task_classifier": "task_classifier", END: END},
    )
    builder.add_conditional_edges(
        "task_classifier",
        _route_after_classification,
        {"rag_retriever": "rag_retriever", END: END},
    )
    builder.add_conditional_edges(
        "rag_retriever",
        _route_after_rag,
        {
            "job_researcher": "job_researcher",
            "job_matcher": "job_matcher",
            "advisory_responder": "advisory_responder",
        },
    )
    builder.add_conditional_edges(
        "job_researcher",
        _route_after_research,
        {"job_matcher": "job_matcher", END: END},
    )
    builder.add_conditional_edges(
        "job_matcher",
        _route_after_match,
        {"document_drafter": "document_drafter", END: END},
    )
    builder.add_conditional_edges(
        "document_drafter",
        _route_after_draft,
        {"approval_gate": "approval_gate", END: END},
    )
    builder.add_conditional_edges(
        "approval_gate",
        _route_after_approval_gate,
        {"action_executor": "action_executor", END: END},
    )
    builder.add_edge("advisory_responder", END)
    builder.add_edge("action_executor", END)

    active_checkpointer = checkpointer if checkpointer is not None else InMemorySaver()
    return builder.compile(checkpointer=active_checkpointer)
