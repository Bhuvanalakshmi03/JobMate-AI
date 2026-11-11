"""Job Researcher specialist node."""

from __future__ import annotations

from typing import Any

from app.agents.policies import execute_traced_step
from app.agents.state import AgentNodeProtocol, CareerPilotAgentState
from app.agents.tools.registry import AgentToolset


def _derive_search_query(
    *,
    search_query: str | None,
    profile: dict[str, Any],
    requested_task: str,
) -> str:
    if search_query and search_query.strip():
        return search_query.strip()
    roles = profile.get("target_roles") or []
    if roles:
        return str(roles[0])
    skills = profile.get("verified_skill_names") or []
    lowered = requested_task.lower()
    role_hints = ("engineer", "developer", "intern", "analyst", "scientist", "designer", "manager")
    if any(hint in lowered for hint in role_hints):
        return requested_task
    if skills:
        return f"{' '.join(str(s) for s in skills[:3])} engineer"
    return "software engineer intern"


def make_job_researcher_node(toolset: AgentToolset) -> AgentNodeProtocol:
    async def job_researcher(state: CareerPilotAgentState) -> dict[str, Any]:
        async def _op() -> dict[str, Any]:
            profile = state.get("verified_profile_ref") or {}
            locs = profile.get("preferred_locations") or []
            query = _derive_search_query(
                search_query=state.get("search_query"),
                profile=profile,
                requested_task=state["requested_task"],
            )
            location = state.get("search_location") or (str(locs[0]) if locs else None)
            return await toolset.search_jobs(query=query, location=location, limit=5)

        outcome = await execute_traced_step(
            state,
            node="job_researcher",
            operation=_op,
            detail="Executed job discovery.",
            max_tokens=toolset.max_tokens_budget,
        )
        if not outcome.ok or outcome.value is None:
            return {
                "current_stage": "job_researcher",
                "execution_status": "FAILED",
                "error_details": outcome.error_message,
                "execution_trace": outcome.trace,
                "step_count": state.get("step_count", 0) + 1,
            }

        outputs = dict(state.get("agent_outputs", {}))
        outputs["job_researcher"] = outcome.value
        jobs = outcome.value.get("jobs") or []
        resolved_job_id = state.get("job_id") or (str(jobs[0]["id"]) if jobs else None)
        return {
            "current_stage": "jobs_discovered",
            "job_id": resolved_job_id,
            "agent_outputs": outputs,
            "execution_status": (
                "COMPLETED"
                if state.get("task_category") == "job_discovery" and not resolved_job_id
                else state.get("execution_status", "RUNNING")
            ),
            "execution_trace": outcome.trace,
            "step_count": state.get("step_count", 0) + 1,
        }

    return job_researcher
