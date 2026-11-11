"""Timezone-aware reminder scheduling, deduplication, cancellation, and retry dispatch."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.database.base import utc_now
from app.modules.applications.repository import ApplicationRepository
from app.modules.authentication.models import User
from app.modules.profile.repository import ProfileRepository
from app.modules.reminders.models import Reminder
from app.modules.reminders.repository import ReminderRepository
from app.modules.reminders.schemas import (
    ReminderCreateRequest,
    ReminderDispatchSummary,
    ReminderListResponse,
    ReminderResponse,
    ReminderUpdateRequest,
)
from app.repositories.audit_repository import AuditLogRepository

logger = get_logger(__name__)


class NotificationDispatcherProtocol(Protocol):
    """Protocol decoupling reminder notification delivery for clean worker testing."""

    async def deliver(self, *, reminder: Reminder) -> None: ...


class InAppNotificationDispatcher:
    """Default durable in-app notification recorder backed by structured logging."""

    async def deliver(self, *, reminder: Reminder) -> None:
        logger.info(
            "Reminder notification dispatched",
            extra={
                "reminder_id": str(reminder.id),
                "user_id": str(reminder.user_id),
                "channel": reminder.channel,
                "reminder_type": reminder.reminder_type,
            },
        )


def normalize_to_utc(dt: datetime, user_timezone: str) -> datetime:
    """Convert naive or zoned datetimes safely to UTC using the user's IANA timezone."""
    if dt.tzinfo is not None:
        return dt.astimezone(UTC)
    tz = ZoneInfo(user_timezone)
    return dt.replace(tzinfo=tz).astimezone(UTC)


class ReminderService:
    """Coordinates deduplicated reminder scheduling, timezone handling, and dispatch retries."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        dispatcher: NotificationDispatcherProtocol | None = None,
    ) -> None:
        self._session = session
        self._dispatcher: NotificationDispatcherProtocol = (
            dispatcher or InAppNotificationDispatcher()
        )
        self._repo = ReminderRepository(session)
        self._apps = ApplicationRepository(session)
        self._profiles = ProfileRepository(session)
        self._audit = AuditLogRepository(session)

    async def create_reminder(
        self,
        *,
        user: User,
        payload: ReminderCreateRequest,
    ) -> ReminderResponse:
        if payload.application_id is not None:
            app = await self._apps.get_by_id_for_user(
                application_id=payload.application_id, user_id=user.id
            )
            if app is None:
                raise NotFoundError("Linked application not found.")

        if payload.channel == "email_digest":
            profile = await self._profiles.get_by_user_id(user.id)
            if profile is None or not profile.notification_consent:
                raise ValidationError(
                    "Enable notification consent in Privacy & Memory settings before "
                    "scheduling external digest reminders."
                )

        resolved_tz = payload.timezone or user.timezone or "UTC"
        scheduled_utc = normalize_to_utc(payload.scheduled_for, resolved_tz)

        if payload.dedup_key and payload.dedup_key.strip():
            clean_key = payload.dedup_key.strip()[:160]
            existing = await self._repo.get_by_dedup_key(
                user_id=user.id, dedup_key=clean_key
            )
            if existing is not None:
                # Guarantee zero duplicate reminders: update/reactivate existing if cancelled,
                # or return existing idempotently without inserting a duplicate row.
                if existing.status in ("CANCELLED", "DISMISSED"):
                    existing.title = payload.title.strip()[:255]
                    existing.message = payload.message.strip()[:2000] if payload.message else None
                    existing.scheduled_for = scheduled_utc
                    existing.user_timezone = resolved_tz
                    existing.status = "SCHEDULED"
                    existing.attempts = 0
                    existing.last_error = None
                    existing.next_retry_at = None
                    await self._session.flush()
                    await self._session.refresh(existing)
                return ReminderResponse.model_validate(existing)

        row = await self._repo.create(
            user_id=user.id,
            application_id=payload.application_id,
            job_id=payload.job_id,
            title=payload.title,
            message=payload.message,
            reminder_type=payload.reminder_type,
            dedup_key=payload.dedup_key,
            scheduled_for=scheduled_utc,
            user_timezone=resolved_tz,
            channel=payload.channel,
        )
        await self._audit.record(
            event_type="reminder.scheduled",
            user_id=user.id,
            resource_type="reminder",
            resource_id=str(row.id),
            details={"scheduled_for": scheduled_utc.isoformat(), "timezone": resolved_tz},
        )
        return ReminderResponse.model_validate(row)

    async def list_reminders(
        self, *, user: User, status: str | None = None
    ) -> ReminderListResponse:
        rows, total, due_count = await self._repo.list_for_user(
            user_id=user.id, status=status
        )
        return ReminderListResponse(
            items=[ReminderResponse.model_validate(r) for r in rows],
            total=total,
            due_notifications_count=due_count,
        )

    async def update_reminder(
        self,
        *,
        user: User,
        reminder_id: uuid.UUID,
        payload: ReminderUpdateRequest,
    ) -> ReminderResponse:
        row = await self._repo.get_by_id(reminder_id=reminder_id, user_id=user.id)
        if row is None:
            raise NotFoundError("Reminder not found.")
        if row.status in ("CANCELLED", "DISMISSED"):
            raise ValidationError(f"Cannot edit a reminder in '{row.status}' state.")

        if payload.title is not None:
            row.title = payload.title.strip()[:255]
        if payload.message is not None:
            row.message = payload.message.strip()[:2000]
        if payload.timezone is not None:
            row.user_timezone = payload.timezone
        if payload.scheduled_for is not None:
            row.scheduled_for = normalize_to_utc(payload.scheduled_for, row.user_timezone)
            row.status = "SCHEDULED"
            row.next_retry_at = None

        await self._session.flush()
        await self._session.refresh(row)
        return ReminderResponse.model_validate(row)

    async def cancel_reminder(self, *, user: User, reminder_id: uuid.UUID) -> ReminderResponse:
        row = await self._repo.get_by_id(reminder_id=reminder_id, user_id=user.id)
        if row is None:
            raise NotFoundError("Reminder not found.")
        row.status = "CANCELLED"
        row.next_retry_at = None
        await self._session.flush()
        await self._session.refresh(row)
        await self._audit.record(
            event_type="reminder.cancelled",
            user_id=user.id,
            resource_type="reminder",
            resource_id=str(row.id),
        )
        return ReminderResponse.model_validate(row)

    async def dismiss_reminder(self, *, user: User, reminder_id: uuid.UUID) -> ReminderResponse:
        row = await self._repo.get_by_id(reminder_id=reminder_id, user_id=user.id)
        if row is None:
            raise NotFoundError("Reminder not found.")
        row.status = "DISMISSED"
        await self._session.flush()
        await self._session.refresh(row)
        return ReminderResponse.model_validate(row)

    async def delete_reminder(self, *, user: User, reminder_id: uuid.UUID) -> None:
        row = await self._repo.get_by_id(reminder_id=reminder_id, user_id=user.id)
        if row is None:
            raise NotFoundError("Reminder not found.")
        await self._repo.delete_row(row)

    async def dispatch_due_reminders(
        self,
        *,
        user_id: uuid.UUID | None = None,
        now_utc: datetime | None = None,
    ) -> ReminderDispatchSummary:
        """Process due reminders without duplicate delivery and with bounded backoff retries."""
        now = now_utc or utc_now()
        due_rows = await self._repo.list_due_for_dispatch(now=now, user_id=user_id, limit=100)

        sent_count = 0
        failed_count = 0
        retried_scheduled = 0

        for reminder in due_rows:
            if reminder.status == "SENT":
                continue
            reminder.attempts += 1
            try:
                await self._dispatcher.deliver(reminder=reminder)
                reminder.status = "SENT"
                reminder.sent_at = now
                reminder.last_error = None
                reminder.next_retry_at = None
                sent_count += 1
                await self._audit.record(
                    event_type="reminder.dispatched",
                    user_id=reminder.user_id,
                    resource_type="reminder",
                    resource_id=str(reminder.id),
                    details={"attempts": reminder.attempts, "channel": reminder.channel},
                )
            except Exception as exc:
                failed_count += 1
                reminder.status = "FAILED"
                reminder.last_error = (str(exc) or exc.__class__.__name__)[:500]
                if reminder.attempts < reminder.max_attempts:
                    backoff_minutes = 5 * (2 ** (reminder.attempts - 1))
                    reminder.next_retry_at = now + timedelta(minutes=backoff_minutes)
                    retried_scheduled += 1
                else:
                    reminder.next_retry_at = None

        await self._session.flush()
        return ReminderDispatchSummary(
            processed=len(due_rows),
            sent=sent_count,
            failed=failed_count,
            retried_scheduled=retried_scheduled,
        )
