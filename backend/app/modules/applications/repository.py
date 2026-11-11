"""Repositories for job applications and transition history scoped by user_id."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import utc_now
from app.modules.applications.models import Application, ApplicationHistory


class ApplicationRepository:
    """Data access layer for Application and ApplicationHistory scoped by user_id."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id_for_user(
        self,
        *,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Application | None:
        return await self._session.scalar(
            select(Application).where(
                Application.id == application_id,
                Application.user_id == user_id,
            )
        )

    async def get_by_user_and_job(
        self,
        *,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> Application | None:
        return await self._session.scalar(
            select(Application).where(
                Application.user_id == user_id,
                Application.job_id == job_id,
            )
        )

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        job_id: uuid.UUID | None,
        tailored_resume_id: uuid.UUID | None,
        cover_letter_id: uuid.UUID | None,
        company_name: str,
        role_title: str,
        job_url: str | None,
        location: str | None,
        deadline_at: datetime | None,
        follow_up_at: datetime | None,
        notes: str | None,
    ) -> Application:
        app = Application(
            user_id=user_id,
            job_id=job_id,
            tailored_resume_id=tailored_resume_id,
            cover_letter_id=cover_letter_id,
            company_name=company_name,
            role_title=role_title,
            job_url=job_url,
            location=location,
            status="SAVED",
            deadline_at=deadline_at,
            follow_up_at=follow_up_at,
            notes=notes,
        )
        self._session.add(app)
        await self._session.flush()
        return app

    async def add_history(
        self,
        *,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
        from_status: str | None,
        to_status: str,
        note: str | None = None,
    ) -> ApplicationHistory:
        entry = ApplicationHistory(
            application_id=application_id,
            user_id=user_id,
            from_status=from_status,
            to_status=to_status,
            note=note,
            changed_at=utc_now(),
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def list_history(
        self,
        *,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[ApplicationHistory]:
        rows = await self._session.scalars(
            select(ApplicationHistory)
            .where(
                ApplicationHistory.application_id == application_id,
                ApplicationHistory.user_id == user_id,
            )
            .order_by(ApplicationHistory.changed_at.desc())
        )
        return list(rows.all())

    async def list_for_user(
        self,
        *,
        user_id: uuid.UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Application], int]:
        stmt = select(Application).where(Application.user_id == user_id)
        count_stmt = (
            select(func.count())
            .select_from(Application)
            .where(Application.user_id == user_id)
        )
        if status and status.strip():
            normalized = status.strip().upper()
            stmt = stmt.where(Application.status == normalized)
            count_stmt = count_stmt.where(Application.status == normalized)

        total = await self._session.scalar(count_stmt)
        rows = await self._session.scalars(
            stmt.order_by(Application.updated_at.desc()).limit(limit).offset(offset)
        )
        return list(rows.all()), int(total or 0)

    async def list_all_for_summary(self, *, user_id: uuid.UUID) -> list[Application]:
        rows = await self._session.scalars(
            select(Application)
            .where(Application.user_id == user_id)
            .order_by(Application.deadline_at.asc(), Application.updated_at.desc())
        )
        return list(rows.all())

    async def delete_record(self, application: Application) -> None:
        await self._session.delete(application)
        await self._session.flush()
