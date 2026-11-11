"""Task classification node routing user requests to minimal specialist subsets."""

from __future__ import annotations

from typing import Any

from app.agents.policies import execute_traced_step
from app.agents.state import AgentNodeProtocol, CareerPilotAgentState
from app.agents.tools.registry import AgentToolset

VALID_CATEGORIES = frozenset({"job_discovery", "application_prep", "career_advisory"})


def make_task_classifier_node(toolset: AgentToolset) -> AgentNodeProtocol:
    async def task_classifier(state: CareerPilotAgentState) -> dict[str, Any]:
        async def _op() -> tuple[str, str, int]:
            explicit = state.get("requested_task_type", "auto")
            if explicit in VALID_CATEGORIES:
                return explicit, f"Explicitly requested workflow type: {explicit}.", 0
            return await toolset.classify_request(requested_task=state["requested_task"])

        outcome = await execute_traced_step(
            state,
            node="task_classifier",
            operation=_op,
            token_extractor=lambda res: res[2],
            detail="Classified task route.",
            max_tokens=toolset.max_tokens_budget,
        )
        if not outcome.ok or outcome.value is None:
            return {
                "current_stage": "task_classifier",
                "execution_status": "FAILED",
                "error_details": outcome.error_message,
                "execution_trace": outcome.trace,
                "step_count": state.get("step_count", 0) + 1,
            }

        category, reason, tokens = outcome.value
        outputs = dict(state.get("agent_outputs", {}))
        outputs["task_classifier"] = {"task_category": category, "reason": reason}
        return {
            "task_category": category,
            "current_stage": "task_classified",
            "agent_outputs": outputs,
            "execution_trace": outcome.trace,
            "total_tokens_used": state.get("total_tokens_used", 0) + tokens,
            "step_count": state.get("step_count", 0) + 1,
        }

    return task_classifier
