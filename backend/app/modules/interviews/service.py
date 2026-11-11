"""Domain service coordinating mock interviews, rubric evaluation, and skill-gap plans."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import NotFoundError, ValidationError
from app.integrations.llm.factory import create_llm_client
from app.modules.applications.repository import ApplicationRepository
from app.modules.authentication.models import User
from app.modules.interviews.engine import InterviewAIProtocol, OpenAIInterviewEngine
from app.modules.interviews.repository import InterviewRepository
from app.modules.interviews.schemas import (
    GenerateQuestionsRequest,
    InterviewAnswerResponse,
    InterviewFeedbackResponse,
    InterviewQuestionResponse,
    InterviewSessionCreateRequest,
    InterviewSessionDetailResponse,
    InterviewSessionListResponse,
    InterviewSessionSummary,
    SkillGapPlanResponse,
    SkillImprovementItem,
    SubmitAnswerRequest,
)
from app.modules.jobs.repository import JobRepository
from app.modules.matching.models import JobMatch
from app.modules.profile.repository import ProfileRepository, SkillRepository
from app.modules.resume.models import ResumeFact
from app.repositories.audit_repository import AuditLogRepository


class InterviewService:
    """User-isolated business logic for mock interviews and skill-gap roadmaps."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
        engine: InterviewAIProtocol | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._engine: InterviewAIProtocol = engine or OpenAIInterviewEngine(
            create_llm_client(settings)
        )
        self._repo = InterviewRepository(session)
        self._jobs = JobRepository(session)
        self._apps = ApplicationRepository(session)
        self._profiles = ProfileRepository(session)
        self._skills = SkillRepository(session)
        self._audit = AuditLogRepository(session)

    async def _build_candidate_context(self, user: User) -> str:
        profile = await self._profiles.get_by_user_id(user.id)
        skills = await self._skills.list_by_user_id(user.id)
        facts = list(
            (
                await self._session.scalars(
                    select(ResumeFact)
                    .where(
                        ResumeFact.user_id == user.id,
                        ResumeFact.is_verified.is_(True),
                        ResumeFact.verification_status != "rejected",
                    )
                    .limit(20)
                )
            ).all()
        )
        lines = [
            f"Candidate: {user.full_name}",
            f"Headline: {profile.headline if profile else ''}",
            f"Skills: {', '.join(s.name for s in skills)}",
        ]
        for fact in facts:
            lines.append(
                f"- [{fact.fact_type}] {fact.title}"
                + (f" ({fact.organization})" if fact.organization else "")
                + (f": {fact.description[:180]}" if fact.description else "")
            )
        return "\n".join(lines).strip()

    async def _resolve_job_description(
        self, *, job_id: uuid.UUID | None, application_id: uuid.UUID | None, user_id: uuid.UUID
    ) -> tuple[str | None, str | None, str]:
        resolved_role: str | None = None
        resolved_company: str | None = None
        description_parts: list[str] = []

        if application_id is not None:
            app = await self._apps.get_by_id_for_user(
                application_id=application_id, user_id=user_id
            )
            if app is None:
                raise NotFoundError("Linked application not found.")
            resolved_role = app.role_title
            resolved_company = app.company_name
            if app.job_id and job_id is None:
                job_id = app.job_id

        if job_id is not None:
            job = await self._jobs.get_by_id(job_id)
            if job is None:
                raise NotFoundError("Target job listing not found.")
            resolved_role = resolved_role or job.title
            resolved_company = resolved_company or job.company
            description_parts.append(
                f"Role: {job.title} at {job.company}\n"
                f"Required Skills: {', '.join(job.required_skills)}\n"
                f"Description: {job.description[:2500]}"
            )

        return resolved_role, resolved_company, "\n".join(description_parts)

    async def create_session(
        self,
        *,
        user: User,
        payload: InterviewSessionCreateRequest,
    ) -> InterviewSessionDetailResponse:
        job_role, job_company, job_desc = await self._resolve_job_description(
            job_id=payload.job_id,
            application_id=payload.application_id,
            user_id=user.id,
        )
        target_role = (payload.target_role or job_role or "").strip()
        if not target_role:
            profile = await self._profiles.get_by_user_id(user.id)
            target_role = (
                profile.target_roles[0]
                if profile and profile.target_roles
                else "Software Engineer"
            )
        company_name = payload.company_name or job_company
        title = (
            payload.title.strip()
            if payload.title and payload.title.strip()
            else f"{target_role}" + (f" — {company_name}" if company_name else " Mock Interview")
        )

        session_row = await self._repo.create_session(
            user_id=user.id,
            job_id=payload.job_id,
            application_id=payload.application_id,
            title=title,
            target_role=target_role,
            company_name=company_name,
            focus_area=payload.focus_area,
            difficulty=payload.difficulty,
        )

        questions = []
        if payload.generate_questions:
            verified_context = await self._build_candidate_context(user)
            draft = await self._engine.generate_questions(
                target_role=session_row.target_role,
                company_name=session_row.company_name,
                focus_area=session_row.focus_area,
                difficulty=session_row.difficulty,
                count=payload.question_count,
                verified_context=verified_context,
                job_description=job_desc,
            )
            questions = await self._repo.add_questions(
                session=session_row, questions_data=draft.questions
            )

        await self._audit.record(
            event_type="interview.session_created",
            user_id=user.id,
            resource_type="interview_session",
            resource_id=str(session_row.id),
            details={
                "target_role": session_row.target_role,
                "question_count": session_row.question_count,
            },
        )
        return InterviewSessionDetailResponse(
            session=InterviewSessionSummary.model_validate(session_row),
            questions=[InterviewQuestionResponse.model_validate(q) for q in questions],
            answers=[],
            feedback=None,
        )

    async def list_sessions(
        self,
        *,
        user: User,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> InterviewSessionListResponse:
        rows, total = await self._repo.list_sessions(
            user_id=user.id, status=status, limit=limit, offset=offset
        )
        return InterviewSessionListResponse(
            items=[InterviewSessionSummary.model_validate(r) for r in rows],
            total=total,
        )

    async def get_session_detail(
        self, *, user: User, session_id: uuid.UUID
    ) -> InterviewSessionDetailResponse:
        row = await self._repo.get_session(session_id=session_id, user_id=user.id)
        if row is None:
            raise NotFoundError("Interview session not found.")
        questions = await self._repo.list_questions(session_id=row.id, user_id=user.id)
        answers = await self._repo.list_answers(session_id=row.id, user_id=user.id)
        feedback = await self._repo.get_feedback(session_id=row.id, user_id=user.id)
        return InterviewSessionDetailResponse(
            session=InterviewSessionSummary.model_validate(row),
            questions=[InterviewQuestionResponse.model_validate(q) for q in questions],
            answers=[InterviewAnswerResponse.model_validate(a) for a in answers],
            feedback=InterviewFeedbackResponse.model_validate(feedback) if feedback else None,
        )

    async def delete_session(self, *, user: User, session_id: uuid.UUID) -> None:
        row = await self._repo.get_session(session_id=session_id, user_id=user.id)
        if row is None:
            raise NotFoundError("Interview session not found.")
        await self._repo.delete_session(row)

    async def generate_more_questions(
        self,
        *,
        user: User,
        session_id: uuid.UUID,
        payload: GenerateQuestionsRequest,
    ) -> list[InterviewQuestionResponse]:
        row = await self._repo.get_session(session_id=session_id, user_id=user.id)
        if row is None:
            raise NotFoundError("Interview session not found.")

        _, _, job_desc = await self._resolve_job_description(
            job_id=row.job_id, application_id=row.application_id, user_id=user.id
        )
        verified_context = await self._build_candidate_context(user)
        draft = await self._engine.generate_questions(
            target_role=row.target_role,
            company_name=row.company_name,
            focus_area=payload.focus_area or row.focus_area,
            difficulty=row.difficulty,
            count=payload.count,
            verified_context=verified_context,
            job_description=job_desc,
        )
        created = await self._repo.add_questions(session=row, questions_data=draft.questions)
        return [InterviewQuestionResponse.model_validate(q) for q in created]

    async def submit_answer(
        self,
        *,
        user: User,
        session_id: uuid.UUID,
        payload: SubmitAnswerRequest,
    ) -> InterviewAnswerResponse:
        row = await self._repo.get_session(session_id=session_id, user_id=user.id)
        if row is None:
            raise NotFoundError("Interview session not found.")
        question = await self._repo.get_question(
            question_id=payload.question_id, session_id=row.id, user_id=user.id
        )
        if question is None:
            raise NotFoundError("Interview question not found in this session.")

        answer = await self._repo.upsert_answer(
            question=question,
            answer_text=payload.answer_text,
            time_spent_seconds=payload.time_spent_seconds,
        )
        if row.status == "CREATED":
            row.status = "IN_PROGRESS"
            await self._session.flush()
        return InterviewAnswerResponse.model_validate(answer)

    async def evaluate_session(
        self, *, user: User, session_id: uuid.UUID
    ) -> InterviewFeedbackResponse:
        row = await self._repo.get_session(session_id=session_id, user_id=user.id)
        if row is None:
            raise NotFoundError("Interview session not found.")
        questions = await self._repo.list_questions(session_id=row.id, user_id=user.id)
        if not questions:
            raise ValidationError("Generate interview questions before evaluating.")
        answers = await self._repo.list_answers(session_id=row.id, user_id=user.id)
        if not answers:
            raise ValidationError("Submit at least one answer before running evaluation.")

        answer_by_q = {a.question_id: a for a in answers}
        qa_pairs = [
            {
                "question_id": str(q.id),
                "category": q.category,
                "prompt": q.prompt,
                "expected_topics": q.expected_topics,
                "answer_text": (
                    answer_by_q[q.id].answer_text if q.id in answer_by_q else "[No answer yet]"
                ),
            }
            for q in questions
        ]
        _, _, job_desc = await self._resolve_job_description(
            job_id=row.job_id, application_id=row.application_id, user_id=user.id
        )
        verified_context = await self._build_candidate_context(user)
        draft = await self._engine.evaluate_answers(
            target_role=row.target_role,
            company_name=row.company_name,
            difficulty=row.difficulty,
            qa_pairs=qa_pairs,
            verified_context=verified_context,
            job_description=job_desc,
        )
        feedback = await self._repo.upsert_feedback(
            session=row,
            overall_score=draft.overall_score,
            rubric_scores=draft.rubric_scores,
            strengths=draft.strengths,
            weaknesses=draft.weaknesses,
            question_evaluations=draft.question_evaluations,
            skill_improvement_plan=draft.skill_improvement_plan,
            summary=draft.summary,
            model_used=draft.model,
            tokens_used=draft.tokens_used,
        )
        await self._audit.record(
            event_type="interview.evaluated",
            user_id=user.id,
            resource_type="interview_session",
            resource_id=str(row.id),
            details={"overall_score": draft.overall_score, "tokens_used": draft.tokens_used},
        )
        return InterviewFeedbackResponse.model_validate(feedback)

    async def get_feedback(
        self, *, user: User, session_id: uuid.UUID
    ) -> InterviewFeedbackResponse:
        feedback = await self._repo.get_feedback(session_id=session_id, user_id=user.id)
        if feedback is None:
            raise NotFoundError("Interview feedback not generated yet for this session.")
        return InterviewFeedbackResponse.model_validate(feedback)

    async def get_skill_gap_plan(self, *, user: User) -> SkillGapPlanResponse:
        """Aggregate verified skills, missing skills from JobMatches, and interview weaknesses."""
        skills = await self._skills.list_by_user_id(user.id)
        verified_names = [s.name for s in skills]
        verified_lower = {s.normalized_name for s in skills}

        matches = list(
            (
                await self._session.scalars(
                    select(JobMatch)
                    .where(JobMatch.user_id == user.id)
                    .order_by(JobMatch.overall_score.desc())
                    .limit(15)
                )
            ).all()
        )
        missing_counter: dict[str, int] = {}
        for m in matches:
            for ms in m.missing_skills or []:
                cleaned = str(ms).strip()
                if cleaned and cleaned.lower() not in verified_lower:
                    missing_counter[cleaned] = missing_counter.get(cleaned, 0) + 1
        top_missing = [
            name
            for name, _ in sorted(
                missing_counter.items(), key=lambda pair: (-pair[1], pair[0].lower())
            )
        ][:10]

        recent_feedback = await self._repo.list_recent_feedback(user_id=user.id, limit=10)
        avg_score = (
            round(
                sum(fb.overall_score for fb in recent_feedback) / len(recent_feedback),
                1,
            )
            if recent_feedback
            else None
        )
        weaknesses: list[str] = []
        plan_items: list[SkillImprovementItem] = []
        seen_skills: set[str] = set()

        for fb in recent_feedback:
            for w in fb.weaknesses or []:
                text = str(w).strip()
                if text and text not in weaknesses:
                    weaknesses.append(text)
            for item in fb.skill_improvement_plan or []:
                if not isinstance(item, dict):
                    continue
                sk = str(item.get("skill") or "").strip()
                if not sk or sk.lower() in seen_skills:
                    continue
                seen_skills.add(sk.lower())
                plan_items.append(SkillImprovementItem.model_validate(item))

        for missing_skill in top_missing:
            if missing_skill.lower() in seen_skills:
                continue
            seen_skills.add(missing_skill.lower())
            freq = missing_counter.get(missing_skill, 1)
            plan_items.append(
                SkillImprovementItem(
                    skill=missing_skill,
                    current_gap=(
                        f"Requested across {freq} matched job posting(s), not yet in "
                        "your verified profile skills."
                    ),
                    priority="high" if freq >= 2 else "medium",
                    action_items=[
                        f"Build a focused mini-project or hands-on lab exercising {missing_skill}.",
                        f"Practice explaining trade-offs and common interview patterns in "
                        f"{missing_skill}.",
                    ],
                    estimated_hours=6 if freq >= 2 else 4,
                )
            )

        return SkillGapPlanResponse(
            verified_skills=verified_names,
            missing_skills_from_matches=top_missing,
            recurring_interview_weaknesses=weaknesses[:8],
            average_interview_score=avg_score,
            evaluated_sessions_count=len(recent_feedback),
            improvement_plan=plan_items[:12],
        )
