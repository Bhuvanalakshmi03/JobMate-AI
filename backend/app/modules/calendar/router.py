"""Google Calendar API v1 routes (/api/v1/calendar/*)."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import RedirectResponse

from app.core.dependencies import DBSessionDep, SettingsDep
from app.modules.authentication.dependencies import CurrentUserDep
from app.modules.authentication.schemas import AuthUrlResponse
from app.modules.calendar.schemas import (
    CalendarEventCreateRequest,
    CalendarEventItem,
    CalendarEventsResponse,
    CalendarStatusResponse,
)
from app.modules.calendar.service import CalendarService

router = APIRouter(prefix="/calendar", tags=["Google Calendar"])


def get_calendar_service(
    session: DBSessionDep,
    settings: SettingsDep,
) -> CalendarService:
    return CalendarService(session=session, settings=settings)


CalendarServiceDep = Annotated[CalendarService, Depends(get_calendar_service)]


@router.get(
    "/status",
    response_model=CalendarStatusResponse,
    summary="Check whether Google Calendar is connected for the current user",
)
async def get_calendar_status(
    current_user: CurrentUserDep,
    service: CalendarServiceDep,
) -> CalendarStatusResponse:
    return await service.get_status(user_id=current_user.id)


@router.get(
    "/connect",
    response_model=AuthUrlResponse,
    summary="Generate Google OAuth authorization URL with Google Calendar access",
)
async def connect_google_calendar(
    current_user: CurrentUserDep,
    service: CalendarServiceDep,
    mode: Literal["json", "redirect"] = Query(default="json"),
    redirect_to: str = Query(default="/copilot"),
) -> Response | AuthUrlResponse:
    auth_url = await service.initiate_connect(user=current_user, redirect_to=redirect_to)
    if mode == "redirect":
        return RedirectResponse(url=auth_url.authorization_url, status_code=status.HTTP_302_FOUND)
    return auth_url


@router.get(
    "/events",
    response_model=CalendarEventsResponse,
    summary="List upcoming events from connected Google Calendar",
)
async def list_calendar_events(
    current_user: CurrentUserDep,
    service: CalendarServiceDep,
    days_ahead: Annotated[int, Query(ge=1, le=90)] = 7,
    max_results: Annotated[int, Query(ge=1, le=100)] = 50,
) -> CalendarEventsResponse:
    return await service.list_upcoming_events(
        user_id=current_user.id,
        days_ahead=days_ahead,
        max_results=max_results,
    )


@router.post(
    "/events",
    response_model=CalendarEventItem,
    status_code=status.HTTP_201_CREATED,
    summary="Create an event in connected Google Calendar",
)
async def create_calendar_event(
    payload: CalendarEventCreateRequest,
    current_user: CurrentUserDep,
    service: CalendarServiceDep,
) -> CalendarEventItem:
    return await service.create_event(user=current_user, payload=payload)


@router.delete(
    "/disconnect",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect stored Google Calendar OAuth tokens",
)
async def disconnect_google_calendar(
    current_user: CurrentUserDep,
    service: CalendarServiceDep,
) -> None:
    await service.disconnect(user_id=current_user.id)

