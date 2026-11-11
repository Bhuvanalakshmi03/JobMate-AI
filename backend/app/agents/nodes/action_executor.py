"""Post-approval action execution node strictly guarded by user confirmation."""

from __future__ import annotations

from typing import Any

from app.agents.policies import execute_traced_step
from app.agents.state import AgentNodeProtocol, CareerPilotAgentState
from app.agents.tools.registry import AgentToolset
from app.core.exceptions import ValidationError


def make_action_executor_node(toolset: AgentToolset) -> AgentNodeProtocol:
    async def action_executor(state: CareerPilotAgentState) -> dict[str, Any]:
        decision = state.get("approval_decision")

        async def _op() -> dict[str, Any]:
            if decision not in ("APPROVED", "REJECTED"):
                raise ValidationError(
                    "External workflow execution is blocked until explicit human approval."
                )
            await toolset.record_workflow_audit(
                event_type=f"agent.workflow_{decision.lower()}",
                workflow_id=state["workflow_id"],
                details={
                    "pending_approval_id": state.get("pending_approval_id"),
                    "application_id": state.get("application_id"),
                    "decision": decision,
                },
            )
            return {"decision": decision, "executed": decision == "APPROVED"}

        outcome = await execute_traced_step(
            state,
            node="action_executor",
            operation=_op,
            detail=f"Processed explicit approval decision ({decision}).",
            max_tokens=toolset.max_tokens_budget,
            retryable=False,
        )
        if not outcome.ok or outcome.value is None:
            return {
                "current_stage": "action_executor",
                "execution_status": "FAILED",
                "error_details": outcome.error_message,
                "execution_trace": outcome.trace,
                "step_count": state.get("step_count", 0) + 1,
            }

        outputs = dict(state.get("agent_outputs", {}))
        outputs["action_executor"] = outcome.value
        final_status = "COMPLETED" if decision == "APPROVED" else "CANCELLED"
        final_stage = "action_executed" if decision == "APPROVED" else "approval_rejected"
        return {
            "current_stage": final_stage,
            "execution_status": final_status,
            "agent_outputs": outputs,
            "execution_trace": outcome.trace,
            "step_count": state.get("step_count", 0) + 1,
        }

    return action_executor
