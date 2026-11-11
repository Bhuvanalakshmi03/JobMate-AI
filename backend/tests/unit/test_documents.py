"""Unit and API tests for Phase 5 AI Document Generation, factuality, versioning, and export."""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime

import docx
import httpx
import pymupdf
from fastapi import FastAPI

from app.core.config import Settings
from app.integrations.job_search.openai_web_search import DiscoveredJobRecord, JobSearchQuery
from app.main import create_app
from app.modules.documents.generator import (
    GeneratedDocumentDraft,
    JobTargetContext,
    VerifiedCandidateContext,
)
from app.modules.documents.router import get_document_generator
from app.modules.jobs.router import get_job_search_provider
from app.modules.resume.extractor import RawExtractionOutput
from app.modules.resume.router import get_resume_extractor


class FakeJobProvider:
    def __init__(self, records: list[DiscoveredJobRecord]) -> None:
        self._records = records

    async def search_jobs(self, query: JobSearchQuery) -> list[DiscoveredJobRecord]:
        return list(self._records)


class FakeResumeExtractor:
    def __init__(self, raw_json: str) -> None:
        self._raw = raw_json

    async def extract(self, *, resume_text: str) -> RawExtractionOutput:
        return RawExtractionOutput(raw_json=self._raw, model="gpt-4o-mini-test", total_tokens=100)


class FakeDocumentGenerator:
    def __init__(
        self,
        *,
        tailored_json: str,
        cover_letter_json: str = "{}",
        note_json: str = "{}",
    ) -> None:
        self.tailored_json = tailored_json
        self.cover_letter_json = cover_letter_json
        self.note_json = note_json
        self.last_candidate: VerifiedCandidateContext | None = None

    async def generate_tailored_resume(
        self,
        *,
        candidate: VerifiedCandidateContext,
        job: JobTargetContext,
        focus_instructions: str | None = None,
    ) -> GeneratedDocumentDraft:
        self.last_candidate = candidate
        return GeneratedDocumentDraft(
            raw_json=self.tailored_json,
            model="gpt-4o-mini-test",
            total_tokens=220,
        )

    async def generate_cover_letter(
        self,
        *,
        candidate: VerifiedCandidateContext,
        job: JobTargetContext,
        tone: str = "professional",
        custom_notes: str | None = None,
    ) -> GeneratedDocumentDraft:
        self.last_candidate = candidate
        return GeneratedDocumentDraft(
            raw_json=self.cover_letter_json,
            model="gpt-4o-mini-test",
            total_tokens=180,
        )

    async def generate_application_note(
        self,
        *,
        candidate: VerifiedCandidateContext,
        job: JobTargetContext,
        max_words: int = 150,
    ) -> GeneratedDocumentDraft:
        self.last_candidate = candidate
        return GeneratedDocumentDraft(
            raw_json=self.note_json,
            model="gpt-4o-mini-test",
            total_tokens=90,
        )


def _sample_pdf_bytes() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "Maya Rao\n"
        "Experience: Backend Intern at CloudNova (2025)\n"
        "Built REST APIs in Python and FastAPI reducing latency by 30%.\n"
        "Education: B.Tech CS, IIIT Bangalore\n"
        "Skills: Python, FastAPI, PostgreSQL",
    )
    data = bytes(doc.tobytes())
    doc.close()
    return data


async def _login(client: httpx.AsyncClient, email: str, name: str) -> dict[str, str]:
    res = await client.post("/api/v1/auth/dev-login", json={"email": email, "full_name": name})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def test_document_generation_requires_verified_facts_and_blocks_hallucinations(
    migrated_test_app: FastAPI,
    test_settings: Settings,
) -> None:
    _ = migrated_test_app
    now = datetime.now(UTC)
    job_provider = FakeJobProvider(
        [
            DiscoveredJobRecord(
                source_provider="openai_web_search",
                title="Backend Engineer",
                company="Orbit Systems",
                location="Bengaluru",
                work_mode="hybrid",
                experience_level="entry_level",
                employment_type="full_time",
                description="Looking for Python and FastAPI engineer.",
                requirements_summary=None,
                required_skills=["Python", "FastAPI"],
                preferred_skills=[],
                education_requirements=[],
                min_years_experience=0.0,
                salary_range=None,
                external_url="https://careers.orbitsystems.io/backend",
                source_domain="careers.orbitsystems.io",
                posted_at=now,
                raw_metadata={},
            )
        ]
    )
    hallucinated_resume = json.dumps(
        {
            "summary": "Backend engineer with 95% uptime guarantee.",
            "selected_skills": ["Python", "QuantumRust"],
            "experience": [
                {
                    "title": "Staff Engineer",
                    "organization": "InventedMegaCorp",
                    "date_range": "2024 - 2026",
                    "bullets": ["Increased revenue by 400%."],
                }
            ],
            "projects": [],
            "education": [],
        }
    )
    doc_gen = FakeDocumentGenerator(tailored_json=hallucinated_resume)

    settings = test_settings.model_copy(update={"dev_auth_enabled": True})
    app = create_app(settings=settings)
    app.dependency_overrides[get_job_search_provider] = lambda: job_provider
    app.dependency_overrides[get_document_generator] = lambda: doc_gen

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            headers = await _login(client, "maya@edu.org", "Maya Rao")
            jobs_res = await client.get("/api/v1/jobs/search?q=Backend", headers=headers)
            job_id = jobs_res.json()["items"][0]["id"]

            # 1. Fails cleanly when user has no verified facts/profile/skills
            no_facts = await client.post(
                "/api/v1/documents/tailor-resume",
                headers=headers,
                json={"job_id": job_id},
            )
            assert no_facts.status_code == 422

            # 2. Create verified skill & profile, then ensure hallucinated claims are blocked
            await client.post(
                "/api/v1/profile",
                headers=headers,
                json={"headline": "CS Student"},
            )
            await client.put(
                "/api/v1/profile/skills",
                headers=headers,
                json={"skills": [{"name": "Python", "category": "language"}]},
            )
            hallucination_res = await client.post(
                "/api/v1/documents/tailor-resume",
                headers=headers,
                json={"job_id": job_id},
            )
            assert hallucination_res.status_code == 422
            err_msg = hallucination_res.json()["error"]["message"].lower()
            assert "unsupported factual claims" in err_msg


async def test_tailored_resume_cover_letter_note_versioning_and_exports(
    migrated_test_app: FastAPI,
    test_settings: Settings,
    tmp_path: object,
) -> None:
    _ = migrated_test_app
    now = datetime.now(UTC)
    job_provider = FakeJobProvider(
        [
            DiscoveredJobRecord(
                source_provider="openai_web_search",
                title="Backend Engineer",
                company="Orbit Systems",
                location="Remote",
                work_mode="remote",
                experience_level="entry_level",
                employment_type="full_time",
                description="Python, FastAPI, PostgreSQL backend role.",
                requirements_summary=None,
                required_skills=["Python", "FastAPI"],
                preferred_skills=["PostgreSQL"],
                education_requirements=[],
                min_years_experience=0.0,
                salary_range=None,
                external_url="https://careers.orbitsystems.io/backend-2",
                source_domain="careers.orbitsystems.io",
                posted_at=now,
                raw_metadata={},
            )
        ]
    )
    resume_extraction_json = json.dumps(
        {
            "completeness_score": 85,
            "overall_assessment": "Strong backend resume.",
            "strengths": ["FastAPI intern experience"],
            "weaknesses": [],
            "missing_skills": [],
            "recommendations": [],
            "facts": [
                {
                    "fact_type": "experience",
                    "title": "Backend Intern",
                    "organization": "CloudNova",
                    "start_date": "2025",
                    "end_date": "2025",
                    "description": "Built REST APIs in Python and FastAPI reducing latency by 30%.",
                    "source_section": "Experience",
                    "evidence_excerpt": "Backend Intern at CloudNova",
                    "confidence": 0.95,
                },
                {
                    "fact_type": "education",
                    "title": "B.Tech CS",
                    "organization": "IIIT Bangalore",
                    "source_section": "Education",
                    "evidence_excerpt": "B.Tech CS, IIIT Bangalore",
                    "confidence": 0.95,
                },
                {
                    "fact_type": "skill",
                    "title": "Python",
                    "structured_data": {"category": "language"},
                    "source_section": "Skills",
                    "evidence_excerpt": "Skills: Python, FastAPI, PostgreSQL",
                    "confidence": 0.98,
                },
                {
                    "fact_type": "skill",
                    "title": "FastAPI",
                    "structured_data": {"category": "framework"},
                    "source_section": "Skills",
                    "evidence_excerpt": "Skills: Python, FastAPI, PostgreSQL",
                    "confidence": 0.98,
                },
            ],
        }
    )

    valid_tailored = json.dumps(
        {
            "summary": "Backend engineer experienced in Python and FastAPI APIs.",
            "selected_skills": ["Python", "FastAPI"],
            "experience": [
                {
                    "title": "Backend Intern",
                    "organization": "CloudNova",
                    "date_range": "2025",
                    "bullets": ["Built REST APIs in Python and FastAPI reducing latency by 30%."],
                }
            ],
            "projects": [],
            "education": [{"degree": "B.Tech CS", "institution": "IIIT Bangalore"}],
        }
    )
    valid_cover_letter = json.dumps(
        {
            "subject": "Application for Backend Engineer — Maya Rao",
            "salutation": "Dear Orbit Systems Hiring Team,",
            "paragraphs": [
                "During my Backend Intern role at CloudNova, I built Python and FastAPI APIs.",
                "I would welcome the opportunity to contribute to Orbit Systems.",
            ],
            "closing": "Sincerely,",
        }
    )
    valid_note = json.dumps(
        {
            "note": (
                "Hi Orbit Systems team, I built Python & FastAPI APIs at CloudNova reducing "
                "latency by 30% and would love to apply for Backend Engineer."
            )
        }
    )

    doc_gen = FakeDocumentGenerator(
        tailored_json=valid_tailored,
        cover_letter_json=valid_cover_letter,
        note_json=valid_note,
    )
    settings = test_settings.model_copy(
        update={
            "dev_auth_enabled": True,
            "local_storage_path": str(tmp_path) + "/vault",
        }
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_job_search_provider] = lambda: job_provider
    app.dependency_overrides[get_resume_extractor] = lambda: FakeResumeExtractor(
        resume_extraction_json
    )
    app.dependency_overrides[get_document_generator] = lambda: doc_gen

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            headers_a = await _login(client, "maya@iiitb.edu", "Maya Rao")
            headers_b = await _login(client, "other@iiitb.edu", "Other User")

            # Upload, analyze, and verify facts
            up = await client.post(
                "/api/v1/resumes/upload",
                headers=headers_a,
                files={"file": ("maya.pdf", _sample_pdf_bytes(), "application/pdf")},
            )
            resume_id = up.json()["id"]
            analysis = (
                await client.post(f"/api/v1/resumes/{resume_id}/analyze", headers=headers_a)
            ).json()
            await client.patch(
                f"/api/v1/resumes/{resume_id}/facts",
                headers=headers_a,
                json={
                    "sync_to_profile": True,
                    "updates": [
                        {"fact_id": f["id"], "action": "verify"} for f in analysis["facts"]
                    ],
                },
            )

            # Discover job
            job_id = (
                await client.get("/api/v1/jobs/search?q=Backend", headers=headers_a)
            ).json()["items"][0]["id"]

            # Generate tailored resume
            tailored_res = await client.post(
                "/api/v1/documents/tailor-resume",
                headers=headers_a,
                json={"job_id": job_id, "resume_id": resume_id},
            )
            assert tailored_res.status_code == 201
            doc_v1 = tailored_res.json()
            assert doc_v1["version"] == 1
            assert doc_v1["factuality_report"]["is_grounded"] is True
            assert "CloudNova" in doc_v1["content_markdown"]

            # Generate cover letter & application note
            cl_res = await client.post(
                "/api/v1/documents/cover-letter",
                headers=headers_a,
                json={"job_id": job_id, "resume_id": resume_id, "tone": "professional"},
            )
            assert cl_res.status_code == 201
            assert cl_res.json()["document_type"] == "cover_letter"

            note_res = await client.post(
                "/api/v1/documents/application-note",
                headers=headers_a,
                json={"job_id": job_id, "resume_id": resume_id, "max_words": 100},
            )
            assert note_res.status_code == 201
            assert note_res.json()["document_type"] == "application_note"

            # Edit tailored resume creating version 2 while keeping version 1
            edit_res = await client.patch(
                f"/api/v1/documents/{doc_v1['id']}",
                headers=headers_a,
                json={
                    "content_markdown": (
                        doc_v1["content_markdown"] + "\n\n## Availability\nImmediate"
                    ),
                    "create_new_version": True,
                },
            )
            assert edit_res.status_code == 200
            doc_v2 = edit_res.json()
            assert doc_v2["version"] == 2
            assert doc_v2["is_user_edited"] is True
            assert [v["version"] for v in doc_v2["versions"]] == [2, 1]

            # Original uploaded resume was never overwritten
            orig_resume = (
                await client.get(f"/api/v1/resumes/{resume_id}", headers=headers_a)
            ).json()
            assert "Immediate" not in orig_resume["extracted_text"]

            # Export PDF, DOCX, and Markdown
            pdf_dl = await client.get(
                f"/api/v1/documents/{doc_v2['id']}/download?format=pdf",
                headers=headers_a,
            )
            assert pdf_dl.status_code == 200
            assert pdf_dl.headers["content-type"].startswith("application/pdf")
            assert pdf_dl.content.startswith(b"%PDF-")
            exported_pdf = pymupdf.open(stream=pdf_dl.content, filetype="pdf")
            extracted_pdf_text = exported_pdf.load_page(0).get_text("text")
            exported_pdf.close()
            assert "Maya Rao" in extracted_pdf_text
            assert "CloudNova" in extracted_pdf_text

            docx_dl = await client.get(
                f"/api/v1/documents/{doc_v2['id']}/download?format=docx",
                headers=headers_a,
            )
            assert docx_dl.status_code == 200
            exported_docx = docx.Document(io.BytesIO(docx_dl.content))
            joined_docx = "\n".join(p.text for p in exported_docx.paragraphs)
            assert "Maya Rao" in joined_docx
            assert "CloudNova" in joined_docx

            # Cross-user isolation: User B cannot access, edit, or download User A's document
            assert (
                await client.get(f"/api/v1/documents/{doc_v2['id']}", headers=headers_b)
            ).status_code == 404
            assert (
                await client.get(
                    f"/api/v1/documents/{doc_v2['id']}/download?format=pdf",
                    headers=headers_b,
                )
            ).status_code == 404
