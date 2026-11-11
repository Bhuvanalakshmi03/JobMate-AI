"""Job discovery, normalization, caching, and bookmarking service."""

from __future__ import annotations

import hashlib
import json
import uuid

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.integrations.job_search.openai_web_search import (
    JobSearchProviderProtocol,
    JobSearchQuery,
)
from app.modules.authentication.models import User
from app.modules.jobs.models import Job
from app.modules.jobs.repository import JobRepository, SavedJobRepository
from app.modules.jobs.schemas import (
    JobDetailResponse,
    JobMatchPreview,
    JobSearchResponse,
    JobSummaryResponse,
    SavedJobResponse,
)
from app.modules.matching.models import JobMatch
from app.modules.matching.repository import JobMatchRepository
from app.repositories.audit_repository import AuditLogRepository

logger = get_logger(__name__)

SEARCH_CACHE_TTL_SECONDS = 900


class JobDiscoveryService:
    """Orchestrates live web-search job discovery, caching, persistence, and saving."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
        search_provider: JobSearchProviderProtocol,
    ) -> None:
        self._session = session
        self._settings = settings
        self._provider = search_provider
        self._jobs = JobRepository(session)
        self._saved = SavedJobRepository(session)
        self._matches = JobMatchRepository(session)
        self._audit = AuditLogRepository(session)

    def _cache_key(self, query: JobSearchQuery) -> str:
        raw = json.dumps(
            {
                "q": query.query.strip().lower(),
                "loc": (query.location or "").strip().lower(),
                "mode": (query.work_mode or "").strip().lower(),
                "exp": (query.experience_level or "").strip().lower(),
                "skills": sorted(s.strip().lower() for s in query.skills),
                "limit": query.limit,
            },
            sort_keys=True,
        )
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"jobmate:job_search:{digest}"

    async def _get_cached_job_ids(self, cache_key: str) -> list[uuid.UUID] | None:
        client: aioredis.Redis | None = None
        try:
            client = aioredis.from_url(
                self._settings.redis_url,
                socket_connect_timeout=1.0,
                socket_timeout=1.0,
            )
            raw = await client.get(cache_key)
            if not raw:
                return None
            ids_raw = json.loads(raw)
            if isinstance(ids_raw, list):
                return [uuid.UUID(str(item)) for item in ids_raw]
        except Exception as exc:
            logger.debug(
                "Job search cache read skipped",
                extra={"exception_class": exc.__class__.__name__},
            )
        finally:
            if client is not None:
                await client.aclose()
        return None

    async def _set_cached_job_ids(self, cache_key: str, job_ids: list[uuid.UUID]) -> None:
        client: aioredis.Redis | None = None
        try:
            client = aioredis.from_url(
                self._settings.redis_url,
                socket_connect_timeout=1.0,
                socket_timeout=1.0,
            )
            await client.set(
                cache_key,
                json.dumps([str(jid) for jid in job_ids]),
                ex=SEARCH_CACHE_TTL_SECONDS,
            )
        except Exception as exc:
            logger.debug(
                "Job search cache write skipped",
                extra={"exception_class": exc.__class__.__name__},
            )
        finally:
            if client is not None:
                await client.aclose()

    def _to_summary(
        self,
        *,
        job: Job,
        saved_ids: set[uuid.UUID],
        match_map: dict[uuid.UUID, JobMatch],
    ) -> JobSummaryResponse:
        match_row = match_map.get(job.id)
        preview = (
            JobMatchPreview(
                overall_score=match_row.overall_score,
                matching_skills=list(match_row.matching_skills),
                missing_skills=list(match_row.missing_skills),
                algorithm_version=match_row.algorithm_version,
            )
            if match_row is not None
            else None
        )
        return JobSummaryResponse(
            id=job.id,
            source_provider=job.source_provider,
            title=job.title,
            company=job.company,
            location=job.location,
            work_mode=job.work_mode,
            experience_level=job.experience_level,
            employment_type=job.employment_type,
            required_skills=list(job.required_skills),
            preferred_skills=list(job.preferred_skills),
            salary_range=job.salary_range,
            external_url=job.external_url,
            source_domain=job.source_domain,
            posted_at=job.posted_at,
            retrieved_at=job.retrieved_at,
            is_active=job.is_active,
            is_saved=job.id in saved_ids,
            match_preview=preview,
        )

    async def search_jobs(
        self,
        *,
        user: User,
        q: str | None = None,
        location: str | None = None,
        work_mode: str | None = None,
        experience_level: str | None = None,
        skills: list[str] | None = None,
        refresh: bool = False,
        limit: int = 10,
        offset: int = 0,
    ) -> JobSearchResponse:
        """Search cached/persisted listings or fetch live listings via OpenAI Web Search."""
        cleaned_q = (q or "").strip()
        skill_tuple = tuple(s.strip() for s in (skills or []) if s.strip())
        cached = False
        source = "database"
        jobs: list[Job] = []
        total = 0

        if not cleaned_q and not refresh:
            jobs, total = await self._jobs.search_local(
                location=location,
                work_mode=work_mode,
                experience_level=experience_level,
                skills=list(skill_tuple) if skill_tuple else None,
                limit=limit,
                offset=offset,
            )
        else:
            search_query = JobSearchQuery(
                query=cleaned_q or "software engineer intern",
                location=location,
                work_mode=work_mode,
                experience_level=experience_level,
                skills=skill_tuple,
                limit=limit,
            )
            cache_key = self._cache_key(search_query)

            provider_name = str(
                getattr(self._provider, "source_provider", "openai_web_search")
            )
            if not refresh:
                cached_ids = await self._get_cached_job_ids(cache_key)
                if cached_ids:
                    jobs = await self._jobs.get_by_ids(cached_ids[offset : offset + limit])
                    total = len(cached_ids)
                    cached = True
                    source = provider_name

            if not jobs and not refresh:
                local_rows, local_total = await self._jobs.search_local(
                    q=cleaned_q,
                    location=location,
                    work_mode=work_mode,
                    experience_level=experience_level,
                    skills=list(skill_tuple) if skill_tuple else None,
                    limit=limit,
                    offset=offset,
                )
                if local_rows:
                    jobs = local_rows
                    total = local_total
                    source = "database"

            if not jobs or refresh:
                discovered = await self._provider.search_jobs(search_query)
                persisted = await self._jobs.upsert_discovered(discovered)
                await self._set_cached_job_ids(cache_key, [j.id for j in persisted])
                jobs = persisted[offset : offset + limit]
                total = len(persisted)
                source = provider_name
                cached = False
                await self._audit.record(
                    event_type="jobs.discovered",
                    user_id=user.id,
                    resource_type="job_search",
                    details={
                        "query": search_query.query,
                        "result_count": len(persisted),
                        "provider": provider_name,
                    },
                )

        job_ids = [j.id for j in jobs]
        saved_ids = await self._saved.get_saved_job_ids(user.id)
        match_map = await self._matches.get_map_for_user_and_jobs(user_id=user.id, job_ids=job_ids)
        summaries = [
            self._to_summary(job=j, saved_ids=saved_ids, match_map=match_map) for j in jobs
        ]
        return JobSearchResponse(items=summaries, total=total, source=source, cached=cached)

    async def get_job_detail(self, *, user: User, job_id: uuid.UUID) -> JobDetailResponse:
        job = await self._jobs.get_by_id(job_id)
        if job is None:
            raise NotFoundError("Job listing not found.")
        saved_ids = await self._saved.get_saved_job_ids(user.id)
        match_map = await self._matches.get_map_for_user_and_jobs(
            user_id=user.id, job_ids=[job.id]
        )
        summary = self._to_summary(job=job, saved_ids=saved_ids, match_map=match_map)
        return JobDetailResponse(
            **summary.model_dump(),
            description=job.description,
            requirements_summary=job.requirements_summary,
            education_requirements=list(job.education_requirements),
            min_years_experience=job.min_years_experience,
        )

    async def save_job(
        self,
        *,
        user: User,
        job_id: uuid.UUID,
        notes: str | None = None,
    ) -> SavedJobResponse:
        job = await self._jobs.get_by_id(job_id)
        if job is None:
            raise NotFoundError("Job listing not found.")
        saved = await self._saved.save(user_id=user.id, job_id=job.id, notes=notes)
        await self._audit.record(
            event_type="jobs.saved",
            user_id=user.id,
            resource_type="job",
            resource_id=str(job.id),
        )
        return SavedJobResponse(
            job_id=job.id,
            is_saved=True,
            notes=saved.notes,
            saved_at=saved.created_at,
        )

    async def unsave_job(self, *, user: User, job_id: uuid.UUID) -> None:
        await self._saved.unsave(user_id=user.id, job_id=job_id)

    async def list_saved_jobs(
        self,
        *,
        user: User,
        limit: int = 50,
        offset: int = 0,
    ) -> JobSearchResponse:
        jobs, total = await self._saved.list_saved_jobs(
            user_id=user.id,
            limit=limit,
            offset=offset,
        )
        job_ids = [j.id for j in jobs]
        saved_ids = set(job_ids)
        match_map = await self._matches.get_map_for_user_and_jobs(user_id=user.id, job_ids=job_ids)
        summaries = [
            self._to_summary(job=j, saved_ids=saved_ids, match_map=match_map) for j in jobs
        ]
        return JobSearchResponse(items=summaries, total=total, source="saved", cached=False)
