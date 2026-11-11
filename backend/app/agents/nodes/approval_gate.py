"""Human approval gate node pausing workflow before external submission side effects."""

from __future__ import annotations

from typing import Any

from app.agents.policies import execute_traced_step
from app.agents.state import AgentNodeProtocol, CareerPilotAgentState
from app.agents.tools.registry import AgentToolset
from app.core.exceptions import ValidationError


def make_approval_gate_node(toolset: AgentToolset) -> AgentNodeProtocol:
    async def approval_gate(state: CareerPilotAgentState) -> dict[str, Any]:
        async def _op() -> dict[str, Any]:
            job_id = state.get("job_id")
            if not job_id:
                raise ValidationError("Target job_id is required before requesting approval.")
            outputs = state.get("agent_outputs", {})
            return await toolset.prepare_submission_approval(
                workflow_id=state["workflow_id"],
                job_id=job_id,
                application_id=state.get("application_id"),
                documents_output=dict(outputs.get("document_drafter") or {}),
                match_output=outputs.get("job_matcher"),
                requested_task=state["requested_task"],
            )

        outcome = await execute_traced_step(
            state,
            node="approval_gate",
            operation=_op,
            detail="Prepared approval payload and paused workflow awaiting human confirmation.",
            max_tokens=toolset.max_tokens_budget,
            retryable=False,
        )
        if not outcome.ok or outcome.value is None:
            return {
                "current_stage": "approval_gate",
                "execution_status": "FAILED",
                "error_details": outcome.error_message,
                "execution_trace": outcome.trace,
                "step_count": state.get("step_count", 0) + 1,
            }

        outputs = dict(state.get("agent_outputs", {}))
        outputs["approval_gate"] = outcome.value
        return {
            "current_stage": "awaiting_human_approval",
            "application_id": outcome.value["application_id"],
            "pending_approval_id": outcome.value["approval_id"],
            "execution_status": "PAUSED_FOR_APPROVAL",
            "agent_outputs": outputs,
            "execution_trace": outcome.trace,
            "step_count": state.get("step_count", 0) + 1,
        }

    return approval_gate
