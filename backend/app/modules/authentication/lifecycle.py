"""Account lifecycle service: GDPR-friendly user data export & permanent deletion."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.integrations.storage.local import LocalPrivateStorage
from app.modules.applications.models import Application, ApplicationHistory
from app.modules.approvals.models import ApprovalRequest
from app.modules.authentication.models import User
from app.modules.copilot.models import CopilotConversation, CopilotMessage
from app.modules.documents.models import GeneratedDocument
from app.modules.interviews.models import (
    InterviewAnswer,
    InterviewFeedback,
    InterviewQuestion,
    InterviewSession,
)
from app.modules.jobs.models import SavedJob
from app.modules.matching.models import JobMatch
from app.modules.memory.models import CareerMemory
from app.modules.profile.models import UserProfile, UserSkill
from app.modules.reminders.models import Reminder
from app.modules.resume.models import Resume, ResumeFact


async def export_user_data(*, session: AsyncSession, user: User) -> dict[str, Any]:
    """Assemble sanitized JSON export of all personal career data owned by the user."""
    profile = await session.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    skills = list(
        (await session.scalars(select(UserSkill).where(UserSkill.user_id == user.id))).all()
    )
    resumes = list(
        (await session.scalars(select(Resume).where(Resume.user_id == user.id))).all()
    )
    facts = list(
        (await session.scalars(select(ResumeFact).where(ResumeFact.user_id == user.id))).all()
    )
    saved_jobs = list(
        (await session.scalars(select(SavedJob).where(SavedJob.user_id == user.id))).all()
    )
    matches = list(
        (await session.scalars(select(JobMatch).where(JobMatch.user_id == user.id))).all()
    )
    documents = list(
        (
            await session.scalars(
                select(GeneratedDocument).where(GeneratedDocument.user_id == user.id)
            )
        ).all()
    )
    apps = list(
        (await session.scalars(select(Application).where(Application.user_id == user.id))).all()
    )
    history = list(
        (
            await session.scalars(
                select(ApplicationHistory).where(ApplicationHistory.user_id == user.id)
            )
        ).all()
    )
    interviews = list(
        (
            await session.scalars(
                select(InterviewSession).where(InterviewSession.user_id == user.id)
            )
        ).all()
    )
    questions = list(
        (
            await session.scalars(
                select(InterviewQuestion).where(InterviewQuestion.user_id == user.id)
            )
        ).all()
    )
    answers = list(
        (
            await session.scalars(
                select(InterviewAnswer).where(InterviewAnswer.user_id == user.id)
            )
        ).all()
    )
    feedback = list(
        (
            await session.scalars(
                select(InterviewFeedback).where(InterviewFeedback.user_id == user.id)
            )
        ).all()
    )
    memories = list(
        (await session.scalars(select(CareerMemory).where(CareerMemory.user_id == user.id))).all()
    )
    reminders = list(
        (await session.scalars(select(Reminder).where(Reminder.user_id == user.id))).all()
    )
    approvals = list(
        (
            await session.scalars(
                select(ApprovalRequest).where(ApprovalRequest.user_id == user.id)
            )
        ).all()
    )
    convs = list(
        (
            await session.scalars(
                select(CopilotConversation).where(CopilotConversation.user_id == user.id)
            )
        ).all()
    )
    msgs = list(
        (
            await session.scalars(
                select(CopilotMessage).where(CopilotMessage.user_id == user.id)
            )
        ).all()
    )

    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "account": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "timezone": user.timezone,
            "oauth_provider": user.oauth_provider,
            "created_at": user.created_at.isoformat(),
        },
        "profile": (
            {
                "headline": profile.headline,
                "summary": profile.summary,
                "location": profile.location,
                "university": profile.university,
                "degree": profile.degree,
                "target_roles": profile.target_roles,
                "ai_consent_given": profile.ai_consent_given,
                "notification_consent": profile.notification_consent,
            }
            if profile
            else None
        ),
        "skills": [
            {"name": s.name, "category": s.category, "proficiency": s.proficiency}
            for s in skills
        ],
        "resumes": [
            {"id": str(r.id), "filename": r.original_filename, "status": r.parse_status}
            for r in resumes
        ],
        "resume_facts": [
            {
                "id": str(f.id),
                "type": f.fact_type,
                "title": f.title,
                "status": f.verification_status,
            }
            for f in facts
        ],
        "saved_jobs_count": len(saved_jobs),
        "job_matches": [
            {"job_id": str(m.job_id), "overall_score": m.overall_score} for m in matches
        ],
        "generated_documents": [
            {
                "id": str(d.id),
                "type": d.document_type,
                "title": d.title,
                "version": d.version,
            }
            for d in documents
        ],
        "applications": [
            {
                "id": str(a.id),
                "company": a.company_name,
                "role": a.role_title,
                "status": a.status,
            }
            for a in apps
        ],
        "application_history_count": len(history),
        "interview_sessions": [
            {
                "id": str(i.id),
                "title": i.title,
                "status": i.status,
                "score": i.overall_score,
            }
            for i in interviews
        ],
        "interview_questions_count": len(questions),
        "interview_answers_count": len(answers),
        "interview_feedback_count": len(feedback),
        "career_memory": [
            {
                "id": str(m.id),
                "category": m.category,
                "title": m.title,
                "content": m.content,
            }
            for m in memories
        ],
        "reminders": [
            {
                "id": str(r.id),
                "title": r.title,
                "status": r.status,
                "scheduled_for": r.scheduled_for.isoformat(),
            }
            for r in reminders
        ],
        "approvals_count": len(approvals),
        "copilot_conversations": [{"id": str(c.id), "title": c.title} for c in convs],
        "copilot_messages_count": len(msgs),
    }


async def delete_user_account(
    *, session: AsyncSession, settings: Settings, user: User
) -> None:
    """Permanently delete a user's stored files and cascading database account record."""
    resumes = list(
        (await session.scalars(select(Resume).where(Resume.user_id == user.id))).all()
    )
    storage = LocalPrivateStorage(settings.local_storage_path)
    for resume in resumes:
        if resume.storage_key:
            await storage.delete(key=resume.storage_key)

    await session.delete(user)
    await session.flush()
