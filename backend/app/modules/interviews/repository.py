"""Repository for user-scoped interview sessions, questions, answers, and feedback."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import utc_now
from app.modules.interviews.models import (
    InterviewAnswer,
    InterviewFeedback,
    InterviewQuestion,
    InterviewSession,
)


class InterviewRepository:
    """Data access layer strictly isolated by user_id."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_session(
        self,
        *,
        user_id: uuid.UUID,
        job_id: uuid.UUID | None,
        application_id: uuid.UUID | None,
        title: str,
        target_role: str,
        company_name: str | None,
        focus_area: str,
        difficulty: str,
    ) -> InterviewSession:
        row = InterviewSession(
            user_id=user_id,
            job_id=job_id,
            application_id=application_id,
            title=title.strip()[:255],
            target_role=target_role.strip()[:255],
            company_name=company_name.strip()[:255] if company_name else None,
            focus_area=focus_area,
            difficulty=difficulty,
            status="CREATED",
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_session(
        self, *, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> InterviewSession | None:
        return await self._session.scalar(
            select(InterviewSession).where(
                InterviewSession.id == session_id,
                InterviewSession.user_id == user_id,
            )
        )

    async def list_sessions(
        self,
        *,
        user_id: uuid.UUID,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[InterviewSession], int]:
        stmt = select(InterviewSession).where(InterviewSession.user_id == user_id)
        count_stmt = (
            select(func.count())
            .select_from(InterviewSession)
            .where(InterviewSession.user_id == user_id)
        )
        if status:
            stmt = stmt.where(InterviewSession.status == status)
            count_stmt = count_stmt.where(InterviewSession.status == status)
        total = int((await self._session.scalar(count_stmt)) or 0)
        rows = list(
            (
                await self._session.scalars(
                    stmt.order_by(InterviewSession.updated_at.desc())
                    .offset(offset)
                    .limit(limit)
                )
            ).all()
        )
        return rows, total

    async def delete_session(self, row: InterviewSession) -> None:
        await self._session.delete(row)
        await self._session.flush()

    async def list_questions(
        self, *, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[InterviewQuestion]:
        return list(
            (
                await self._session.scalars(
                    select(InterviewQuestion)
                    .where(
                        InterviewQuestion.session_id == session_id,
                        InterviewQuestion.user_id == user_id,
                    )
                    .order_by(InterviewQuestion.order_index.asc())
                )
            ).all()
        )

    async def get_question(
        self,
        *,
        question_id: uuid.UUID,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> InterviewQuestion | None:
        return await self._session.scalar(
            select(InterviewQuestion).where(
                InterviewQuestion.id == question_id,
                InterviewQuestion.session_id == session_id,
                InterviewQuestion.user_id == user_id,
            )
        )

    async def add_questions(
        self,
        *,
        session: InterviewSession,
        questions_data: list[dict[str, Any]],
    ) -> list[InterviewQuestion]:
        existing = await self.list_questions(session_id=session.id, user_id=session.user_id)
        start_order = max((q.order_index for q in existing), default=0) + 1
        created: list[InterviewQuestion] = []
        for idx, item in enumerate(questions_data):
            q = InterviewQuestion(
                session_id=session.id,
                user_id=session.user_id,
                order_index=start_order + idx,
                category=str(item.get("category") or "technical")[:32],
                prompt=str(item.get("prompt") or "").strip(),
                expected_topics=[str(t) for t in (item.get("expected_topics") or [])][:8],
                difficulty=str(item.get("difficulty") or session.difficulty)[:32],
                guidance=str(item["guidance"])[:1000] if item.get("guidance") else None,
            )
            self._session.add(q)
            created.append(q)
        session.question_count = len(existing) + len(created)
        session.updated_at = utc_now()
        await self._session.flush()
        for q in created:
            await self._session.refresh(q)
        return created

    async def upsert_answer(
        self,
        *,
        question: InterviewQuestion,
        answer_text: str,
        time_spent_seconds: int | None,
    ) -> InterviewAnswer:
        existing = await self._session.scalar(
            select(InterviewAnswer).where(
                InterviewAnswer.question_id == question.id,
                InterviewAnswer.user_id == question.user_id,
            )
        )
        now = utc_now()
        if existing is not None:
            existing.answer_text = answer_text.strip()
            existing.time_spent_seconds = time_spent_seconds
            existing.submitted_at = now
            await self._session.flush()
            await self._session.refresh(existing)
            return existing

        row = InterviewAnswer(
            question_id=question.id,
            session_id=question.session_id,
            user_id=question.user_id,
            answer_text=answer_text.strip(),
            time_spent_seconds=time_spent_seconds,
            submitted_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def list_answers(
        self, *, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[InterviewAnswer]:
        return list(
            (
                await self._session.scalars(
                    select(InterviewAnswer)
                    .where(
                        InterviewAnswer.session_id == session_id,
                        InterviewAnswer.user_id == user_id,
                    )
                    .order_by(InterviewAnswer.submitted_at.asc())
                )
            ).all()
        )

    async def get_feedback(
        self, *, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> InterviewFeedback | None:
        return await self._session.scalar(
            select(InterviewFeedback).where(
                InterviewFeedback.session_id == session_id,
                InterviewFeedback.user_id == user_id,
            )
        )

    async def list_recent_feedback(
        self, *, user_id: uuid.UUID, limit: int = 10
    ) -> list[InterviewFeedback]:
        return list(
            (
                await self._session.scalars(
                    select(InterviewFeedback)
                    .where(InterviewFeedback.user_id == user_id)
                    .order_by(InterviewFeedback.evaluated_at.desc())
                    .limit(limit)
                )
            ).all()
        )

    async def upsert_feedback(
        self,
        *,
        session: InterviewSession,
        overall_score: float,
        rubric_scores: dict[str, float],
        strengths: list[str],
        weaknesses: list[str],
        question_evaluations: list[dict[str, Any]],
        skill_improvement_plan: list[dict[str, Any]],
        summary: str,
        model_used: str | None,
        tokens_used: int,
    ) -> InterviewFeedback:
        existing = await self.get_feedback(session_id=session.id, user_id=session.user_id)
        now = utc_now()
        if existing is not None:
            existing.overall_score = overall_score
            existing.rubric_scores = rubric_scores
            existing.strengths = strengths
            existing.weaknesses = weaknesses
            existing.question_evaluations = question_evaluations
            existing.skill_improvement_plan = skill_improvement_plan
            existing.summary = summary
            existing.model_used = model_used
            existing.tokens_used = tokens_used
            existing.evaluated_at = now
            row = existing
        else:
            row = InterviewFeedback(
                session_id=session.id,
                user_id=session.user_id,
                overall_score=overall_score,
                rubric_scores=rubric_scores,
                strengths=strengths,
                weaknesses=weaknesses,
                question_evaluations=question_evaluations,
                skill_improvement_plan=skill_improvement_plan,
                summary=summary,
                model_used=model_used,
                tokens_used=tokens_used,
                evaluated_at=now,
            )
            self._session.add(row)

        session.overall_score = overall_score
        session.status = "EVALUATED"
        session.updated_at = now
        await self._session.flush()
        await self._session.refresh(row)
        return row
