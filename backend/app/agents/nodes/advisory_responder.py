"""Career Advisory Agent node generating RAG-grounded guidance."""

from __future__ import annotations

from typing import Any

from app.agents.policies import execute_traced_step
from app.agents.state import AgentNodeProtocol, CareerPilotAgentState
from app.agents.tools.registry import AgentToolset


def make_advisory_responder_node(toolset: AgentToolset) -> AgentNodeProtocol:
    async def advisory_responder(state: CareerPilotAgentState) -> dict[str, Any]:
        async def _op() -> dict[str, Any]:
            return await toolset.generate_advisory(
                requested_task=state["requested_task"],
                profile_ref=state.get("verified_profile_ref") or {},
                rag_context=list(state.get("rag_context", [])),
            )

        outcome = await execute_traced_step(
            state,
            node="advisory_responder",
            operation=_op,
            token_extractor=lambda res: int(res.get("tokens_used", 0)),
            detail="Generated RAG-grounded career advisory.",
            max_tokens=toolset.max_tokens_budget,
        )
        if not outcome.ok or outcome.value is None:
            return {
                "current_stage": "advisory_responder",
                "execution_status": "FAILED",
                "error_details": outcome.error_message,
                "execution_trace": outcome.trace,
                "step_count": state.get("step_count", 0) + 1,
            }

        outputs = dict(state.get("agent_outputs", {}))
        outputs["advisory_responder"] = outcome.value
        return {
            "current_stage": "advisory_completed",
            "execution_status": "COMPLETED",
            "agent_outputs": outputs,
            "execution_trace": outcome.trace,
            "total_tokens_used": state.get("total_tokens_used", 0) + outcome.tokens_used,
            "step_count": state.get("step_count", 0) + 1,
        }

    return advisory_responder
