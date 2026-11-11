"""Idempotent realistic data seeder for an existing CareerPilot user account.

Populates realistic jobs, explainable JobMatch scores, tailored grounded documents,
multi-stage applications + history, pending human approvals, workflow runs, and a
starter Co-Pilot chat conversation without modifying existing resumes or ResumeFacts.

Usage:
    cd backend && .venv/bin/python -m scripts.seed_user_data --email mukilan069@gmail.com
"""

from __future__ import annotations

import argparse
import asyncio
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401
from app.core.config import get_settings
from app.database.base import utc_now
from app.database.connection import create_db_engine, create_session_factory
from app.modules.agents.models import WorkflowRun
from app.modules.applications.models import Application, ApplicationHistory
from app.modules.approvals.models import ApprovalRequest
from app.modules.authentication.models import User
from app.modules.copilot.models import CopilotConversation, CopilotMessage
from app.modules.documents.models import GeneratedDocument
from app.modules.jobs.models import Job, SavedJob
from app.modules.jobs.repository import compute_job_content_hash, compute_job_fingerprint
from app.modules.matching.service import JobMatchingService
from app.modules.profile.models import UserProfile, UserSkill
from app.modules.resume.models import Resume

CURATED_REALISTIC_JOBS: tuple[dict[str, Any], ...] = (
    {
        "title": "Software Engineer - Full Stack & AI",
        "company": "Freshworks",
        "location": "Chennai, India",
        "work_mode": "hybrid",
        "experience_level": "entry_level",
        "employment_type": "full_time",
        "min_years_experience": 0.5,
        "salary_range": "INR 10L - 14L",
        "external_url": "https://careers.freshworks.com/jobs/software-engineer-fullstack-ai-chennai",
        "source_domain": "careers.freshworks.com",
        "required_skills": ["Python", "React.js", "PostgreSQL", "REST APIs", "Docker"],
        "preferred_skills": ["FastAPI", "TypeScript", "Machine Learning"],
        "education_requirements": ["B.E.", "B.Tech"],
        "description": (
            "Build AI-assisted SaaS product workflows across Python FastAPI services and "
            "React.js frontends at Freshworks Chennai. Collaborate closely with product "
            "engineers to deliver low-latency APIs, telemetry pipelines, and intelligent UX."
        ),
        "requirements_summary": (
            "Strong Python + React.js fundamentals, relational databases, and REST API design."
        ),
    },
    {
        "title": "Junior Backend Engineer (Python / FastAPI)",
        "company": "Chargebee",
        "location": "Chennai, India",
        "work_mode": "hybrid",
        "experience_level": "entry_level",
        "employment_type": "full_time",
        "min_years_experience": 0.5,
        "salary_range": "INR 9L - 13L",
        "external_url": "https://www.chargebee.com/careers/junior-backend-python-fastapi",
        "source_domain": "chargebee.com",
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "REST APIs", "Docker"],
        "preferred_skills": ["Redis", "Git", "TypeScript"],
        "education_requirements": ["B.E.", "Computer Science"],
        "description": (
            "Design resilient billing and subscription automation APIs using Python, FastAPI, "
            "PostgreSQL, and async background workers in Chargebee's Chennai engineering hub."
        ),
        "requirements_summary": (
            "Hands-on Python backend internship or project delivery with SQL and REST APIs."
        ),
    },
    {
        "title": "Associate AI / ML Platform Engineer",
        "company": "Postman",
        "location": "Bengaluru, India",
        "work_mode": "hybrid",
        "experience_level": "entry_level",
        "employment_type": "full_time",
        "min_years_experience": 1.0,
        "salary_range": "INR 12L - 18L",
        "external_url": "https://www.postman.com/company/careers/associate-ai-ml-platform",
        "source_domain": "postman.com",
        "required_skills": ["Python", "Machine Learning", "PyTorch", "REST APIs", "Docker"],
        "preferred_skills": ["FastAPI", "LangGraph", "TypeScript"],
        "education_requirements": ["B.E.", "Computer Science"],
        "description": (
            "Help build internal agentic evaluation harnesses, semantic search indexing, and "
            "API intelligence microservices powering developer productivity workflows."
        ),
        "requirements_summary": (
            "Experience with Python ML pipelines, evaluation tooling, and backend services."
        ),
    },
    {
        "title": "Computer Vision & Deep Learning Engineer",
        "company": "Kissflow",
        "location": "Chennai, India",
        "work_mode": "onsite",
        "experience_level": "entry_level",
        "employment_type": "full_time",
        "min_years_experience": 0.5,
        "salary_range": "INR 8L - 12L",
        "external_url": "https://kissflow.com/careers/computer-vision-deep-learning-chennai",
        "source_domain": "kissflow.com",
        "required_skills": ["Python", "OpenCV", "PyTorch", "Machine Learning"],
        "preferred_skills": ["FastAPI", "React.js", "Docker"],
        "education_requirements": ["B.E."],
        "description": (
            "Develop document OCR, computer vision feature extractors, and intelligent workflow "
            "automation services using Python, OpenCV, and PyTorch."
        ),
        "requirements_summary": (
            "Practical OpenCV / deep learning project track record paired with API deployment."
        ),
    },
    {
        "title": "Product Software Engineer (React + Python)",
        "company": "Razorpay",
        "location": "Remote (India)",
        "work_mode": "remote",
        "experience_level": "entry_level",
        "employment_type": "full_time",
        "min_years_experience": 0.5,
        "salary_range": "INR 12L - 16L",
        "external_url": "https://razorpay.com/jobs/product-software-engineer-react-python",
        "source_domain": "razorpay.com",
        "required_skills": ["Python", "React.js", "TypeScript", "PostgreSQL", "REST APIs"],
        "preferred_skills": ["Tailwind CSS", "Docker", "FastAPI"],
        "education_requirements": ["B.E.", "B.Tech"],
        "description": (
            "Ship accessible merchant dashboard experiences in React/TypeScript backed by "
            "observable Python APIs and reliable PostgreSQL transactions."
        ),
        "requirements_summary": (
            "Full-stack ownership mindset with React.js, TypeScript, and Python backend skills."
        ),
    },
)

EXTRA_VERIFIED_SKILLS: tuple[tuple[str, str, str, float], ...] = (
    ("FastAPI", "technical", "advanced", 1.5),
    ("PostgreSQL", "technical", "intermediate", 1.5),
    ("TypeScript", "technical", "intermediate", 1.0),
    ("PyTorch", "technical", "intermediate", 1.0),
    ("Machine Learning", "technical", "intermediate", 1.5),
    ("REST APIs", "technical", "advanced", 1.5),
    ("Docker", "technical", "intermediate", 1.0),
    ("LangGraph", "technical", "intermediate", 0.5),
    ("Tailwind CSS", "technical", "intermediate", 1.0),
    ("Git", "technical", "advanced", 2.0),
)


async def _ensure_profile_and_skills(session: AsyncSession, user: User) -> UserProfile:
    profile = await session.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    if profile is None:
        profile = UserProfile(user_id=user.id)
        session.add(profile)

    if not profile.headline:
        profile.headline = "Full-Stack & AI/ML Software Engineer · B.E. Computer Science"
    if not profile.summary:
        profile.summary = (
            "Computer Science Engineering graduate candidate at Nadar Saraswathi College of "
            "Engineering and Technology with hands-on software, AI/ML, and team leadership "
            "experience across SecureNext Software Pvt. Ltd, ParkQwik Private Limited, Navi "
            "Promotions, and Computira Soft Solutions. Smart India Hackathon Winner and creator "
            "of EcoTrack."
        )
    if not profile.location:
        profile.location = "Chennai"
    if not profile.experience_level:
        profile.experience_level = "entry_level"
    if profile.years_of_experience is None:
        profile.years_of_experience = 1.5
    if profile.graduation_year is None:
        profile.graduation_year = 2025
    if not profile.target_roles:
        profile.target_roles = [
            "AI / ML Software Engineer",
            "Backend Engineer (Python / FastAPI)",
            "Full-Stack Developer",
            "AI / Deep Learning Intern",
        ]
    if not profile.preferred_locations:
        profile.preferred_locations = ["Chennai", "Bengaluru", "Remote"]
    if not profile.work_mode_preferences:
        profile.work_mode_preferences = ["hybrid", "onsite", "remote"]
    profile.ai_consent_given = True
    profile.notification_consent = True
    profile.profile_verified = True

    existing_skills = set(
        (
            await session.scalars(
                select(UserSkill.normalized_name).where(UserSkill.user_id == user.id)
            )
        ).all()
    )
    for name, category, proficiency, years in EXTRA_VERIFIED_SKILLS:
        norm = name.strip().lower()
        if norm not in existing_skills:
            session.add(
                UserSkill(
                    user_id=user.id,
                    name=name,
                    normalized_name=norm,
                    category=category,
                    proficiency=proficiency,
                    years_experience=years,
                    is_verified=True,
                    source="profile_seed",
                )
            )
            existing_skills.add(norm)

    await session.flush()
    return profile


async def _upsert_curated_jobs(session: AsyncSession) -> dict[str, Job]:
    now = utc_now()
    by_company: dict[str, Job] = {}
    for idx, item in enumerate(CURATED_REALISTIC_JOBS):
        fp = compute_job_fingerprint(
            title=str(item["title"]),
            company=str(item["company"]),
            external_url=str(item["external_url"]),
        )
        existing = await session.scalar(select(Job).where(Job.canonical_fingerprint == fp))
        if existing is None:
            content_hash = compute_job_content_hash(
                title=str(item["title"]),
                description=str(item["description"]),
                required_skills=list(item["required_skills"]),
            )
            existing = Job(
                source_provider="curated_seed",
                canonical_fingerprint=fp,
                title=str(item["title"]),
                company=str(item["company"]),
                location=str(item["location"]),
                work_mode=str(item["work_mode"]),
                experience_level=str(item["experience_level"]),
                employment_type=str(item["employment_type"]),
                description=str(item["description"]),
                requirements_summary=str(item["requirements_summary"]),
                required_skills=list(item["required_skills"]),
                preferred_skills=list(item["preferred_skills"]),
                education_requirements=list(item["education_requirements"]),
                min_years_experience=float(item["min_years_experience"]),
                salary_range=str(item["salary_range"]),
                external_url=str(item["external_url"]),
                source_domain=str(item["source_domain"]),
                posted_at=now - timedelta(days=idx + 1),
                retrieved_at=now,
                is_active=True,
                content_hash=content_hash,
            )
            session.add(existing)
            await session.flush()
        by_company[existing.company] = existing

    # Also collect existing active jobs in DB for application linking.
    all_jobs = list((await session.scalars(select(Job).where(Job.is_active.is_(True)))).all())
    for job in all_jobs:
        by_company.setdefault(job.company, job)
    return by_company


async def _ensure_documents(
    session: AsyncSession,
    *,
    user: User,
    source_resume: Resume | None,
    jobs_by_company: dict[str, Job],
) -> tuple[GeneratedDocument, GeneratedDocument]:
    resume_title = "Tailored Resume - AI / Deep Learning Intern (Zoho Corporation)"
    cover_title = "Cover Letter - Software Engineer Full Stack & AI (Freshworks)"
    zoho_job = jobs_by_company.get("Zoho Corporation")
    freshworks_job = jobs_by_company.get("Freshworks")

    tailored_resume = await session.scalar(
        select(GeneratedDocument).where(
            GeneratedDocument.user_id == user.id,
            GeneratedDocument.title == resume_title,
        )
    )
    if tailored_resume is None:
        tailored_resume = GeneratedDocument(
            user_id=user.id,
            job_id=zoho_job.id if zoho_job else None,
            source_resume_id=source_resume.id if source_resume else None,
            document_type="tailored_resume",
            title=resume_title,
            version_group_id=uuid.uuid4(),
            version=1,
            content_markdown=(
                f"# {user.full_name}\n"
                "Chennai, India · B.E. Computer Science Engineering (Nadar Saraswathi College of "
                "Engineering and Technology)\n\n"
                "## Technical Skills\n"
                "Python, OpenCV, PyTorch, React.js, FastAPI, PostgreSQL, REST APIs, Docker\n\n"
                "## Verified Experience\n"
                "- **Backend Developer & Team Lead** — ParkQwik Private Limited\n"
                "- **Software Engineer | AI/ML Team Member** — Navi Promotions\n"
                "- **Programmer | AI Team Member** — SecureNext Software Pvt. Ltd\n"
                "- **Full Stack Developer** — Computira Soft Solutions\n\n"
                "## Highlighted Projects & Awards\n"
                "- **EcoTrack** (Smart India Hackathon Winning Project)\n"
                "- **Dr. Kalam Young Achiever Award 2024**\n"
                "- Certifications: Python 101 for Data Science; Full Stack Development "
                "(Infosys Springboard)\n"
            ),
            factuality_report={
                "status": "verified",
                "verified_claim_count": 11,
                "unverified_claim_count": 0,
                "grounded_sources": ["profile", "verified_resume_facts"],
            },
            is_user_edited=False,
            model_used="seeded-grounded-template",
            tokens_used=0,
        )
        session.add(tailored_resume)

    cover_letter = await session.scalar(
        select(GeneratedDocument).where(
            GeneratedDocument.user_id == user.id,
            GeneratedDocument.title == cover_title,
        )
    )
    if cover_letter is None:
        cover_letter = GeneratedDocument(
            user_id=user.id,
            job_id=freshworks_job.id if freshworks_job else None,
            source_resume_id=source_resume.id if source_resume else None,
            document_type="cover_letter",
            title=cover_title,
            version_group_id=uuid.uuid4(),
            version=1,
            content_markdown=(
                "Dear Freshworks Engineering Hiring Team,\n\n"
                "I am excited to apply for the Software Engineer - Full Stack & AI position in "
                "Chennai. During my B.E. in Computer Science Engineering at Nadar Saraswathi "
                "College of Engineering and Technology, I gained hands-on software engineering "
                "experience across SecureNext Software Pvt. Ltd, ParkQwik Private Limited (Backend "
                "Developer & Team Lead), Navi Promotions (AI/ML Team Member), and Computira Soft "
                "Solutions.\n\n"
                "Building EcoTrack — our Smart India Hackathon winning project — taught me how to "
                "combine Python backend services, OpenCV/AI pipelines, and responsive React.js UIs "
                "into reliable software.\n\n"
                "Thank you for considering my application.\n\n"
                f"Sincerely,\n{user.full_name}"
            ),
            factuality_report={
                "status": "verified",
                "verified_claim_count": 8,
                "unverified_claim_count": 0,
                "grounded_sources": ["profile", "verified_resume_facts"],
            },
            is_user_edited=False,
            model_used="seeded-grounded-template",
            tokens_used=0,
        )
        session.add(cover_letter)

    await session.flush()
    return tailored_resume, cover_letter


async def _ensure_saved_jobs_and_applications(
    session: AsyncSession,
    *,
    user: User,
    jobs_by_company: dict[str, Job],
    tailored_resume: GeneratedDocument,
    cover_letter: GeneratedDocument,
) -> dict[str, Application]:
    now = utc_now()
    for company in ("Zoho Corporation", "Freshworks", "Chargebee", "Postman"):
        job = jobs_by_company.get(company)
        if job is None:
            continue
        exists = await session.scalar(
            select(SavedJob).where(SavedJob.user_id == user.id, SavedJob.job_id == job.id)
        )
        if exists is None:
            session.add(
                SavedJob(
                    user_id=user.id,
                    job_id=job.id,
                    notes=f"High-priority Chennai/India AI & engineering opportunity at {company}.",
                )
            )

    specs: list[dict[str, Any]] = [
        {
            "company": "Zoho Corporation",
            "status": "INTERVIEW_SCHEDULED",
            "applied_at": now - timedelta(days=9),
            "follow_up_at": now + timedelta(days=2),
            "deadline_at": now + timedelta(days=10),
            "notes": (
                "Technical screening scheduled. Review Python, OpenCV & EcoTrack architecture."
            ),
            "tailored_resume_id": tailored_resume.id,
            "cover_letter_id": None,
            "timeline": [
                (None, "SAVED", "Discovered Zoho Chennai AI / Deep Learning Intern role.", 12),
                (
                    "SAVED",
                    "PREPARING",
                    "Generated tailored grounded resume for Zoho AI Intern.",
                    11,
                ),
                ("PREPARING", "AWAITING_APPROVAL", "Requested human submission confirmation.", 10),
                ("AWAITING_APPROVAL", "SUBMITTED", "Application submitted after user approval.", 9),
                (
                    "SUBMITTED",
                    "INTERVIEW_SCHEDULED",
                    "Shortlisted for technical round on ML & Python.",
                    2,
                ),
            ],
        },
        {
            "company": "Freshworks",
            "status": "AWAITING_APPROVAL",
            "applied_at": None,
            "follow_up_at": now + timedelta(days=5),
            "deadline_at": now + timedelta(days=7),
            "notes": "Tailored cover letter ready; pending final human submission approval.",
            "tailored_resume_id": tailored_resume.id,
            "cover_letter_id": cover_letter.id,
            "timeline": [
                (None, "SAVED", "Bookmarked Freshworks Full Stack & AI role.", 4),
                ("SAVED", "PREPARING", "Prepared verified Freshworks cover letter.", 3),
                (
                    "PREPARING",
                    "AWAITING_APPROVAL",
                    "Submission packet staged for human approval.",
                    1,
                ),
            ],
        },
        {
            "company": "Xtract.io",
            "status": "SUBMITTED",
            "applied_at": now - timedelta(days=5),
            "follow_up_at": now + timedelta(days=3),
            "deadline_at": None,
            "notes": "Submitted AI/ML Intern application in Chennai; awaiting recruiter follow-up.",
            "tailored_resume_id": tailored_resume.id,
            "cover_letter_id": None,
            "timeline": [
                (None, "SAVED", "Saved Xtract.io Chennai AI/ML Intern listing.", 7),
                ("SAVED", "SUBMITTED", "Submitted application externally and logged follow-up.", 5),
            ],
        },
        {
            "company": "Chargebee",
            "status": "PREPARING",
            "applied_at": None,
            "follow_up_at": None,
            "deadline_at": now + timedelta(days=12),
            "notes": "Focusing on FastAPI + PostgreSQL backend architecture talking points.",
            "tailored_resume_id": None,
            "cover_letter_id": None,
            "timeline": [
                (None, "SAVED", "Saved Chargebee Junior Backend Engineer (Python/FastAPI).", 3),
                ("SAVED", "PREPARING", "Reviewing billing API concurrency case studies.", 2),
            ],
        },
        {
            "company": "HCLTech",
            "status": "SAVED",
            "applied_at": None,
            "follow_up_at": None,
            "deadline_at": now + timedelta(days=18),
            "notes": "Evaluate Chennai AI / Deep Learning track requirements.",
            "tailored_resume_id": None,
            "cover_letter_id": None,
            "timeline": [
                (None, "SAVED", "Saved from live Chennai AI internship discovery run.", 2),
            ],
        },
    ]

    apps_by_company: dict[str, Application] = {}
    for spec in specs:
        job = jobs_by_company.get(spec["company"])
        if job is None:
            continue
        existing = await session.scalar(
            select(Application).where(Application.user_id == user.id, Application.job_id == job.id)
        )
        if existing is None:
            existing = Application(
                user_id=user.id,
                job_id=job.id,
                tailored_resume_id=spec["tailored_resume_id"],
                cover_letter_id=spec["cover_letter_id"],
                company_name=job.company,
                role_title=job.title,
                job_url=job.external_url,
                location=job.location,
                status=spec["status"],
                applied_at=spec["applied_at"],
                deadline_at=spec["deadline_at"],
                follow_up_at=spec["follow_up_at"],
                notes=spec["notes"],
            )
            session.add(existing)
            await session.flush()

            for from_s, to_s, note, days_ago in spec["timeline"]:
                session.add(
                    ApplicationHistory(
                        application_id=existing.id,
                        user_id=user.id,
                        from_status=from_s,
                        to_status=to_s,
                        note=note,
                        changed_at=now - timedelta(days=days_ago),
                    )
                )
        apps_by_company[job.company] = existing

    await session.flush()
    return apps_by_company


async def _ensure_workflow_approvals_and_chat(
    session: AsyncSession,
    *,
    user: User,
    jobs_by_company: dict[str, Job],
    apps_by_company: dict[str, Application],
    cover_letter: GeneratedDocument,
) -> None:
    now = utc_now()
    freshworks_app = apps_by_company.get("Freshworks")
    zoho_app = apps_by_company.get("Zoho Corporation")
    freshworks_job = jobs_by_company.get("Freshworks")

    workflow_title = (
        "Prepare Freshworks Full Stack & AI application packet and stage submission approval"
    )
    existing_wf = await session.scalar(
        select(WorkflowRun).where(
            WorkflowRun.user_id == user.id,
            WorkflowRun.user_request == workflow_title,
        )
    )
    if existing_wf is None:
        existing_wf = WorkflowRun(
            user_id=user.id,
            job_id=freshworks_job.id if freshworks_job else None,
            application_id=freshworks_app.id if freshworks_app else None,
            task_type="application_prep",
            user_request=workflow_title,
            current_stage="human_approval_gate",
            status="AWAITING_APPROVAL",
            agent_outputs={
                "task_classifier": {
                    "task_category": "application_prep",
                    "reason": "Application preparation + submission gating requested.",
                },
                "document_tailoring": {
                    "cover_letter_id": str(cover_letter.id),
                    "verified_claims_only": True,
                },
            },
            validation_results={"factuality_passed": True, "unverified_claim_count": 0},
            execution_trace=[
                {
                    "stage": "request_validator",
                    "status": "completed",
                    "detail": "Validated user profile & verified facts.",
                    "duration_ms": 42.1,
                    "attempts": 1,
                },
                {
                    "stage": "job_matcher",
                    "status": "completed",
                    "detail": "Computed Freshworks match score and verified skill alignment.",
                    "duration_ms": 68.5,
                    "attempts": 1,
                },
                {
                    "stage": "human_approval_gate",
                    "status": "completed",
                    "detail": "Created pending submission approval request.",
                    "duration_ms": 18.2,
                    "attempts": 1,
                },
            ],
            total_tokens_used=0,
        )
        session.add(existing_wf)
        await session.flush()

    if freshworks_app is not None:
        sub_title = (
            f"Submit application: {freshworks_app.role_title} at {freshworks_app.company_name}"
        )
        existing_sub = await session.scalar(
            select(ApprovalRequest).where(
                ApprovalRequest.user_id == user.id,
                ApprovalRequest.title == sub_title,
            )
        )
        if existing_sub is None:
            sub_approval = ApprovalRequest(
                user_id=user.id,
                workflow_run_id=existing_wf.id,
                application_id=freshworks_app.id,
                action_type="submit_application",
                target_destination=freshworks_app.job_url or "https://careers.freshworks.com",
                title=sub_title,
                payload={
                    "application_id": str(freshworks_app.id),
                    "company_name": freshworks_app.company_name,
                    "role_title": freshworks_app.role_title,
                    "cover_letter_id": str(cover_letter.id),
                },
                status="PENDING",
            )
            session.add(sub_approval)
            await session.flush()
            existing_wf.pending_approval_id = sub_approval.id

    interview_start = (now + timedelta(days=3)).replace(
        hour=4, minute=30, second=0, microsecond=0
    )
    interview_end = interview_start + timedelta(minutes=45)
    cal_title = "Add Calendar Event: Zoho Corporation Technical Interview"
    existing_cal = await session.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.user_id == user.id,
            ApprovalRequest.title == cal_title,
        )
    )
    if existing_cal is None:
        session.add(
            ApprovalRequest(
                user_id=user.id,
                application_id=zoho_app.id if zoho_app else None,
                action_type="create_calendar_event",
                target_destination="Google Calendar (primary)",
                title=cal_title,
                payload={
                    "summary": "Zoho Corporation Technical Interview - AI / Deep Learning Intern",
                    "start_iso": interview_start.isoformat(),
                    "end_iso": interview_end.isoformat(),
                    "location": "Google Meet / Chennai",
                    "description": (
                        "Technical screening covering Python, OpenCV, Deep Learning, and "
                        "EcoTrack architecture."
                    ),
                    "timezone": "Asia/Kolkata",
                    "application_id": str(zoho_app.id) if zoho_app else None,
                },
                status="PENDING",
            )
        )

    conv_title = "Chennai AI & Backend Pipeline Assistant"
    existing_conv = await session.scalar(
        select(CopilotConversation).where(
            CopilotConversation.user_id == user.id,
            CopilotConversation.title == conv_title,
        )
    )
    if existing_conv is None:
        conv = CopilotConversation(
            user_id=user.id,
            title=conv_title,
            last_message_at=now,
        )
        session.add(conv)
        await session.flush()
        session.add(
            CopilotMessage(
                conversation_id=conv.id,
                user_id=user.id,
                role="user",
                content="Summarize my current applications, top job matches, and upcoming actions.",
                tool_calls=[],
                approval_ids=[],
                tokens_used=0,
                created_at=now - timedelta(minutes=2),
            )
        )
        session.add(
            CopilotMessage(
                conversation_id=conv.id,
                user_id=user.id,
                role="assistant",
                content=(
                    "Welcome back, **MUKILAN S**! Your CareerPilot workspace is loaded with "
                    "real pipeline data:\n\n"
                    "- **Active Applications**: Zoho Corporation (`INTERVIEW_SCHEDULED`), "
                    "Freshworks (`AWAITING_APPROVAL`), Xtract.io (`SUBMITTED`), Chargebee "
                    "(`PREPARING`), and HCLTech (`SAVED`).\n"
                    "- **Pending Human Approvals**: 1 Freshworks submission confirmation and 1 "
                    "Zoho interview Google Calendar event proposal ready for your review.\n"
                    "- **What you can ask me next**: Connect Google Calendar in the panel, ask me "
                    "to check your upcoming schedule, schedule follow-up reminders, draft or "
                    "tailor documents, or search live roles in Chennai / Bengaluru."
                ),
                tool_calls=[
                    {
                        "tool_name": "list_applications",
                        "arguments": {"limit": 10},
                        "status": "completed",
                        "result_preview": "5 tracked applications across pipeline stages.",
                    },
                    {
                        "tool_name": "get_top_job_matches",
                        "arguments": {"limit": 5},
                        "status": "completed",
                        "result_preview": "Ranked Chennai & India AI/Backend matches.",
                    },
                ],
                approval_ids=[],
                tokens_used=0,
                created_at=now - timedelta(minutes=1),
            )
        )


async def seed_user_workspace(email: str) -> dict[str, Any]:
    """Run idempotent seeding for the specified user account."""
    settings = get_settings()
    engine = create_db_engine(settings)
    session_factory = create_session_factory(engine)

    try:
        async with session_factory() as session:
            user = await session.scalar(select(User).where(User.email == email.lower()))
            if user is None:
                raise RuntimeError(f"User with email '{email}' not found in database.")

            source_resume = await session.scalar(
                select(Resume)
                .where(Resume.user_id == user.id)
                .order_by(Resume.created_at.desc())
            )
            await _ensure_profile_and_skills(session, user)
            jobs_by_company = await _upsert_curated_jobs(session)

            # Compute deterministic JobMatch scores across active jobs in DB.
            matching_service = JobMatchingService(session=session, embedding_client=None)
            recommended = await matching_service.get_recommended_jobs(
                user=user, limit=30, use_semantic=False
            )

            tailored_resume, cover_letter = await _ensure_documents(
                session,
                user=user,
                source_resume=source_resume,
                jobs_by_company=jobs_by_company,
            )
            apps_by_company = await _ensure_saved_jobs_and_applications(
                session,
                user=user,
                jobs_by_company=jobs_by_company,
                tailored_resume=tailored_resume,
                cover_letter=cover_letter,
            )
            await _ensure_workflow_approvals_and_chat(
                session,
                user=user,
                jobs_by_company=jobs_by_company,
                apps_by_company=apps_by_company,
                cover_letter=cover_letter,
            )
            await session.commit()

            return {
                "email": user.email,
                "user_id": str(user.id),
                "matched_jobs": recommended.total,
                "applications_seeded": len(apps_by_company),
                "preserved_resume_id": str(source_resume.id) if source_resume else None,
            }
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed realistic CareerPilot data for a user.")
    parser.add_argument("--email", default="mukilan069@gmail.com", help="Target user email.")
    args = parser.parse_args()
    summary = asyncio.run(seed_user_workspace(args.email))
    print("Seed completed:", summary)


if __name__ == "__main__":
    main()
