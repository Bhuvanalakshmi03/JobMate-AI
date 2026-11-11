"""Repository for persisted JobMatch evaluations scoped by user_id."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import utc_now
from app.modules.matching.models import JobMatch
from app.modules.matching.scorer import MatchScoreResult


class JobMatchRepository:
    """Data access layer for user-scoped job matching scores."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_user_and_job(
        self,
        *,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> JobMatch | None:
        return await self._session.scalar(
            select(JobMatch).where(JobMatch.user_id == user_id, JobMatch.job_id == job_id)
        )

    async def get_map_for_user_and_jobs(
        self,
        *,
        user_id: uuid.UUID,
        job_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, JobMatch]:
        if not job_ids:
            return {}
        rows = await self._session.scalars(
            select(JobMatch).where(
                JobMatch.user_id == user_id,
                JobMatch.job_id.in_(job_ids),
            )
        )
        return {row.job_id: row for row in rows.all()}

    async def upsert(
        self,
        *,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
        result: MatchScoreResult,
    ) -> JobMatch:
        existing = await self.get_for_user_and_job(user_id=user_id, job_id=job_id)
        now = utc_now()
        if existing is not None:
            existing.algorithm_version = result.algorithm_version
            existing.overall_score = result.overall_score
            existing.factor_scores = result.factor_scores
            existing.weights_used = result.weights_used
            existing.matching_skills = result.matching_skills
            existing.missing_skills = result.missing_skills
            existing.match_explanation = result.match_explanation
            existing.recommended_preparation = result.recommended_preparation
            existing.computed_at = now
            await self._session.flush()
            return existing

        match = JobMatch(
            user_id=user_id,
            job_id=job_id,
            algorithm_version=result.algorithm_version,
            overall_score=result.overall_score,
            factor_scores=result.factor_scores,
            weights_used=result.weights_used,
            matching_skills=result.matching_skills,
            missing_skills=result.missing_skills,
            match_explanation=result.match_explanation,
            recommended_preparation=result.recommended_preparation,
            computed_at=now,
        )
        self._session.add(match)
        await self._session.flush()
        return match
