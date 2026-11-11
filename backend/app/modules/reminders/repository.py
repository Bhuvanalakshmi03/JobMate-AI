"""Repository for user-scoped reminders and worker due-dispatch queries."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reminders.models import Reminder


class ReminderRepository:
    """Data access layer for deduplicated reminders."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self, *, reminder_id: uuid.UUID, user_id: uuid.UUID
    ) -> Reminder | None:
        return await self._session.scalar(
            select(Reminder).where(
                Reminder.id == reminder_id,
                Reminder.user_id == user_id,
            )
        )

    async def get_by_dedup_key(
        self, *, user_id: uuid.UUID, dedup_key: str
    ) -> Reminder | None:
        return await self._session.scalar(
            select(Reminder).where(
                Reminder.user_id == user_id,
                Reminder.dedup_key == dedup_key,
            )
        )

    async def list_for_user(
        self,
        *,
        user_id: uuid.UUID,
        status: str | None = None,
        limit: int = 50,
    ) -> tuple[list[Reminder], int, int]:
        stmt = select(Reminder).where(Reminder.user_id == user_id)
        count_stmt = (
            select(func.count()).select_from(Reminder).where(Reminder.user_id == user_id)
        )
        if status:
            stmt = stmt.where(Reminder.status == status)
            count_stmt = count_stmt.where(Reminder.status == status)

        total = int((await self._session.scalar(count_stmt)) or 0)
        due_count = int(
            (
                await self._session.scalar(
                    select(func.count())
                    .select_from(Reminder)
                    .where(
                        Reminder.user_id == user_id,
                        Reminder.status == "SENT",
                    )
                )
            )
            or 0
        )
        rows = list(
            (
                await self._session.scalars(
                    stmt.order_by(Reminder.scheduled_for.asc()).limit(limit)
                )
            ).all()
        )
        return rows, total, due_count

    async def list_due_for_dispatch(
        self,
        *,
        now: datetime,
        user_id: uuid.UUID | None = None,
        limit: int = 100,
    ) -> list[Reminder]:
        due_condition = or_(
            (Reminder.status == "SCHEDULED") & (Reminder.scheduled_for <= now),
            (Reminder.status == "FAILED")
            & (Reminder.attempts < Reminder.max_attempts)
            & (Reminder.next_retry_at.is_not(None))
            & (Reminder.next_retry_at <= now),
        )
        stmt = select(Reminder).where(due_condition)
        if user_id is not None:
            stmt = stmt.where(Reminder.user_id == user_id)
        return list(
            (
                await self._session.scalars(
                    stmt.order_by(Reminder.scheduled_for.asc()).limit(limit)
                )
            ).all()
        )

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        application_id: uuid.UUID | None,
        job_id: uuid.UUID | None,
        title: str,
        message: str | None,
        reminder_type: str,
        dedup_key: str | None,
        scheduled_for: datetime,
        user_timezone: str,
        channel: str,
    ) -> Reminder:
        row = Reminder(
            user_id=user_id,
            application_id=application_id,
            job_id=job_id,
            title=title.strip()[:255],
            message=message.strip()[:2000] if message else None,
            reminder_type=reminder_type,
            dedup_key=dedup_key.strip()[:160] if dedup_key else None,
            scheduled_for=scheduled_for,
            user_timezone=user_timezone,
            channel=channel,
            status="SCHEDULED",
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def delete_row(self, row: Reminder) -> None:
        await self._session.delete(row)
        await self._session.flush()
