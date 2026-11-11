"""Database repository for WorkflowRun checkpoints and user-isolated queries."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agents.models import WorkflowRun


class WorkflowRunRepository:
    """Persists and queries multi-agent workflow runs scoped strictly by user_id."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        task_type: str,
        user_request: str,
        job_id: uuid.UUID | None = None,
        application_id: uuid.UUID | None = None,
    ) -> WorkflowRun:
        record = WorkflowRun(
            user_id=user_id,
            job_id=job_id,
            application_id=application_id,
            task_type=task_type,
            user_request=user_request,
            current_stage="initialized",
            status="RUNNING",
            state_snapshot={},
            agent_outputs={},
            validation_results={},
            execution_trace=[],
            total_tokens_used=0,
        )
        self._session.add(record)
        await self._session.flush()
        await self._session.refresh(record)
        return record

    async def get_by_id_for_user(
        self,
        *,
        workflow_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> WorkflowRun | None:
        return await self._session.scalar(
            select(WorkflowRun).where(
                WorkflowRun.id == workflow_id,
                WorkflowRun.user_id == user_id,
            )
        )

    async def list_for_user(
        self,
        *,
        user_id: uuid.UUID,
        limit: int = 30,
        offset: int = 0,
    ) -> tuple[list[WorkflowRun], int]:
        base = select(WorkflowRun).where(WorkflowRun.user_id == user_id)
        total = int(
            await self._session.scalar(select(func.count()).select_from(base.subquery())) or 0
        )
        rows = list(
            (
                await self._session.scalars(
                    base.order_by(WorkflowRun.created_at.desc()).limit(limit).offset(offset)
                )
            ).all()
        )
        return rows, total

    async def apply_state(
        self,
        record: WorkflowRun,
        *,
        state: dict[str, Any],
    ) -> WorkflowRun:
        resolved_job_id = state.get("job_id")
        resolved_app_id = state.get("application_id")
        resolved_approval_id = state.get("pending_approval_id")
        resolved_category = state.get("task_category")

        record.job_id = uuid.UUID(str(resolved_job_id)) if resolved_job_id else record.job_id
        record.application_id = (
            uuid.UUID(str(resolved_app_id)) if resolved_app_id else record.application_id
        )
        record.pending_approval_id = (
            uuid.UUID(str(resolved_approval_id)) if resolved_approval_id else None
        )
        if resolved_category:
            record.task_type = str(resolved_category)
        record.current_stage = str(state.get("current_stage", record.current_stage))
        record.status = str(state.get("execution_status", record.status))
        record.state_snapshot = dict(state)
        record.agent_outputs = dict(state.get("agent_outputs", {}))
        record.validation_results = dict(state.get("validation_results", {}))
        record.execution_trace = list(state.get("execution_trace", []))
        record.total_tokens_used = int(state.get("total_tokens_used", 0))
        record.error_detail = (
            str(state["error_details"]) if state.get("error_details") else None
        )
        await self._session.flush()
        await self._session.refresh(record)
        return record
