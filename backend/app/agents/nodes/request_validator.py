"""Request validation and verified user profile loading node."""

from __future__ import annotations

from typing import Any

from app.agents.policies import execute_traced_step
from app.agents.state import AgentNodeProtocol, CareerPilotAgentState
from app.agents.tools.registry import AgentToolset
from app.core.exceptions import ValidationError


def make_request_validator_node(toolset: AgentToolset) -> AgentNodeProtocol:
    async def request_validator(state: CareerPilotAgentState) -> dict[str, Any]:
        async def _op() -> dict[str, Any]:
            task = (state.get("requested_task") or "").strip()
            if len(task) < 3:
                raise ValidationError("Workflow request must be at least 3 characters.")
            return await toolset.load_verified_profile()

        outcome = await execute_traced_step(
            state,
            node="request_validator",
            operation=_op,
            detail="Validated workflow request and loaded verified profile.",
            max_tokens=toolset.max_tokens_budget,
            retryable=False,
        )
        if not outcome.ok or outcome.value is None:
            return {
                "current_stage": "request_validator",
                "execution_status": "FAILED",
                "error_details": outcome.error_message,
                "execution_trace": outcome.trace,
                "step_count": state.get("step_count", 0) + 1,
            }

        return {
            "current_stage": "request_validated",
            "verified_profile_ref": outcome.value,
            "execution_trace": outcome.trace,
            "step_count": state.get("step_count", 0) + 1,
        }

    return request_validator
