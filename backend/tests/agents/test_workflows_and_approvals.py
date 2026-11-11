"""Tests for LangGraph workflows, failure recovery, human approval gating, and isolation."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.agents.policies import MAX_WORKFLOW_STEPS, enforce_workflow_budgets, run_with_retry_policy
from app.core.config import Settings
from app.core.dependencies import DBSessionDep
from app.core.exceptions import ExternalServiceError, ValidationError
from app.integrations.chroma.store import InMemoryVectorStore
from app.integrations.job_search.openai_web_search import DiscoveredJobRecord, JobSearchQuery
from app.integrations.openai.client import LLMCompletionResult
from app.main import create_app
from app.models.audit_log import AuditLog
from app.modules.agents.router import get_agent_service
from app.modules.agents.service import AgentOrchestrationService
from app.modules.documents.generator import (
    GeneratedDocumentDraft,
    JobTargetContext,
    VerifiedCandidateContext,
)
from app.modules.jobs.router import get_job_search_provider


class FakeLLMClient:
    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float = 0.1,
    ) -> LLMCompletionResult:
        _ = (max_tokens, temperature)
        if "Workflow Router" in system_prompt:
            payload = {"task_category": "career_advisory", "reason": "Career preparation query."}
        else:
            payload = {
                "summary": (
                    "Your Python and FastAPI skills align strongly with backend internships."
                ),
                "strengths": ["Python", "FastAPI"],
                "recommended_actions": ["Keep tailored resume concise."],
                "cited_sources": ["profile: Career Profile"],
            }
        return LLMCompletionResult(
            content=json.dumps(payload),
            model="gpt-4o-mini-test",
            prompt_tokens=40,
            completion_tokens=40,
            total_tokens=80,
        )


class FakeEmbeddingClient:
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.8, 0.2, 0.1] for _ in texts]


class FakeJobProvider:
    def __init__(self, records: list[DiscoveredJobRecord]) -> None:
        self._records = records

    async def search_jobs(self, query: JobSearchQuery) -> list[DiscoveredJobRecord]:
        return list(self._records)


class FakeDocGenerator:
    async def generate_tailored_resume(
        self,
        *,
        candidate: VerifiedCandidateContext,
        job: JobTargetContext,
        focus_instructions: str | None = None,
    ) -> GeneratedDocumentDraft:
        _ = (candidate, job, focus_instructions)
        return GeneratedDocumentDraft(
            raw_json=json.dumps(
                {
                    "summary": "Backend Engineering student experienced with Python and FastAPI.",
                    "selected_skills": ["Python", "FastAPI"],
                    "experience": [],
                    "projects": [],
                    "education": [],
                }
            ),
            model="gpt-4o-mini-test",
            total_tokens=120,
        )

    async def generate_cover_letter(
        self,
        *,
        candidate: VerifiedCandidateContext,
        job: JobTargetContext,
        tone: str = "professional",
        custom_notes: str | None = None,
    ) -> GeneratedDocumentDraft:
        _ = (candidate, job, tone, custom_notes)
        return GeneratedDocumentDraft(
            raw_json=json.dumps(
                {
                    "subject": "Application for Backend Intern",
                    "salutation": "Dear Hiring Team,",
                    "paragraphs": [
                        "I am excited to apply for Backend Intern at Orbit Systems.",
                        "I build REST services using Python and FastAPI.",
                    ],
                    "closing": "Sincerely,\nStudent A",
                }
            ),
            model="gpt-4o-mini-test",
            total_tokens=90,
        )

    async def generate_application_note(
        self,
        *,
        candidate: VerifiedCandidateContext,
        job: JobTargetContext,
        max_words: int = 150,
    ) -> GeneratedDocumentDraft:
        _ = (candidate, job, max_words)
        return GeneratedDocumentDraft(
            raw_json='{"note":"Hello"}', model="gpt-4o-mini-test", total_tokens=40
        )


async def _login(client: httpx.AsyncClient, email: str, name: str) -> dict[str, str]:
    res = await client.post("/api/v1/auth/dev-login", json={"email": email, "full_name": name})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def test_retry_recovery_and_budget_policies() -> None:
    calls = 0

    async def flaky_operation() -> str:
        nonlocal calls
        calls += 1
        if calls < 2:
            raise ExternalServiceError("Transient timeout")
        return "ok"

    result, attempts = await run_with_retry_policy(flaky_operation, base_delay_seconds=0.001)
    assert result == "ok"
    assert attempts == 2

    with pytest.raises(ValidationError, match="step limit exceeded"):
        enforce_workflow_budgets(
            step_count=MAX_WORKFLOW_STEPS,
            total_tokens_used=100,
            max_tokens=10000,
        )
    with pytest.raises(ValidationError, match="token budget exceeded"):
        enforce_workflow_budgets(step_count=1, total_tokens_used=5000, max_tokens=1000)


async def test_langgraph_workflow_pauses_resumes_on_approval_and_isolates_users(
    migrated_test_app: FastAPI,
    test_settings: Settings,
) -> None:
    _ = migrated_test_app
    now = datetime.now(UTC)
    vector_store = InMemoryVectorStore()
    job_provider = FakeJobProvider(
        [
            DiscoveredJobRecord(
                source_provider="openai_web_search",
                title="Backend Intern",
                company="Orbit Systems",
                location="Remote",
                work_mode="remote",
                experience_level="intern",
                employment_type="internship",
                description="Looking for Python and FastAPI developer.",
                requirements_summary=None,
                required_skills=["Python", "FastAPI"],
                preferred_skills=[],
                education_requirements=[],
                min_years_experience=0.0,
                salary_range=None,
                external_url="https://careers.orbitsystems.io/backend-intern",
                source_domain="careers.orbitsystems.io",
                posted_at=now,
                raw_metadata={},
            )
        ]
    )

    settings = test_settings.model_copy(
        update={
            "dev_auth_enabled": True,
            "openai_api_key": "sk-test-placeholder",
        }
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_job_search_provider] = lambda: job_provider

    def _fake_agent_service(session: DBSessionDep) -> AgentOrchestrationService:
        return AgentOrchestrationService(
            session=session,
            settings=settings,
            llm_client=FakeLLMClient(),
            embedding_client=FakeEmbeddingClient(),
            vector_store=vector_store,
            job_search_provider=job_provider,
            document_generator=FakeDocGenerator(),
        )

    app.dependency_overrides[get_agent_service] = _fake_agent_service

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            headers_a = await _login(client, "agent_a@edu.org", "Student A")
            headers_b = await _login(client, "agent_b@edu.org", "Student B")

            # Prepare verified profile & skills for Student A
            await client.post(
                "/api/v1/profile",
                headers=headers_a,
                json={
                    "headline": "Backend Engineering Student",
                    "summary": "Builds Python FastAPI APIs",
                    "target_roles": ["Backend Intern"],
                    "preferred_locations": ["Remote"],
                },
            )
            await client.put(
                "/api/v1/profile/skills",
                headers=headers_a,
                json={
                    "skills": [
                        {"name": "Python", "category": "technical", "is_verified": True},
                        {"name": "FastAPI", "category": "technical", "is_verified": True},
                    ]
                },
            )

            # Index RAG & discover target job
            rag_sync = await client.post("/api/v1/agents/rag/sync", headers=headers_a)
            assert rag_sync.status_code == 200
            assert rag_sync.json()["indexed_chunks"] >= 1

            jobs_res = await client.get("/api/v1/jobs/search?q=Backend+Intern", headers=headers_a)
            assert jobs_res.status_code == 200
            job_id = jobs_res.json()["items"][0]["id"]

            # 1. Start application_prep LangGraph workflow -> MUST pause awaiting human approval
            wf_res = await client.post(
                "/api/v1/agents/workflows",
                headers=headers_a,
                json={
                    "requested_task": "Prepare application and tailored resume for Backend Intern",
                    "task_type": "application_prep",
                    "job_id": job_id,
                },
            )
            assert wf_res.status_code == 201
            wf = wf_res.json()
            assert wf["status"] == "PAUSED_FOR_APPROVAL", (
                f"error={wf.get('error_detail')} trace={wf.get('execution_trace')}"
            )
            assert wf["current_stage"] == "awaiting_human_approval"
            approval_id = wf["pending_approval_id"]
            app_id = wf["application_id"]
            assert approval_id is not None
            assert app_id is not None
            assert wf["validation_results"]["documents_grounded"] is True
            trace_nodes = [entry["node"] for entry in wf["execution_trace"]]
            assert trace_nodes == [
                "request_validator",
                "task_classifier",
                "rag_retriever",
                "job_matcher",
                "document_drafter",
                "approval_gate",
            ]

            # Linked application must be AWAITING_APPROVAL (NOT submitted without consent)
            app_before = await client.get(f"/api/v1/applications/{app_id}", headers=headers_a)
            assert app_before.status_code == 200
            assert app_before.json()["status"] == "AWAITING_APPROVAL"

            # Cross-user isolation check on both workflow and approval
            assert (
                await client.get(f"/api/v1/agents/workflows/{wf['id']}", headers=headers_b)
            ).status_code == 404
            assert (
                await client.post(f"/api/v1/approvals/{approval_id}/approve", headers=headers_b)
            ).status_code == 404

            # 2. Approve external action -> transition App to SUBMITTED & complete workflow
            approve_res = await client.post(
                f"/api/v1/approvals/{approval_id}/approve",
                headers=headers_a,
                json={"note": "Reviewed tailored resume and portal URL; approved to submit."},
            )
            assert approve_res.status_code == 200
            approved = approve_res.json()
            assert approved["status"] == "EXECUTED"
            assert approved["execution_result"]["application_transitioned_to_submitted"] is True

            app_after = await client.get(f"/api/v1/applications/{app_id}", headers=headers_a)
            assert app_after.status_code == 200
            assert app_after.json()["status"] == "SUBMITTED"

            wf_after = await client.get(f"/api/v1/agents/workflows/{wf['id']}", headers=headers_a)
            assert wf_after.status_code == 200
            assert wf_after.json()["status"] == "COMPLETED"
            assert wf_after.json()["execution_trace"][-1]["node"] == "action_executor"

            # 3. Minimal specialist routing check: career_advisory runs only advisory subset
            advisory_res = await client.post(
                "/api/v1/agents/workflows",
                headers=headers_a,
                json={"requested_task": "How prepared am I for backend internships?"},
            )
            assert advisory_res.status_code == 201
            adv = advisory_res.json()
            assert adv["status"] == "COMPLETED"
            assert [e["node"] for e in adv["execution_trace"]] == [
                "request_validator",
                "task_classifier",
                "rag_retriever",
                "advisory_responder",
            ]

            # 4. Rejection flow prevents execution and rolls application back to PREPARING
            manual_app = (
                await client.post(
                    "/api/v1/applications",
                    headers=headers_a,
                    json={"company_name": "Nova AI", "role_title": "ML Intern"},
                )
            ).json()
            req_approval = await client.post(
                "/api/v1/approvals",
                headers=headers_a,
                json={
                    "action_type": "submit_application",
                    "application_id": manual_app["id"],
                    "target_destination": "https://nova.ai/apply",
                    "title": "Submit Application: ML Intern at Nova AI",
                    "payload": {"notes": "Draft ready"},
                },
            )
            assert req_approval.status_code == 201
            rej_res = await client.post(
                f"/api/v1/approvals/{req_approval.json()['id']}/reject",
                headers=headers_a,
                json={"note": "Need to refine cover letter first."},
            )
            assert rej_res.status_code == 200
            assert rej_res.json()["status"] == "REJECTED"
            assert rej_res.json()["executed_at"] is None
            manual_app_after = (
                await client.get(f"/api/v1/applications/{manual_app['id']}", headers=headers_a)
            ).json()
            assert manual_app_after["status"] == "PREPARING"

            # Verify immutable audit log captured approval lifecycle
            async with app.state.db_session_factory() as db:
                events = set(
                    (
                        await db.scalars(select(AuditLog.event_type))
                    ).all()
                )
            expected_events = {
                "approval.requested",
                "approval.approved",
                "approval.executed",
                "approval.rejected",
            }
            assert expected_events <= events
