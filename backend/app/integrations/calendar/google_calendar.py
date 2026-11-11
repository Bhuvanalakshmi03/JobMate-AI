"""Async Google Calendar REST v3 client adapter with mocked-transport testability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.core.exceptions import AuthenticationError, ExternalServiceError

GOOGLE_CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
GOOGLE_CALENDAR_EVENTS_SCOPE = "https://www.googleapis.com/auth/calendar.events"


@dataclass(frozen=True, slots=True)
class CalendarEventRecord:
    """Normalized Google Calendar event metadata."""

    event_id: str
    summary: str
    start_iso: str
    end_iso: str
    location: str | None = None
    description: str | None = None
    html_link: str | None = None
    status: str = "confirmed"


class CalendarProviderProtocol(Protocol):
    """Protocol decoupling CareerPilot calendar actions from HTTP transport."""

    async def list_events(
        self,
        *,
        access_token: str,
        time_min_iso: str,
        time_max_iso: str | None = None,
        max_results: int = 15,
    ) -> list[CalendarEventRecord]: ...

    async def create_event(
        self,
        *,
        access_token: str,
        summary: str,
        start_iso: str,
        end_iso: str,
        description: str | None = None,
        location: str | None = None,
        timezone: str = "UTC",
    ) -> CalendarEventRecord: ...

    async def delete_event(self, *, access_token: str, event_id: str) -> None: ...


def _parse_event(raw: dict[str, Any]) -> CalendarEventRecord:
    start_obj = raw.get("start") or {}
    end_obj = raw.get("end") or {}
    start_iso = str(start_obj.get("dateTime") or start_obj.get("date") or "")
    end_iso = str(end_obj.get("dateTime") or end_obj.get("date") or "")
    return CalendarEventRecord(
        event_id=str(raw.get("id") or ""),
        summary=str(raw.get("summary") or "Untitled event"),
        start_iso=start_iso,
        end_iso=end_iso,
        location=str(raw["location"]) if raw.get("location") else None,
        description=str(raw["description"]) if raw.get("description") else None,
        html_link=str(raw["htmlLink"]) if raw.get("htmlLink") else None,
        status=str(raw.get("status") or "confirmed"),
    )


class GoogleCalendarClient:
    """Async Google Calendar API v3 client using OAuth bearer access tokens."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 15.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._transport = transport

    def _client(self, access_token: str) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=GOOGLE_CALENDAR_API_BASE,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=self._timeout,
            transport=self._transport,
        )

    @staticmethod
    def _raise_for_error(response: httpx.Response, *, action: str) -> None:
        if response.status_code in (401, 403):
            detail = ""
            try:
                err_obj = response.json().get("error", {})
                detail = str(err_obj.get("message") or "").strip()
            except Exception:
                detail = ""
            msg = (
                "Google Calendar permission missing or expired. Reconnect Google Calendar "
                "and grant calendar event access."
            )
            if detail:
                msg = f"{msg} ({detail[:180]})"
            raise AuthenticationError(msg)
        if response.status_code >= 400:
            raise ExternalServiceError(
                f"Google Calendar failed during {action} (status {response.status_code})."
            )

    async def list_events(
        self,
        *,
        access_token: str,
        time_min_iso: str,
        time_max_iso: str | None = None,
        max_results: int = 15,
    ) -> list[CalendarEventRecord]:
        params: dict[str, str] = {
            "singleEvents": "true",
            "orderBy": "startTime",
            "timeMin": time_min_iso,
            "maxResults": str(max(1, min(max_results, 50))),
        }
        if time_max_iso:
            params["timeMax"] = time_max_iso

        try:
            async with self._client(access_token) as client:
                response = await client.get("/calendars/primary/events", params=params)
        except httpx.HTTPError as exc:
            raise ExternalServiceError("Failed to contact Google Calendar API.") from exc

        self._raise_for_error(response, action="list events")
        items = response.json().get("items") or []
        return [_parse_event(item) for item in items if isinstance(item, dict)]

    async def create_event(
        self,
        *,
        access_token: str,
        summary: str,
        start_iso: str,
        end_iso: str,
        description: str | None = None,
        location: str | None = None,
        timezone: str = "UTC",
    ) -> CalendarEventRecord:
        body: dict[str, Any] = {
            "summary": summary.strip()[:250],
            "start": {"dateTime": start_iso, "timeZone": timezone},
            "end": {"dateTime": end_iso, "timeZone": timezone},
        }
        if description:
            body["description"] = description.strip()[:4000]
        if location:
            body["location"] = location.strip()[:500]

        try:
            async with self._client(access_token) as client:
                response = await client.post("/calendars/primary/events", json=body)
        except httpx.HTTPError as exc:
            raise ExternalServiceError("Failed to create event in Google Calendar.") from exc

        self._raise_for_error(response, action="create event")
        return _parse_event(response.json())

    async def delete_event(self, *, access_token: str, event_id: str) -> None:
        try:
            async with self._client(access_token) as client:
                response = await client.delete(f"/calendars/primary/events/{event_id}")
        except httpx.HTTPError as exc:
            raise ExternalServiceError("Failed to delete event in Google Calendar.") from exc

        if response.status_code == 404:
            return
        self._raise_for_error(response, action="delete event")
