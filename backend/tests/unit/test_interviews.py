"""Unit and API tests for Phase 8 mock interviews, rubric evaluation, and skill-gap plans."""

from __future__ import annotations

import uuid
from typing import Any

import httpx
from fastapi import FastAPI

from app.core.config import Settings
from app.core.dependencies import DBSessionDep
from app.main import create_app
from app.modules.interviews.engine import EvaluationResultDraft, GeneratedQuestionDraft
from app.modules.interviews.router import get_interview_service
from app.modules.interviews.service import InterviewService
from app.modules.jobs.models import Job
from app.modules.jobs.repository import compute_job_content_hash, compute_job_fingerprint
from app.modules.matching.models import JobMatch


class FakeInterviewEngine:
    """Deterministic fake interview generator and rubric evaluator."""

    def __init__(self) -> None:
        self.last_verified_context = ""

    async def generate_questions(
        self,
        *,
        target_role: str,
        company_name: str | None,
        focus_area: str,
        difficulty: str,
        count: int,
        verified_context: str,
        job_description: str,
    ) -> GeneratedQuestionDraft:
        _ = (company_name, job_description)
        self.last_verified_context = verified_context
        questions = [
            {
                "category": "technical" if focus_area in ("mixed", "technical") else focus_area,
                "prompt": f"Explain how you structure async APIs in Python for {target_role}.",
                "expected_topics": ["FastAPI", "PostgreSQL", "Error handling"],
                "difficulty": difficulty,
                "guidance": "Highlight latency, connection pooling, and schema validation.",
            },
            {
                "category": "behavioral",
                "prompt": "Tell me about a challenging bug you resolved using STAR format.",
                "expected_topics": ["Situation", "Action", "Result"],
                "difficulty": difficulty,
                "guidance": "Keep outcome concrete and measurable.",
            },
        ][:count]
        return GeneratedQuestionDraft(
            questions=questions, model="gpt-4o-mini-test", tokens_used=110
        )

    async def evaluate_answers(
        self,
        *,
        target_role: str,
        company_name: str | None,
        difficulty: str,
        qa_pairs: list[dict[str, Any]],
        verified_context: str,
        job_description: str,
    ) -> EvaluationResultDraft:
        _ = (target_role, company_name, difficulty, verified_context, job_description)
        q_evals = []
        for idx, pair in enumerate(qa_pairs):
            q_evals.append(
                {
                    "question_id": str(pair["question_id"]),
                    "prompt": pair["prompt"],
                    "category": pair["category"],
                    "score": 84.0 if idx == 0 else 78.0,
                    "rubric": {
                        "technical_accuracy": 86.0 if idx == 0 else 76.0,
                        "communication_clarity": 85.0,
                        "star_structure": 74.0 if idx == 0 else 84.0,
                        "role_alignment": 85.0,
                    },
                    "strengths": ["Clear explanation of async database pooling."],
                    "improvements": ["Add explicit retry/timeout trade-off metrics."],
                    "sample_strong_points": ["Mention connection recycling and health probes."],
                }
            )
        return EvaluationResultDraft(
            overall_score=81.0,
            rubric_scores={
                "technical_accuracy": 81.0,
                "communication_clarity": 85.0,
                "star_structure": 79.0,
                "role_alignment": 85.0,
            },
            strengths=["Strong Python & FastAPI ownership"],
            weaknesses=["Quantify STAR impact more explicitly"],
            question_evaluations=q_evals,
            skill_improvement_plan=[
                {
                    "skill": "System Design Trade-offs",
                    "current_gap": "Practice articulating caching & retry bounds.",
                    "priority": "high",
                    "action_items": ["Walk through 2 async queue designs aloud."],
                    "estimated_hours": 5,
                }
            ],
            summary="Solid backend interview readiness with room to sharpen STAR results.",
            model="gpt-4o-mini-test",
            tokens_used=195,
        )


async def test_mock_interview_lifecycle_rubric_and_isolation(
    migrated_test_app: FastAPI,
    test_settings: Settings,
) -> None:
    _ = migrated_test_app
    app_settings = test_settings.model_copy(update={"dev_auth_enabled": True})
    app = create_app(app_settings)

    fake_engine = FakeInterviewEngine()

    def _override_service(session: DBSessionDep) -> InterviewService:
        return InterviewService(session=session, settings=app_settings, engine=fake_engine)

    app.dependency_overrides[get_interview_service] = _override_service

    # Seed a job and JobMatch for cross-job skill gap plan check.
    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        login_a = await client.post(
            "/api/v1/auth/dev-login",
            json={"email": "candidate_a@jobmate.local", "full_name": "Candidate A"},
        )
        headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}
        user_a_id = uuid.UUID(login_a.json()["user"]["id"])

        login_b = await client.post(
            "/api/v1/auth/dev-login",
            json={"email": "candidate_b@jobmate.local", "full_name": "Candidate B"},
        )
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        # Seed verified skill and job match missing skill directly in DB.
        await client.put(
            "/api/v1/profile/skills",
            headers=headers_a,
            json={
                "skills": [
                    {"name": "Python", "category": "technical", "proficiency": "advanced"}
                ]
            },
        )
        async with app.state.db_session_factory() as db:
            job = Job(
                source_provider="curated_test",
                canonical_fingerprint=compute_job_fingerprint(
                    title="Backend AI Engineer",
                    company="Stripe",
                    external_url="https://stripe.com/jobs/backend-ai",
                ),
                title="Backend AI Engineer",
                company="Stripe",
                location="Remote",
                work_mode="remote",
                experience_level="entry_level",
                employment_type="full_time",
                description="Build resilient Python services with Redis and Docker.",
                required_skills=["Python", "Redis", "Docker"],
                preferred_skills=[],
                education_requirements=[],
                external_url="https://stripe.com/jobs/backend-ai",
                content_hash=compute_job_content_hash(
                    title="Backend AI Engineer",
                    description="Build resilient Python services",
                    required_skills=["Python", "Redis", "Docker"],
                ),
            )
            db.add(job)
            await db.flush()
            db.add(
                JobMatch(
                    user_id=user_a_id,
                    job_id=job.id,
                    overall_score=80.0,
                    factor_scores={"skills": 70.0},
                    weights_used={"skills": 0.4},
                    matching_skills=["Python"],
                    missing_skills=["Redis", "Docker"],
                    match_explanation="Good Python alignment; missing Redis & Docker.",
                    recommended_preparation=["Learn Redis caching"],
                )
            )
            await db.commit()
            job_id = str(job.id)

        # 1. Create mock interview session with generated questions
        create_res = await client.post(
            "/api/v1/interviews",
            headers=headers_a,
            json={
                "job_id": job_id,
                "focus_area": "mixed",
                "difficulty": "entry",
                "question_count": 2,
            },
        )
        assert create_res.status_code == 201
        created = create_res.json()
        session_id = created["session"]["id"]
        assert created["session"]["target_role"] == "Backend AI Engineer"
        assert created["session"]["company_name"] == "Stripe"
        assert created["session"]["status"] == "CREATED"
        assert len(created["questions"]) == 2
        assert "Python" in fake_engine.last_verified_context

        # Premature evaluation before answers -> 422
        premature = await client.post(
            f"/api/v1/interviews/{session_id}/evaluate", headers=headers_a
        )
        assert premature.status_code == 422

        # 2. Submit answers for both questions
        for idx, q in enumerate(created["questions"]):
            ans_res = await client.post(
                f"/api/v1/interviews/{session_id}/answers",
                headers=headers_a,
                json={
                    "question_id": q["id"],
                    "answer_text": f"Detailed STAR response {idx + 1} covering design and impact.",
                    "time_spent_seconds": 120,
                },
            )
            assert ans_res.status_code == 201

        detail_mid = await client.get(f"/api/v1/interviews/{session_id}", headers=headers_a)
        assert detail_mid.status_code == 200
        assert detail_mid.json()["session"]["status"] == "IN_PROGRESS"
        assert len(detail_mid.json()["answers"]) == 2

        # 3. Generate one extra HR question cleanly
        extra_q = await client.post(
            f"/api/v1/interviews/{session_id}/questions",
            headers=headers_a,
            json={"count": 1, "focus_area": "hr"},
        )
        assert extra_q.status_code == 201
        assert len(extra_q.json()) == 1

        # 4. Evaluate answers with rubric
        eval_res = await client.post(
            f"/api/v1/interviews/{session_id}/evaluate", headers=headers_a
        )
        assert eval_res.status_code == 200
        fb = eval_res.json()
        assert fb["overall_score"] >= 70.0
        assert "technical_accuracy" in fb["rubric_scores"]
        assert len(fb["skill_improvement_plan"]) >= 1

        # Fetch feedback endpoint directly
        get_fb = await client.get(f"/api/v1/interviews/{session_id}/feedback", headers=headers_a)
        assert get_fb.status_code == 200
        assert get_fb.json()["id"] == fb["id"]

        # 5. Consolidated skill-gap plan combines interview weaknesses + JobMatch missing skills
        gap_res = await client.get("/api/v1/interviews/skill-gap-plan", headers=headers_a)
        assert gap_res.status_code == 200
        gap_data = gap_res.json()
        assert "Python" in gap_data["verified_skills"]
        assert "Redis" in gap_data["missing_skills_from_matches"]
        assert gap_data["evaluated_sessions_count"] == 1
        assert len(gap_data["improvement_plan"]) >= 2

        # 6. Cross-user isolation
        assert (
            await client.get(f"/api/v1/interviews/{session_id}", headers=headers_b)
        ).status_code == 404
        assert (
            await client.post(f"/api/v1/interviews/{session_id}/evaluate", headers=headers_b)
        ).status_code == 404
        assert (
            await client.delete(f"/api/v1/interviews/{session_id}", headers=headers_b)
        ).status_code == 404

        # Owner deletes session cleanly
        assert (
            await client.delete(f"/api/v1/interviews/{session_id}", headers=headers_a)
        ).status_code == 204
