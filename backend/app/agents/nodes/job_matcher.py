"""Job Matching Agent node computing explainable hybrid match scores."""

from __future__ import annotations

from typing import Any

from app.agents.policies import execute_traced_step
from app.agents.state import AgentNodeProtocol, CareerPilotAgentState
from app.agents.tools.registry import AgentToolset
from app.core.exceptions import ValidationError


def make_job_matcher_node(toolset: AgentToolset) -> AgentNodeProtocol:
    async def job_matcher(state: CareerPilotAgentState) -> dict[str, Any]:
        async def _op() -> dict[str, Any]:
            job_id = state.get("job_id")
            if not job_id:
                raise ValidationError("Select or discover a target job before running matching.")
            return await toolset.match_job(job_id=job_id)

        outcome = await execute_traced_step(
            state,
            node="job_matcher",
            operation=_op,
            detail="Computed hybrid match score.",
            max_tokens=toolset.max_tokens_budget,
        )
        if not outcome.ok or outcome.value is None:
            return {
                "current_stage": "job_matcher",
                "execution_status": "FAILED",
                "error_details": outcome.error_message,
                "execution_trace": outcome.trace,
                "step_count": state.get("step_count", 0) + 1,
            }

        outputs = dict(state.get("agent_outputs", {}))
        outputs["job_matcher"] = outcome.value
        next_status = (
            "COMPLETED"
            if state.get("task_category") == "job_discovery"
            else state.get("execution_status", "RUNNING")
        )
        return {
            "current_stage": "job_matched",
            "agent_outputs": outputs,
            "execution_status": next_status,
            "execution_trace": outcome.trace,
            "step_count": state.get("step_count", 0) + 1,
        }

    return job_matcher
