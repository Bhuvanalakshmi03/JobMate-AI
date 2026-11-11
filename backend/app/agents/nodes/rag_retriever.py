"""User-isolated RAG context retrieval node."""

from __future__ import annotations

from typing import Any

from app.agents.policies import execute_traced_step
from app.agents.state import AgentNodeProtocol, CareerPilotAgentState
from app.agents.tools.registry import AgentToolset


def make_rag_retriever_node(toolset: AgentToolset) -> AgentNodeProtocol:
    async def rag_retriever(state: CareerPilotAgentState) -> dict[str, Any]:
        async def _op() -> list[dict[str, Any]]:
            return await toolset.retrieve_rag_context(
                query=state["requested_task"],
                top_k=5,
            )

        outcome = await execute_traced_step(
            state,
            node="rag_retriever",
            operation=_op,
            detail="Retrieved user-isolated RAG career context.",
            max_tokens=toolset.max_tokens_budget,
        )
        hits = outcome.value if outcome.ok and outcome.value is not None else []
        outputs = dict(state.get("agent_outputs", {}))
        outputs["rag_retriever"] = {"chunk_count": len(hits)}
        return {
            "current_stage": "rag_retrieved",
            "rag_context": hits,
            "agent_outputs": outputs,
            "execution_trace": outcome.trace,
            "step_count": state.get("step_count", 0) + 1,
        }

    return rag_retriever
