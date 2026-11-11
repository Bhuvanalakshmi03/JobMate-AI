"""Database repository for ApprovalRequest persistence and user-isolated queries."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.approvals.models import ApprovalRequest


class ApprovalRepository:
    """Data-access layer for pending and historical human approvals."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        action_type: str,
        target_destination: str,
        title: str,
        payload: dict[str, Any],
        workflow_run_id: uuid.UUID | None = None,
        application_id: uuid.UUID | None = None,
    ) -> ApprovalRequest:
        record = ApprovalRequest(
            user_id=user_id,
            workflow_run_id=workflow_run_id,
            application_id=application_id,
            action_type=action_type,
            target_destination=target_destination,
            title=title,
            payload=payload,
            status="PENDING",
        )
        self._session.add(record)
        await self._session.flush()
        await self._session.refresh(record)
        return record

    async def get_by_id_for_user(
        self,
        *,
        approval_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ApprovalRequest | None:
        stmt = select(ApprovalRequest).where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.user_id == user_id,
        )
        return await self._session.scalar(stmt)

    async def list_for_user(
        self,
        *,
        user_id: uuid.UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ApprovalRequest], int, int]:
        base = select(ApprovalRequest).where(ApprovalRequest.user_id == user_id)
        if status:
            base = base.where(ApprovalRequest.status == status)

        total = int(
            await self._session.scalar(select(func.count()).select_from(base.subquery())) or 0
        )
        pending_count = int(
            await self._session.scalar(
                select(func.count())
                .select_from(ApprovalRequest)
                .where(
                    ApprovalRequest.user_id == user_id,
                    ApprovalRequest.status == "PENDING",
                )
            )
            or 0
        )
        rows = list(
            (
                await self._session.scalars(
                    base.order_by(ApprovalRequest.created_at.desc()).limit(limit).offset(offset)
                )
            ).all()
        )
        return rows, total, pending_count
