"""Unit and API tests for OpenAI Web Search job discovery, deduplication, and matching APIs."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx
import pytest
from fastapi import FastAPI

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError
from app.integrations.job_search.openai_web_search import (
    DiscoveredJobRecord,
    JobSearchQuery,
    OpenAIWebSearchJobProvider,
)
from app.integrations.openai.client import LLMCompletionResult
from app.main import create_app
from app.modules.jobs.router import get_embedding_client, get_job_search_provider


class FakeWebSearchLLM:
    def __init__(self, payload_json: str) -> None:
        self._payload_json = payload_json

    async def web_search_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int | None = None,
    ) -> LLMCompletionResult:
        return LLMCompletionResult(
            content=self._payload_json,
            model="gpt-4o-mini-web",
            prompt_tokens=50,
            completion_tokens=100,
            total_tokens=150,
            citations=("https://careers.acme-tech.io/jobs/101",),
        )


class FakeJobSearchProvider:
    def __init__(self, records: list[DiscoveredJobRecord]) -> None:
        self.records = records
        self.calls = 0

    async def search_jobs(self, query: JobSearchQuery) -> list[DiscoveredJobRecord]:
        self.calls += 1
        return list(self.records)


class FakeEmbeddingClient:
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            lowered = text.lower()
            vectors.append(
                [
                    1.0 if "python" in lowered else 0.1,
                    1.0 if "fastapi" in lowered else 0.1,
                    1.0 if "backend" in lowered else 0.2,
                ]
            )
        return vectors


async def _login(client: httpx.AsyncClient, email: str, name: str) -> dict[str, str]:
    res = await client.post("/api/v1/auth/dev-login", json={"email": email, "full_name": name})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def test_openai_web_search_provider_filters_placeholder_urls_and_malformed_json() -> None:
    provider = OpenAIWebSearchJobProvider(
        FakeWebSearchLLM(
            json.dumps(
                {
                    "jobs": [
                        {
                            "title": "Fake Placeholder Job",
                            "company": "FakeCo",
                            "external_url": "https://example.com/jobs/1",
                            "description": "Placeholder should be dropped",
                        },
                        {
                            "title": "Backend Engineer Intern",
                            "company": "Acme Tech",
                            "location": "Remote",
                            "work_mode": "remote",
                            "experience_level": "intern",
                            "employment_type": "internship",
                            "description": "Build FastAPI services with Python and PostgreSQL.",
                            "required_skills": ["Python", "FastAPI"],
                            "external_url": "https://careers.acme-tech.io/jobs/101",
                            "posted_at": "2026-11-10",
                        },
                    ]
                }
            )
        )
    )

    jobs = await provider.search_jobs(JobSearchQuery(query="Backend Engineer Intern"))
    assert len(jobs) == 1
    assert jobs[0].source_domain == "careers.acme-tech.io"
    assert jobs[0].work_mode == "remote"

    bad_provider = OpenAIWebSearchJobProvider(FakeWebSearchLLM("{bad-json"))
    with pytest.raises(ExternalServiceError, match="malformed"):
        await bad_provider.search_jobs(JobSearchQuery(query="Backend"))


async def test_job_discovery_deduplication_matching_saving_and_isolation(
    migrated_test_app: FastAPI,
    test_settings: Settings,
) -> None:
    _ = migrated_test_app
    now = datetime.now(UTC)
    sample_records = [
        DiscoveredJobRecord(
            source_provider="openai_web_search",
            title="Backend Software Engineer",
            company="CloudScale Labs",
            location="Bengaluru, India",
            work_mode="hybrid",
            experience_level="entry_level",
            employment_type="full_time",
            description="Python, FastAPI, PostgreSQL, Docker backend APIs.",
            requirements_summary="1+ year Python/FastAPI",
            required_skills=["Python", "FastAPI", "PostgreSQL"],
            preferred_skills=["Docker"],
            education_requirements=["B.Tech Computer Science"],
            min_years_experience=0.0,
            salary_range=None,
            external_url="https://jobs.cloudscale.io/backend-1?utm_source=web",
            source_domain="jobs.cloudscale.io",
            posted_at=now,
            raw_metadata={"citations": ["https://jobs.cloudscale.io/backend-1"]},
        ),
        # Duplicate canonical URL with different tracking param -> must deduplicate!
        DiscoveredJobRecord(
            source_provider="openai_web_search",
            title="Backend Software Engineer",
            company="CloudScale Labs",
            location="Bengaluru, India",
            work_mode="hybrid",
            experience_level="entry_level",
            employment_type="full_time",
            description="Python, FastAPI, PostgreSQL, Docker backend APIs.",
            requirements_summary="1+ year Python/FastAPI",
            required_skills=["Python", "FastAPI", "PostgreSQL"],
            preferred_skills=["Docker"],
            education_requirements=["B.Tech Computer Science"],
            min_years_experience=0.0,
            salary_range=None,
            external_url="https://jobs.cloudscale.io/backend-1?utm_source=search2",
            source_domain="jobs.cloudscale.io",
            posted_at=now,
            raw_metadata={},
        ),
        DiscoveredJobRecord(
            source_provider="openai_web_search",
            title="Senior iOS Graphics Engineer",
            company="MobileCraft",
            location="San Jose, CA",
            work_mode="onsite",
            experience_level="senior",
            employment_type="full_time",
            description="Swift, Metal, Objective-C graphics pipeline.",
            requirements_summary="6+ years iOS",
            required_skills=["Swift", "Metal", "Objective-C"],
            preferred_skills=[],
            education_requirements=["BS Computer Science"],
            min_years_experience=6.0,
            salary_range=None,
            external_url="https://careers.mobilecraft.io/ios-senior",
            source_domain="careers.mobilecraft.io",
            posted_at=now,
            raw_metadata={},
        ),
    ]

    fake_provider = FakeJobSearchProvider(sample_records)
    settings = test_settings.model_copy(update={"dev_auth_enabled": True})
    app = create_app(settings=settings)
    app.dependency_overrides[get_job_search_provider] = lambda: fake_provider
    app.dependency_overrides[get_embedding_client] = lambda: FakeEmbeddingClient()

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            headers_a = await _login(client, "cand_a@edu.org", "Candidate A")
            headers_b = await _login(client, "cand_b@edu.org", "Candidate B")

            # Candidate A sets profile and skills
            await client.post(
                "/api/v1/profile",
                headers=headers_a,
                json={
                    "headline": "Backend Engineer",
                    "degree": "B.Tech CS",
                    "experience_level": "entry_level",
                    "target_roles": ["Backend Software Engineer"],
                    "preferred_locations": ["Bengaluru"],
                    "work_mode_preferences": ["hybrid", "remote"],
                },
            )
            await client.put(
                "/api/v1/profile/skills",
                headers=headers_a,
                json={
                    "skills": [
                        {"name": "Python", "category": "language"},
                        {"name": "FastAPI", "category": "framework"},
                        {"name": "PostgreSQL", "category": "technical"},
                    ]
                },
            )

            # Search triggers web search provider and deduplicates identical URL
            search_res = await client.get(
                "/api/v1/jobs/search?q=Backend%20Engineer",
                headers=headers_a,
            )
            assert search_res.status_code == 200
            search_data = search_res.json()
            assert search_data["source"] == "openai_web_search"
            assert search_data["total"] == 2  # 3 raw items deduplicated to 2!
            backend_job = next(
                item for item in search_data["items"] if item["company"] == "CloudScale Labs"
            )
            ios_job = next(
                item for item in search_data["items"] if item["company"] == "MobileCraft"
            )

            # Compute match score for backend job
            match_res = await client.post(
                f"/api/v1/jobs/{backend_job['id']}/match",
                headers=headers_a,
            )
            assert match_res.status_code == 200
            match_data = match_res.json()
            assert match_data["overall_score"] >= 75.0
            assert "Python" in match_data["matching_skills"]
            assert match_data["missing_skills"] == []

            # Recommended ranks Backend Engineer ahead of Senior iOS Engineer
            rec_res = await client.get("/api/v1/jobs/recommended", headers=headers_a)
            assert rec_res.status_code == 200
            rec_items = rec_res.json()["items"]
            assert rec_items[0]["job"]["id"] == backend_job["id"]
            assert rec_items[0]["match"]["overall_score"] > rec_items[1]["match"]["overall_score"]
            assert rec_items[1]["job"]["id"] == ios_job["id"]

            # Save job and check cross-user isolation
            save_res = await client.post(
                f"/api/v1/jobs/{backend_job['id']}/save",
                headers=headers_a,
                json={"notes": "Great fit"},
            )
            assert save_res.status_code == 200
            assert save_res.json()["is_saved"] is True

            saved_a = await client.get("/api/v1/jobs/saved", headers=headers_a)
            assert saved_a.json()["total"] == 1

            saved_b = await client.get("/api/v1/jobs/saved", headers=headers_b)
            assert saved_b.json()["total"] == 0

            detail_a = await client.get(f"/api/v1/jobs/{backend_job['id']}", headers=headers_a)
            assert detail_a.status_code == 200
            assert detail_a.json()["is_saved"] is True
            assert detail_a.json()["match_preview"] is not None

            del_save = await client.delete(
                f"/api/v1/jobs/{backend_job['id']}/save",
                headers=headers_a,
            )
            assert del_save.status_code == 204
