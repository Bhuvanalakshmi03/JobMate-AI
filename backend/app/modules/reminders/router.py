"""Reminders & notification delivery API v1 routes (/api/v1/reminders/*)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import DBSessionDep
from app.modules.authentication.dependencies import CurrentUserDep
from app.modules.reminders.schemas import (
    ReminderCreateRequest,
    ReminderDispatchSummary,
    ReminderListResponse,
    ReminderResponse,
    ReminderUpdateRequest,
)
from app.modules.reminders.service import ReminderService

router = APIRouter(prefix="/reminders", tags=["Reminders & Notifications"])


def get_reminder_service(session: DBSessionDep) -> ReminderService:
    return ReminderService(session=session)


ReminderServiceDep = Annotated[ReminderService, Depends(get_reminder_service)]


@router.get(
    "",
    response_model=ReminderListResponse,
    summary="List reminders and due in-app notifications for the current user",
)
async def list_reminders(
    current_user: CurrentUserDep,
    service: ReminderServiceDep,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> ReminderListResponse:
    return await service.list_reminders(user=current_user, status=status_filter)


@router.post(
    "",
    response_model=ReminderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule a deduplicated, timezone-aware reminder",
)
async def create_reminder(
    payload: ReminderCreateRequest,
    current_user: CurrentUserDep,
    service: ReminderServiceDep,
) -> ReminderResponse:
    return await service.create_reminder(user=current_user, payload=payload)


@router.post(
    "/dispatch-due",
    response_model=ReminderDispatchSummary,
    summary="Deliver due reminders for the current user safely without duplicates",
)
async def dispatch_due_reminders(
    current_user: CurrentUserDep,
    service: ReminderServiceDep,
) -> ReminderDispatchSummary:
    return await service.dispatch_due_reminders(user_id=current_user.id)


@router.patch(
    "/{reminder_id}",
    response_model=ReminderResponse,
    summary="Reschedule or edit an active reminder",
)
async def update_reminder(
    reminder_id: uuid.UUID,
    payload: ReminderUpdateRequest,
    current_user: CurrentUserDep,
    service: ReminderServiceDep,
) -> ReminderResponse:
    return await service.update_reminder(
        user=current_user, reminder_id=reminder_id, payload=payload
    )


@router.post(
    "/{reminder_id}/cancel",
    response_model=ReminderResponse,
    summary="Cancel a scheduled or retry-queued reminder",
)
async def cancel_reminder(
    reminder_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: ReminderServiceDep,
) -> ReminderResponse:
    return await service.cancel_reminder(user=current_user, reminder_id=reminder_id)


@router.post(
    "/{reminder_id}/dismiss",
    response_model=ReminderResponse,
    summary="Dismiss a sent in-app notification reminder",
)
async def dismiss_reminder(
    reminder_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: ReminderServiceDep,
) -> ReminderResponse:
    return await service.dismiss_reminder(user=current_user, reminder_id=reminder_id)


@router.delete(
    "/{reminder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a reminder",
)
async def delete_reminder(
    reminder_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: ReminderServiceDep,
) -> None:
    await service.delete_reminder(user=current_user, reminder_id=reminder_id)
