"""Repository for encrypted per-user Google Calendar OAuth credentials."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.calendar.models import GoogleCalendarConnection


class CalendarConnectionRepository:
    """Data-access layer scoped strictly by user_id."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, user_id: uuid.UUID) -> GoogleCalendarConnection | None:
        return await self._session.scalar(
            select(GoogleCalendarConnection).where(GoogleCalendarConnection.user_id == user_id)
        )

    async def upsert_for_user(
        self,
        *,
        user_id: uuid.UUID,
        google_email: str,
        encrypted_access_token: str,
        encrypted_refresh_token: str | None,
        token_expires_at: datetime | None,
        scopes: str,
    ) -> GoogleCalendarConnection:
        existing = await self.get_by_user_id(user_id)
        if existing is None:
            record = GoogleCalendarConnection(
                user_id=user_id,
                google_email=google_email,
                encrypted_access_token=encrypted_access_token,
                encrypted_refresh_token=encrypted_refresh_token,
                token_expires_at=token_expires_at,
                scopes=scopes,
            )
            self._session.add(record)
        else:
            existing.google_email = google_email
            existing.encrypted_access_token = encrypted_access_token
            if encrypted_refresh_token:
                existing.encrypted_refresh_token = encrypted_refresh_token
            existing.token_expires_at = token_expires_at
            existing.scopes = scopes
            record = existing
        await self._session.flush()
        await self._session.refresh(record)
        return record

    async def delete_for_user(self, user_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(GoogleCalendarConnection).where(GoogleCalendarConnection.user_id == user_id)
        )
        await self._session.flush()
