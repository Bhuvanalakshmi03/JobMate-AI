"""Document Drafting Agent node producing verified tailored resumes and cover letters."""

from __future__ import annotations

from typing import Any

from app.agents.policies import execute_traced_step
from app.agents.state import AgentNodeProtocol, CareerPilotAgentState
from app.agents.tools.registry import AgentToolset
from app.core.exceptions import ValidationError


def make_document_drafter_node(toolset: AgentToolset) -> AgentNodeProtocol:
    async def document_drafter(state: CareerPilotAgentState) -> dict[str, Any]:
        async def _op() -> dict[str, Any]:
            job_id = state.get("job_id")
            if not job_id:
                raise ValidationError("Target job_id is required to draft application documents.")
            return await toolset.prepare_documents(
                job_id=job_id,
                resume_id=state.get("resume_id"),
                focus_instructions=state.get("requested_task"),
            )

        outcome = await execute_traced_step(
            state,
            node="document_drafter",
            operation=_op,
            token_extractor=lambda res: int(res.get("tokens_used", 0)),
            detail="Generated and factuality-checked tailored resume and cover letter.",
            max_tokens=toolset.max_tokens_budget,
        )
        if not outcome.ok or outcome.value is None:
            return {
                "current_stage": "document_drafter",
                "execution_status": "FAILED",
                "error_details": outcome.error_message,
                "execution_trace": outcome.trace,
                "step_count": state.get("step_count", 0) + 1,
            }

        outputs = dict(state.get("agent_outputs", {}))
        outputs["document_drafter"] = outcome.value
        validations = dict(state.get("validation_results", {}))
        validations["documents_grounded"] = bool(
            (outcome.value.get("tailored_resume") or {}).get("is_grounded")
            and (outcome.value.get("cover_letter") or {}).get("is_grounded")
        )
        return {
            "current_stage": "documents_drafted",
            "agent_outputs": outputs,
            "validation_results": validations,
            "execution_trace": outcome.trace,
            "total_tokens_used": state.get("total_tokens_used", 0) + outcome.tokens_used,
            "step_count": state.get("step_count", 0) + 1,
        }

    return document_drafter
