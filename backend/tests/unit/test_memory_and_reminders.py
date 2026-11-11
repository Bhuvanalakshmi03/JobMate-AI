"""Tests for Phase 9 Career Memory, Reminders, Deduplication, Retries, and Account Lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
from fastapi import FastAPI

from app.core.config import Settings
from app.core.dependencies import DBSessionDep
from app.main import create_app
from app.modules.reminders.models import Reminder
from app.modules.reminders.router import get_reminder_service
from app.modules.reminders.service import ReminderService


class FlakyDispatcher:
    """Dispatcher failing once before succeeding on retry."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.fail_once = True

    async def deliver(self, *, reminder: Reminder) -> None:
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("Transient notification delivery error")
        self.calls.append(str(reminder.id))


async def test_memory_consent_reminders_dedup_retry_and_account_lifecycle(
    migrated_test_app: FastAPI,
    test_settings: Settings,
) -> None:
    _ = migrated_test_app
    app_settings = test_settings.model_copy(update={"dev_auth_enabled": True})
    app = create_app(app_settings)

    flaky = FlakyDispatcher()

    def _override_reminder_service(session: DBSessionDep) -> ReminderService:
        return ReminderService(session=session, dispatcher=flaky)

    app.dependency_overrides[get_reminder_service] = _override_reminder_service

    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        login_a = await client.post(
            "/api/v1/auth/dev-login",
            json={
                "email": "mem_user_a@jobmate.local",
                "full_name": "Memory User",
                "timezone": "Asia/Kolkata",
            },
        )
        headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}

        login_b = await client.post(
            "/api/v1/auth/dev-login",
            json={"email": "mem_user_b@jobmate.local", "full_name": "Other User"},
        )
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        # 1. Career Memory blocked until explicit consent is granted
        blocked = await client.post(
            "/api/v1/memory",
            headers=headers_a,
            json={
                "category": "preference",
                "title": "Preferred Work Mode",
                "content": "Prefer hybrid backend engineering roles in Chennai.",
                "memory_key": "work_mode_pref",
            },
        )
        assert blocked.status_code == 422

        consent_res = await client.patch(
            "/api/v1/memory/consent",
            headers=headers_a,
            json={"ai_consent_given": True, "notification_consent": True},
        )
        assert consent_res.status_code == 200
        assert consent_res.json()["ai_consent_given"] is True

        # Save + upsert via memory_key (no duplicates!)
        mem1 = await client.post(
            "/api/v1/memory",
            headers=headers_a,
            json={
                "category": "preference",
                "title": "Preferred Work Mode",
                "content": "Prefer hybrid backend roles.",
                "memory_key": "work_mode_pref",
            },
        )
        assert mem1.status_code == 201
        mem_id = mem1.json()["id"]

        mem1_upd = await client.post(
            "/api/v1/memory",
            headers=headers_a,
            json={
                "category": "preference",
                "title": "Preferred Work Mode",
                "content": "Prefer hybrid Python/FastAPI backend roles in Chennai.",
                "memory_key": "work_mode_pref",
            },
        )
        assert mem1_upd.status_code == 201
        assert mem1_upd.json()["id"] == mem_id

        mem_list = await client.get("/api/v1/memory", headers=headers_a)
        assert mem_list.status_code == 200
        assert mem_list.json()["total"] == 1

        # Cross-user memory isolation
        assert (
            await client.patch(
                f"/api/v1/memory/{mem_id}",
                headers=headers_b,
                json={"title": "Hacked"},
            )
        ).status_code == 404

        # 2. Timezone-aware reminder scheduling + deduplication
        past_due_ist = (datetime.now(UTC) + timedelta(hours=5, minutes=20)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        r1 = await client.post(
            "/api/v1/reminders",
            headers=headers_a,
            json={
                "title": "Follow up with Freshworks Recruiter",
                "reminder_type": "follow_up",
                "dedup_key": "followup-freshworks-1",
                "scheduled_for": past_due_ist,
                "timezone": "Asia/Kolkata",
            },
        )
        assert r1.status_code == 201
        rem_id = r1.json()["id"]
        assert r1.json()["user_timezone"] == "Asia/Kolkata"

        # Submitting same dedup_key returns existing row without creating duplicate
        r1_dup = await client.post(
            "/api/v1/reminders",
            headers=headers_a,
            json={
                "title": "Duplicate attempt",
                "reminder_type": "follow_up",
                "dedup_key": "followup-freshworks-1",
                "scheduled_for": past_due_ist,
                "timezone": "Asia/Kolkata",
            },
        )
        assert r1_dup.status_code == 201
        assert r1_dup.json()["id"] == rem_id

        # Cross-user reminder isolation
        assert (
            await client.post(f"/api/v1/reminders/{rem_id}/cancel", headers=headers_b)
        ).status_code == 404

        # 3. Retry & idempotent notification dispatch
        r_cancel = await client.post(
            "/api/v1/reminders",
            headers=headers_a,
            json={
                "title": "Cancel Me Reminder",
                "reminder_type": "custom",
                "scheduled_for": (datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
            },
        )
        cancel_id = r_cancel.json()["id"]
        await client.post(f"/api/v1/reminders/{cancel_id}/cancel", headers=headers_a)

        # Dispatch once -> flaky fails first, schedules retry
        d1 = await client.post("/api/v1/reminders/dispatch-due", headers=headers_a)
        assert d1.status_code == 200
        assert d1.json()["failed"] == 1
        assert d1.json()["retried_scheduled"] == 1
        assert len(flaky.calls) == 0

        # Trigger due delivery directly at +10 min via service (simulating worker backoff tick)
        async with app.state.db_session_factory() as db:
            svc = ReminderService(session=db, dispatcher=flaky)
            d2 = await svc.dispatch_due_reminders(now_utc=datetime.now(UTC) + timedelta(minutes=10))
            await db.commit()
            assert d2.sent == 1
            assert len(flaky.calls) == 1

            # Second dispatch sweep must NOT duplicate already SENT reminder or CANCELLED one
            d3 = await svc.dispatch_due_reminders(now_utc=datetime.now(UTC) + timedelta(minutes=20))
            assert d3.processed == 0
            assert len(flaky.calls) == 1

        # 4. Account export & permanent cascading account deletion
        export_res = await client.get("/api/v1/auth/export", headers=headers_a)
        assert export_res.status_code == 200
        exp = export_res.json()
        assert exp["account"]["email"] == "mem_user_a@jobmate.local"
        assert len(exp["career_memory"]) == 1
        assert len(exp["reminders"]) == 2

        del_acc = await client.delete("/api/v1/auth/account", headers=headers_a)
        assert del_acc.status_code == 204
        assert (await client.get("/api/v1/auth/me", headers=headers_a)).status_code == 401
