"""Unit and API tests for Phase 6 Application Tracking, state machine, and isolation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi import FastAPI

from app.core.config import Settings
from app.core.exceptions import ValidationError
from app.integrations.job_search.openai_web_search import DiscoveredJobRecord, JobSearchQuery
from app.main import create_app
from app.modules.applications.state_machine import validate_status_transition
from app.modules.jobs.router import get_job_search_provider


class FakeJobProvider:
    def __init__(self, records: list[DiscoveredJobRecord]) -> None:
        self._records = records

    async def search_jobs(self, query: JobSearchQuery) -> list[DiscoveredJobRecord]:
        return list(self._records)


async def _login(client: httpx.AsyncClient, email: str, name: str) -> dict[str, str]:
    res = await client.post("/api/v1/auth/dev-login", json={"email": email, "full_name": name})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_state_machine_rejects_invalid_and_terminal_transitions() -> None:
    validate_status_transition(current_status="SAVED", target_status="PREPARING")
    validate_status_transition(current_status="PREPARING", target_status="AWAITING_APPROVAL")
    validate_status_transition(current_status="AWAITING_APPROVAL", target_status="SUBMITTED")
    validate_status_transition(current_status="SUBMITTED", target_status="INTERVIEW_SCHEDULED")
    validate_status_transition(
        current_status="INTERVIEW_SCHEDULED",
        target_status="OFFER_RECEIVED",
    )

    with pytest.raises(ValidationError, match="Invalid status transition"):
        validate_status_transition(current_status="SAVED", target_status="OFFER_RECEIVED")

    with pytest.raises(ValidationError, match="Invalid status transition"):
        validate_status_transition(current_status="SAVED", target_status="SUBMITTED")

    with pytest.raises(ValidationError, match="Invalid status transition"):
        validate_status_transition(current_status="REJECTED", target_status="SUBMITTED")

    with pytest.raises(ValidationError, match="already in status"):
        validate_status_transition(current_status="SAVED", target_status="SAVED")


async def test_application_crud_transitions_duplicate_prevention_and_isolation(
    migrated_test_app: FastAPI,
    test_settings: Settings,
) -> None:
    _ = migrated_test_app
    now = datetime.now(UTC)
    job_provider = FakeJobProvider(
        [
            DiscoveredJobRecord(
                source_provider="openai_web_search",
                title="Platform Engineer Intern",
                company="ScaleGrid",
                location="Remote",
                work_mode="remote",
                experience_level="intern",
                employment_type="internship",
                description="Python, FastAPI, PostgreSQL infrastructure.",
                requirements_summary=None,
                required_skills=["Python"],
                preferred_skills=[],
                education_requirements=[],
                min_years_experience=0.0,
                salary_range=None,
                external_url="https://careers.scalegrid.io/intern",
                source_domain="careers.scalegrid.io",
                posted_at=now,
                raw_metadata={},
            )
        ]
    )

    settings = test_settings.model_copy(update={"dev_auth_enabled": True})
    app = create_app(settings=settings)
    app.dependency_overrides[get_job_search_provider] = lambda: job_provider

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            headers_a = await _login(client, "app_a@edu.org", "Student A")
            headers_b = await _login(client, "app_b@edu.org", "Student B")

            job_id = (
                await client.get("/api/v1/jobs/search?q=Platform", headers=headers_a)
            ).json()["items"][0]["id"]

            # Manual application missing required fields fails
            bad_manual = await client.post(
                "/api/v1/applications",
                headers=headers_a,
                json={"notes": "Missing company and role"},
            )
            assert bad_manual.status_code == 422

            # Create application linked to discovered job
            deadline = (now + timedelta(days=5)).isoformat()
            create_res = await client.post(
                "/api/v1/applications",
                headers=headers_a,
                json={
                    "job_id": job_id,
                    "deadline_at": deadline,
                    "notes": "Tailor backend resume first",
                },
            )
            assert create_res.status_code == 201
            created = create_res.json()
            app_id = created["id"]
            assert created["status"] == "SAVED"
            assert created["company_name"] == "ScaleGrid"
            assert "PREPARING" in created["allowed_next_statuses"]
            assert len(created["history"]) == 1

            # Duplicate application for same user and job rejected with 409 Conflict
            dup_res = await client.post(
                "/api/v1/applications",
                headers=headers_a,
                json={"job_id": job_id},
            )
            assert dup_res.status_code == 409

            # Another user CAN track the same job independently
            other_create = await client.post(
                "/api/v1/applications",
                headers=headers_b,
                json={"job_id": job_id},
            )
            assert other_create.status_code == 201

            # Cross-user ownership check: User B cannot view, update, transition, or delete A's
            b_get = await client.get(f"/api/v1/applications/{app_id}", headers=headers_b)
            assert b_get.status_code == 404
            assert (
                await client.post(
                    f"/api/v1/applications/{app_id}/transition",
                    headers=headers_b,
                    json={"target_status": "PREPARING"},
                )
            ).status_code == 404
            assert (
                await client.delete(f"/api/v1/applications/{app_id}", headers=headers_b)
            ).status_code == 404

            # Invalid skip transition SAVED -> SUBMITTED blocked
            bad_skip = await client.post(
                f"/api/v1/applications/{app_id}/transition",
                headers=headers_a,
                json={"target_status": "SUBMITTED"},
            )
            assert bad_skip.status_code == 422

            # Valid state transitions through SUBMITTED
            for nxt in ("PREPARING", "AWAITING_APPROVAL", "SUBMITTED"):
                t_res = await client.post(
                    f"/api/v1/applications/{app_id}/transition",
                    headers=headers_a,
                    json={"target_status": nxt, "note": f"Moved to {nxt}"},
                )
                assert t_res.status_code == 200
                assert t_res.json()["status"] == nxt

            detail = (await client.get(f"/api/v1/applications/{app_id}", headers=headers_a)).json()
            assert detail["applied_at"] is not None
            assert len(detail["history"]) == 4

            # Patch notes and verify summary
            patch_res = await client.patch(
                f"/api/v1/applications/{app_id}",
                headers=headers_a,
                json={"notes": "Followed up with recruiter"},
            )
            assert patch_res.status_code == 200
            assert patch_res.json()["notes"] == "Followed up with recruiter"

            summary_res = await client.get("/api/v1/applications/summary", headers=headers_a)
            assert summary_res.status_code == 200
            summary = summary_res.json()
            assert summary["total_applications"] == 1
            assert summary["counts_by_status"]["SUBMITTED"] == 1
            assert len(summary["upcoming_deadlines"]) == 1

            # Delete application
            del_res = await client.delete(f"/api/v1/applications/{app_id}", headers=headers_a)
            assert del_res.status_code == 204
            after_del = await client.get(f"/api/v1/applications/{app_id}", headers=headers_a)
            assert after_del.status_code == 404
