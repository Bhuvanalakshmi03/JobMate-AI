"""Job matching service combining deterministic weighted scoring and semantic embeddings."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.integrations.openai.client import EmbeddingClientProtocol
from app.modules.authentication.models import User
from app.modules.jobs.models import Job
from app.modules.jobs.repository import JobRepository, SavedJobRepository
from app.modules.jobs.schemas import JobMatchPreview, JobSummaryResponse
from app.modules.matching.models import JobMatch
from app.modules.matching.repository import JobMatchRepository
from app.modules.matching.schemas import (
    JobMatchResponse,
    MatchingWeights,
    RecommendedJobItem,
    RecommendedJobsResponse,
)
from app.modules.matching.scorer import (
    ALGORITHM_VERSION,
    CandidateScoringInput,
    JobScoringInput,
    compute_match_score,
    cosine_similarity,
)
from app.modules.profile.repository import ProfileRepository, SkillRepository
from app.modules.resume.models import ResumeFact
from app.repositories.audit_repository import AuditLogRepository

logger = get_logger(__name__)


class JobMatchingService:
    """Computes, caches embeddings for, and persists explainable job matches."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        embedding_client: EmbeddingClientProtocol | None = None,
        weights: MatchingWeights | None = None,
    ) -> None:
        self._session = session
        self._embeddings = embedding_client
        self._weights = weights or MatchingWeights()
        self._jobs = JobRepository(session)
        self._saved = SavedJobRepository(session)
        self._matches = JobMatchRepository(session)
        self._profiles = ProfileRepository(session)
        self._skills = SkillRepository(session)
        self._audit = AuditLogRepository(session)

    async def _build_candidate_input(self, user: User) -> CandidateScoringInput:
        profile = await self._profiles.get_by_user_id(user.id)
        skills = await self._skills.list_by_user_id(user.id)
        verified_facts = list(
            (
                await self._session.scalars(
                    select(ResumeFact).where(
                        ResumeFact.user_id == user.id,
                        ResumeFact.is_verified.is_(True),
                        ResumeFact.fact_type.in_(("experience", "internship", "project")),
                    )
                )
            ).all()
        )
        exp_texts = [
            " ".join(
                part
                for part in (fact.title, fact.organization, fact.description)
                if part and part.strip()
            )
            for fact in verified_facts
        ]

        return CandidateScoringInput(
            skills=[s.name for s in skills],
            target_roles=list(profile.target_roles) if profile else [],
            headline=profile.headline if profile else None,
            experience_level=profile.experience_level if profile else None,
            years_of_experience=profile.years_of_experience if profile else None,
            degree=profile.degree if profile else None,
            location=profile.location if profile else None,
            preferred_locations=list(profile.preferred_locations) if profile else [],
            work_mode_preferences=list(profile.work_mode_preferences) if profile else [],
            verified_experience_texts=exp_texts,
        )

    def _candidate_semantic_summary(self, candidate: CandidateScoringInput) -> str:
        parts: list[str] = []
        if candidate.headline:
            parts.append(candidate.headline)
        if candidate.target_roles:
            parts.append("Target roles: " + ", ".join(candidate.target_roles))
        if candidate.skills:
            parts.append("Skills: " + ", ".join(candidate.skills))
        if candidate.verified_experience_texts:
            parts.append("Experience: " + " | ".join(candidate.verified_experience_texts[:6]))
        return "\n".join(parts).strip()

    async def _compute_semantic_similarities(
        self,
        *,
        candidate: CandidateScoringInput,
        jobs: list[Job],
    ) -> dict[uuid.UUID, float]:
        if self._embeddings is None or not jobs:
            return {}
        candidate_text = self._candidate_semantic_summary(candidate)
        if not candidate_text:
            return {}

        jobs_needing_vectors = [j for j in jobs if not j.embedding_vector]
        texts_to_embed = [candidate_text] + [
            f"{j.title} at {j.company}\n"
            f"Required: {', '.join(j.required_skills)}\n{j.description[:2500]}"
            for j in jobs_needing_vectors
        ]

        try:
            vectors = await self._embeddings.embed_texts(texts_to_embed)
        except Exception as exc:
            logger.warning(
                "Semantic embedding unavailable; falling back to deterministic scoring",
                extra={"exception_class": exc.__class__.__name__},
            )
            return {}

        if not vectors:
            return {}

        cand_vec = vectors[0]
        for job_obj, vec in zip(jobs_needing_vectors, vectors[1:], strict=False):
            job_obj.embedding_vector = vec

        if jobs_needing_vectors:
            await self._session.flush()

        similarities: dict[uuid.UUID, float] = {}
        for job_obj in jobs:
            if job_obj.embedding_vector:
                similarities[job_obj.id] = cosine_similarity(cand_vec, job_obj.embedding_vector)
        return similarities

    async def calculate_match_for_job(
        self,
        *,
        user: User,
        job_id: uuid.UUID,
        use_semantic: bool = True,
    ) -> JobMatchResponse:
        job = await self._jobs.get_by_id(job_id)
        if job is None or not job.is_active:
            raise NotFoundError("Job listing not found.")

        candidate = await self._build_candidate_input(user)
        similarities = (
            await self._compute_semantic_similarities(candidate=candidate, jobs=[job])
            if use_semantic
            else {}
        )
        result = compute_match_score(
            candidate=candidate,
            job=JobScoringInput(
                title=job.title,
                description=job.description,
                required_skills=list(job.required_skills),
                preferred_skills=list(job.preferred_skills),
                experience_level=job.experience_level,
                min_years_experience=job.min_years_experience,
                education_requirements=list(job.education_requirements),
                location=job.location,
                work_mode=job.work_mode,
                posted_at=job.posted_at,
                retrieved_at=job.retrieved_at,
            ),
            weights=self._weights,
            semantic_similarity=similarities.get(job.id),
        )
        persisted = await self._matches.upsert(user_id=user.id, job_id=job.id, result=result)
        await self._audit.record(
            event_type="jobs.matched",
            user_id=user.id,
            resource_type="job",
            resource_id=str(job.id),
            details={"overall_score": persisted.overall_score},
        )
        return JobMatchResponse.model_validate(persisted)

    async def get_recommended_jobs(
        self,
        *,
        user: User,
        limit: int = 20,
        use_semantic: bool = True,
    ) -> RecommendedJobsResponse:
        jobs = await self._jobs.list_active(limit=max(limit, 30))
        if not jobs:
            return RecommendedJobsResponse(
                items=[],
                total=0,
                algorithm_version=ALGORITHM_VERSION,
            )

        candidate = await self._build_candidate_input(user)
        saved_ids = await self._saved.get_saved_job_ids(user.id)
        similarities = (
            await self._compute_semantic_similarities(candidate=candidate, jobs=jobs)
            if use_semantic
            else {}
        )

        paired: list[tuple[Job, JobMatch]] = []
        for job in jobs:
            result = compute_match_score(
                candidate=candidate,
                job=JobScoringInput(
                    title=job.title,
                    description=job.description,
                    required_skills=list(job.required_skills),
                    preferred_skills=list(job.preferred_skills),
                    experience_level=job.experience_level,
                    min_years_experience=job.min_years_experience,
                    education_requirements=list(job.education_requirements),
                    location=job.location,
                    work_mode=job.work_mode,
                    posted_at=job.posted_at,
                    retrieved_at=job.retrieved_at,
                ),
                weights=self._weights,
                semantic_similarity=similarities.get(job.id),
            )
            match_row = await self._matches.upsert(user_id=user.id, job_id=job.id, result=result)
            paired.append((job, match_row))

        paired.sort(key=lambda item: item[1].overall_score, reverse=True)
        top = paired[:limit]

        items = [
            RecommendedJobItem(
                job=JobSummaryResponse(
                    **JobSummaryResponse.model_validate(job).model_dump(
                        exclude={"is_saved", "match_preview"}
                    ),
                    is_saved=job.id in saved_ids,
                    match_preview=JobMatchPreview(
                        overall_score=match_row.overall_score,
                        matching_skills=list(match_row.matching_skills),
                        missing_skills=list(match_row.missing_skills),
                        algorithm_version=match_row.algorithm_version,
                    ),
                ),
                match=JobMatchResponse.model_validate(match_row),
            )
            for job, match_row in top
        ]
        return RecommendedJobsResponse(
            items=items,
            total=len(items),
            algorithm_version=ALGORITHM_VERSION,
        )
