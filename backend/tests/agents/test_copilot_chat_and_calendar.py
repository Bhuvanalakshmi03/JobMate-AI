"""Tests for Google Calendar integration, OAuth connect flow, and Co-Pilot chat tools."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.core.config import Settings
from app.core.dependencies import DBSessionDep
from app.core.exceptions import AuthenticationError
from app.core.security import decrypt_secret, encrypt_secret
from app.integrations.calendar.google_calendar import CalendarEventRecord, GoogleCalendarClient
from app.integrations.chroma.store import InMemoryVectorStore
from app.integrations.job_search.openai_web_search import DiscoveredJobRecord, JobSearchQuery
from app.integrations.oauth.google import OAuthIdentity
from app.integrations.openai.client import (
    LLMCompletionResult,
    ToolCallingResult,
)
from app.main import create_app
from app.modules.approvals.router import get_approval_service
from app.modules.approvals.service import ApprovalService
from app.modules.authentication.dependencies import get_oauth_provider
from app.modules.calendar.router import get_calendar_service
from app.modules.calendar.service import CalendarService
from app.modules.copilot.router import get_copilot_chat_service
from app.modules.copilot.service import CopilotChatService
from app.modules.documents.generator import (
    GeneratedDocumentDraft,
    JobTargetContext,
    VerifiedCandidateContext,
)


class FakeCalendarProvider:
    def __init__(self) -> None:
        self.created_events: list[CalendarEventRecord] = []

    async def list_events(
        self,
        *,
        access_token: str,
        time_min_iso: str,
        time_max_iso: str | None = None,
        max_results: int = 50,
    ) -> list[CalendarEventRecord]:
        _ = (access_token, time_min_iso, time_max_iso, max_results)
        now = datetime.now(UTC)
        in_window_start = (now + timedelta(days=1)).isoformat()
        in_window_end = (now + timedelta(days=1, hours=1)).isoformat()
        out_of_window_future = (now + timedelta(days=10)).isoformat()
        out_of_window_future_end = (now + timedelta(days=10, hours=1)).isoformat()
        out_of_window_past = (now - timedelta(days=2)).isoformat()
        out_of_window_past_end = (now - timedelta(days=2) + timedelta(hours=1)).isoformat()
        return [
            CalendarEventRecord(
                event_id="evt-past-ignored",
                summary="Past Interview",
                start_iso=out_of_window_past,
                end_iso=out_of_window_past_end,
            ),
            CalendarEventRecord(
                event_id="evt-existing-1",
                summary="Mock Technical Screen",
                start_iso=in_window_start,
                end_iso=in_window_end,
                location="Google Meet",
                html_link="https://calendar.google.com/event?eid=existing1",
            ),
            CalendarEventRecord(
                event_id="evt-future-ignored",
                summary="Two Weeks Out Sync",
                start_iso=out_of_window_future,
                end_iso=out_of_window_future_end,
            ),
            *self.created_events,
        ]

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
        _ = (access_token, timezone)
        record = CalendarEventRecord(
            event_id=f"evt-created-{len(self.created_events) + 1}",
            summary=summary,
            start_iso=start_iso,
            end_iso=end_iso,
            location=location,
            description=description,
            html_link="https://calendar.google.com/event?eid=created1",
        )
        self.created_events.append(record)
        return record

    async def delete_event(self, *, access_token: str, event_id: str) -> None:
        _ = (access_token, event_id)


class FakeCalendarOAuth:
    def build_authorization_url(
        self,
        *,
        state: str,
        nonce: str,
        code_challenge: str,
        extra_scopes: tuple[str, ...] = (),
        prompt_override: str | None = None,
    ) -> str:
        scope_str = "+".join(["openid", "email", "profile", *extra_scopes])
        return (
            f"https://accounts.google.com/o/oauth2/v2/auth?state={state}"
            f"&nonce={nonce}&code_challenge={code_challenge}"
            f"&scope={scope_str}&prompt={prompt_override or 'select_account'}"
        )

    async def exchange_and_verify(
        self,
        *,
        code: str,
        code_verifier: str,
        expected_nonce: str,
    ) -> OAuthIdentity:
        _ = (code, code_verifier, expected_nonce)
        return OAuthIdentity(
            provider="google",
            subject="google-cal-sub-1",
            email="cal_user@edu.org",
            email_verified=True,
            full_name="Calendar User",
            avatar_url=None,
            access_token="ya29.fake-access-token",
            refresh_token="1//fake-refresh-token",
            expires_in=3600,
            scope="openid email profile https://www.googleapis.com/auth/calendar.events",
        )

    async def refresh_access_token(self, *, refresh_token: str) -> tuple[str, int]:
        _ = refresh_token
        return "ya29.refreshed-access-token", 3600


class FakeToolCallingClient:
    def __init__(self) -> None:
        self.turn_count = 0

    async def complete_with_tools(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_executor: Callable[[str, dict[str, Any]], Awaitable[str]],
        max_rounds: int = 6,
        max_tokens: int | None = None,
    ) -> ToolCallingResult:
        _ = (tools, max_rounds, max_tokens)
        self.turn_count += 1
        last_user = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        executed: list[dict[str, Any]] = []

        if "calendar" in last_user.lower():
            profile_out = await tool_executor("get_profile_and_skills", {})
            executed.append(
                {
                    "tool_name": "get_profile_and_skills",
                    "arguments": {},
                    "status": "completed",
                    "result_preview": profile_out[:120],
                }
            )
            cal_args = {
                "summary": "Backend System Design Prep",
                "start_iso": "2026-11-13T10:00:00+05:30",
                "end_iso": "2026-11-13T11:00:00+05:30",
                "description": "Review FastAPI & PostgreSQL scalability",
            }
            cal_out = await tool_executor("propose_calendar_event", cal_args)
            executed.append(
                {
                    "tool_name": "propose_calendar_event",
                    "arguments": cal_args,
                    "status": "completed",
                    "result_preview": cal_out[:120],
                }
            )
            reply = "I prepared your calendar event. Confirm it using the approval card below."
        else:
            apps_out = await tool_executor(
                "create_or_update_application",
                {
                    "company_name": "Stripe",
                    "role_title": "Backend Intern",
                    "notes": "Tracked from Co-Pilot Chat",
                },
            )
            executed.append(
                {
                    "tool_name": "create_or_update_application",
                    "arguments": {"company_name": "Stripe", "role_title": "Backend Intern"},
                    "status": "completed",
                    "result_preview": apps_out[:120],
                }
            )
            reply = "Added Stripe — Backend Intern to your Application Tracker."

        return ToolCallingResult(
            content=reply,
            model="gpt-4o-mini-test",
            prompt_tokens=60,
            completion_tokens=40,
            total_tokens=100,
            executed_tools=tuple(executed),
        )


class DummyEmbeddingClient:
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.5, 0.5, 0.5] for _ in texts]


class DummyJobProvider:
    async def search_jobs(self, query: JobSearchQuery) -> list[DiscoveredJobRecord]:
        _ = query
        return []


class DummyDocGenerator:
    async def generate_tailored_resume(
        self,
        *,
        candidate: VerifiedCandidateContext,
        job: JobTargetContext,
        focus_instructions: str | None = None,
    ) -> GeneratedDocumentDraft:
        _ = (candidate, job, focus_instructions)
        return GeneratedDocumentDraft(raw_json="{}", model="test", total_tokens=10)

    async def generate_cover_letter(
        self,
        *,
        candidate: VerifiedCandidateContext,
        job: JobTargetContext,
        tone: str = "professional",
        custom_notes: str | None = None,
    ) -> GeneratedDocumentDraft:
        _ = (candidate, job, tone, custom_notes)
        return GeneratedDocumentDraft(raw_json="{}", model="test", total_tokens=10)

    async def generate_application_note(
        self,
        *,
        candidate: VerifiedCandidateContext,
        job: JobTargetContext,
        max_words: int = 150,
    ) -> GeneratedDocumentDraft:
        _ = (candidate, job, max_words)
        return GeneratedDocumentDraft(raw_json="{}", model="test", total_tokens=10)

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float = 0.1,
    ) -> LLMCompletionResult:
        _ = (system_prompt, user_prompt, max_tokens, temperature)
        return LLMCompletionResult(
            content="{}", model="test", prompt_tokens=1, completion_tokens=1, total_tokens=2
        )


async def _login(client: httpx.AsyncClient, email: str, name: str) -> dict[str, str]:
    res = await client.post("/api/v1/auth/dev-login", json={"email": email, "full_name": name})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_secret_encryption_roundtrip_and_tamper_detection() -> None:
    secret = "super-secret-app-key-for-unit-tests-123"
    token = encrypt_secret("1//google-refresh-token", secret_key=secret)
    assert token != "1//google-refresh-token"
    assert decrypt_secret(token, secret_key=secret) == "1//google-refresh-token"

    with pytest.raises(AuthenticationError):
        decrypt_secret("tampered-" + token, secret_key=secret)
    with pytest.raises(AuthenticationError):
        decrypt_secret(token, secret_key="different-secret-key-000000000000")


async def test_google_calendar_client_http_adapter() -> None:
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer ya29.test"
        seen.append((request.method, request.url.path))
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "e1",
                            "summary": "Interview",
                            "start": {"dateTime": "2026-11-12T10:00:00Z"},
                            "end": {"dateTime": "2026-11-12T11:00:00Z"},
                            "htmlLink": "https://calendar.google.com/e1",
                        }
                    ]
                },
            )
        if request.method == "POST":
            return httpx.Response(
                200,
                json={
                    "id": "e2",
                    "summary": "Created Event",
                    "start": {"dateTime": "2026-11-13T10:00:00Z"},
                    "end": {"dateTime": "2026-11-13T11:00:00Z"},
                },
            )
        return httpx.Response(401, json={"error": {"message": "Invalid Credentials"}})

    client = GoogleCalendarClient(transport=httpx.MockTransport(handler))
    events = await client.list_events(
        access_token="ya29.test",
        time_min_iso="2026-11-11T00:00:00Z",
    )
    assert len(events) == 1
    assert events[0].event_id == "e1"

    created = await client.create_event(
        access_token="ya29.test",
        summary="Created Event",
        start_iso="2026-11-13T10:00:00Z",
        end_iso="2026-11-13T11:00:00Z",
    )
    assert created.event_id == "e2"

    with pytest.raises(AuthenticationError, match="permission missing"):
        await client.delete_event(access_token="ya29.test", event_id="e2")


async def test_calendar_oauth_copilot_chat_tool_calling_and_approval_execution(
    migrated_test_app: FastAPI,
    test_settings: Settings,
) -> None:
    _ = migrated_test_app
    fake_calendar_provider = FakeCalendarProvider()
    fake_oauth = FakeCalendarOAuth()
    fake_tool_client = FakeToolCallingClient()
    vector_store = InMemoryVectorStore()

    settings = test_settings.model_copy(
        update={
            "dev_auth_enabled": True,
            "google_client_id": "test-client-id",
            "google_client_secret": "test-client-secret",
        }
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_oauth_provider] = lambda: fake_oauth

    def _calendar_svc(session: DBSessionDep) -> CalendarService:
        return CalendarService(
            session=session,
            settings=settings,
            provider=fake_calendar_provider,
            oauth_client=fake_oauth,  # type: ignore[arg-type]
        )

    def _copilot_svc(session: DBSessionDep) -> CopilotChatService:
        return CopilotChatService(
            session=session,
            settings=settings,
            tool_client=fake_tool_client,
            embedding_client=DummyEmbeddingClient(),
            vector_store=vector_store,
            job_search_provider=DummyJobProvider(),
            document_generator=DummyDocGenerator(),
            calendar_service=_calendar_svc(session),
        )

    def _approval_svc(session: DBSessionDep) -> ApprovalService:
        return ApprovalService(
            session=session,
            settings=settings,
            calendar_service=_calendar_svc(session),
        )

    app.dependency_overrides[get_calendar_service] = _calendar_svc
    app.dependency_overrides[get_copilot_chat_service] = _copilot_svc
    app.dependency_overrides[get_approval_service] = _approval_svc

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            headers_a = await _login(client, "cal_user@edu.org", "Calendar User")
            headers_b = await _login(client, "other_user@edu.org", "Other User")

            # 1. Initially Calendar is not connected
            status_before = await client.get("/api/v1/calendar/status", headers=headers_a)
            assert status_before.status_code == 200
            assert status_before.json()["connected"] is False

            # 2. Initiate incremental Google Calendar OAuth connect & simulate callback
            connect_res = await client.get("/api/v1/calendar/connect", headers=headers_a)
            assert connect_res.status_code == 200
            state_val = connect_res.json()["state"]
            assert "calendar.events" in connect_res.json()["authorization_url"]

            cb_res = await client.get(
                f"/api/v1/auth/google/callback?code=auth-code-1&state={state_val}&mode=json"
            )
            assert cb_res.status_code == 200

            status_after = await client.get("/api/v1/calendar/status", headers=headers_a)
            assert status_after.json()["connected"] is True
            assert status_after.json()["google_email"] == "cal_user@edu.org"

            events_res = await client.get("/api/v1/calendar/events", headers=headers_a)
            assert events_res.status_code == 200
            items = events_res.json()["items"]
            assert len(items) == 1
            assert items[0]["event_id"] == "evt-existing-1"

            # 3. Create Co-Pilot chat session & send message invoking calendar tool
            conv_res = await client.post("/api/v1/copilot/conversations", headers=headers_a)
            assert conv_res.status_code == 201
            conv_id = conv_res.json()["id"]

            turn1 = await client.post(
                f"/api/v1/copilot/conversations/{conv_id}/messages",
                headers=headers_a,
                json={"message": "Add Backend System Design Prep to my Google Calendar tomorrow"},
            )
            assert turn1.status_code == 200
            t1_data = turn1.json()
            assert t1_data["conversation"]["title"].startswith("Add Backend System Design Prep")
            assert len(t1_data["assistant_message"]["tool_calls"]) == 2
            assert len(t1_data["created_approvals"]) == 1
            cal_approval_id = t1_data["created_approvals"][0]["id"]
            assert t1_data["created_approvals"][0]["action_type"] == "create_calendar_event"

            # Calendar event MUST NOT exist yet until user clicks Approve
            assert len(fake_calendar_provider.created_events) == 0

            # Approve -> executes GoogleCalendarClient.create_event and records html_link!
            approve_res = await client.post(
                f"/api/v1/approvals/{cal_approval_id}/approve",
                headers=headers_a,
                json={"note": "Schedule confirmed"},
            )
            assert approve_res.status_code == 200
            approved = approve_res.json()
            assert approved["status"] == "EXECUTED"
            assert approved["execution_result"]["mode"] == "google_calendar_api_v3"
            assert len(fake_calendar_provider.created_events) == 1

            # 4. Second turn in same session creates an application via tool call
            turn2 = await client.post(
                f"/api/v1/copilot/conversations/{conv_id}/messages",
                headers=headers_a,
                json={"message": "Track my application for Stripe Backend Intern"},
            )
            assert turn2.status_code == 200

            history_res = await client.get(
                f"/api/v1/copilot/conversations/{conv_id}", headers=headers_a
            )
            assert history_res.status_code == 200
            assert len(history_res.json()["messages"]) == 4

            # Cross-user isolation checks
            assert (
                await client.get(f"/api/v1/copilot/conversations/{conv_id}", headers=headers_b)
            ).status_code == 404
            assert (
                await client.get("/api/v1/calendar/status", headers=headers_b)
            ).json()["connected"] is False

            # Disconnect Google Calendar cleanly
            del_cal = await client.delete("/api/v1/calendar/disconnect", headers=headers_a)
            assert del_cal.status_code == 204
            assert (
                await client.get("/api/v1/calendar/status", headers=headers_a)
            ).json()["connected"] is False

            # Suppress unused import warning on uuid/timedelta if not needed directly
            _ = (uuid.uuid4(), datetime.now(UTC) + timedelta(days=1))
