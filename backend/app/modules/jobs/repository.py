"""Repositories for normalized job listings and user-saved jobs."""

from __future__ import annotations

import hashlib
import re
import uuid
from urllib.parse import urlparse, urlunparse

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import utc_now
from app.integrations.job_search.openai_web_search import DiscoveredJobRecord
from app.modules.jobs.models import Job, SavedJob

_WS_RE = re.compile(r"\s+")


def _canonicalize_url(raw_url: str) -> str:
    parsed = urlparse(raw_url.strip())
    return urlunparse(
        (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), "", "", "")
    )


def compute_job_fingerprint(*, title: str, company: str, external_url: str) -> str:
    """Compute deterministic fingerprint to detect and deduplicate identical job postings."""
    norm_title = _WS_RE.sub(" ", title).strip().lower()
    norm_company = _WS_RE.sub(" ", company).strip().lower()
    canon_url = _canonicalize_url(external_url)
    raw = f"{norm_title}|{norm_company}|{canon_url}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_job_content_hash(*, title: str, description: str, required_skills: list[str]) -> str:
    """Compute content hash to avoid regenerating embeddings for unchanged jobs."""
    joined_skills = ",".join(sorted(s.strip().lower() for s in required_skills))
    raw = f"{title.strip()}|{description.strip()}|{joined_skills}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class JobRepository:
    """Data access layer for normalized Job records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, job_id: uuid.UUID) -> Job | None:
        return await self._session.scalar(select(Job).where(Job.id == job_id))

    async def get_by_ids(self, job_ids: list[uuid.UUID]) -> list[Job]:
        if not job_ids:
            return []
        rows = await self._session.scalars(select(Job).where(Job.id.in_(job_ids)))
        by_id = {row.id: row for row in rows.all()}
        return [by_id[jid] for jid in job_ids if jid in by_id]

    async def upsert_discovered(self, records: list[DiscoveredJobRecord]) -> list[Job]:
        """Persist new jobs and refresh existing duplicates atomically by canonical fingerprint."""
        if not records:
            return []

        deduped_by_fp: dict[str, DiscoveredJobRecord] = {}
        for rec in records:
            fp = compute_job_fingerprint(
                title=rec.title,
                company=rec.company,
                external_url=rec.external_url,
            )
            deduped_by_fp[fp] = rec

        fingerprints = list(deduped_by_fp.keys())
        existing_rows = await self._session.scalars(
            select(Job).where(Job.canonical_fingerprint.in_(fingerprints))
        )
        existing_map = {row.canonical_fingerprint: row for row in existing_rows.all()}
        now = utc_now()
        persisted: list[Job] = []

        for fp, rec in deduped_by_fp.items():
            content_hash = compute_job_content_hash(
                title=rec.title,
                description=rec.description,
                required_skills=rec.required_skills,
            )
            existing = existing_map.get(fp)
            if existing is not None:
                existing.title = rec.title
                existing.company = rec.company
                existing.location = rec.location
                existing.work_mode = rec.work_mode
                existing.experience_level = rec.experience_level
                existing.employment_type = rec.employment_type
                existing.description = rec.description
                existing.requirements_summary = rec.requirements_summary
                existing.required_skills = rec.required_skills
                existing.preferred_skills = rec.preferred_skills
                existing.education_requirements = rec.education_requirements
                existing.min_years_experience = rec.min_years_experience
                existing.salary_range = rec.salary_range
                existing.external_url = rec.external_url
                existing.source_domain = rec.source_domain
                existing.posted_at = rec.posted_at or existing.posted_at
                existing.retrieved_at = now
                existing.is_active = True
                if existing.content_hash != content_hash:
                    existing.content_hash = content_hash
                    existing.embedding_vector = None
                existing.raw_metadata = rec.raw_metadata
                persisted.append(existing)
            else:
                job = Job(
                    source_provider=rec.source_provider,
                    canonical_fingerprint=fp,
                    title=rec.title,
                    company=rec.company,
                    location=rec.location,
                    work_mode=rec.work_mode,
                    experience_level=rec.experience_level,
                    employment_type=rec.employment_type,
                    description=rec.description,
                    requirements_summary=rec.requirements_summary,
                    required_skills=rec.required_skills,
                    preferred_skills=rec.preferred_skills,
                    education_requirements=rec.education_requirements,
                    min_years_experience=rec.min_years_experience,
                    salary_range=rec.salary_range,
                    external_url=rec.external_url,
                    source_domain=rec.source_domain,
                    posted_at=rec.posted_at,
                    retrieved_at=now,
                    is_active=True,
                    content_hash=content_hash,
                    raw_metadata=rec.raw_metadata,
                )
                self._session.add(job)
                persisted.append(job)

        await self._session.flush()
        return persisted

    async def search_local(
        self,
        *,
        q: str | None = None,
        location: str | None = None,
        work_mode: str | None = None,
        experience_level: str | None = None,
        skills: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Job], int]:
        stmt = select(Job).where(Job.is_active.is_(True))
        if q and q.strip():
            term = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    Job.title.ilike(term),
                    Job.company.ilike(term),
                    Job.description.ilike(term),
                )
            )
        if location and location.strip():
            loc_term = f"%{location.strip()}%"
            stmt = stmt.where(Job.location.ilike(loc_term))
        if work_mode and work_mode.strip():
            stmt = stmt.where(Job.work_mode == work_mode.strip().lower())
        if experience_level and experience_level.strip():
            stmt = stmt.where(Job.experience_level == experience_level.strip().lower())

        rows = list(
            (await self._session.scalars(stmt.order_by(Job.retrieved_at.desc()))).all()
        )
        if skills:
            wanted = {s.strip().lower() for s in skills if s.strip()}
            rows = [
                row
                for row in rows
                if wanted.intersection(
                    {rs.strip().lower() for rs in (row.required_skills + row.preferred_skills)}
                )
                or any(w in row.description.lower() for w in wanted)
            ]

        total = len(rows)
        return rows[offset : offset + limit], total

    async def list_active(self, limit: int = 50) -> list[Job]:
        rows = await self._session.scalars(
            select(Job)
            .where(Job.is_active.is_(True))
            .order_by(Job.retrieved_at.desc())
            .limit(limit)
        )
        return list(rows.all())


class SavedJobRepository:
    """Data access layer for user-scoped job bookmarks."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_saved_job_ids(self, user_id: uuid.UUID) -> set[uuid.UUID]:
        rows = await self._session.scalars(
            select(SavedJob.job_id).where(SavedJob.user_id == user_id)
        )
        return set(rows.all())

    async def save(
        self,
        *,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
        notes: str | None = None,
    ) -> SavedJob:
        existing = await self._session.scalar(
            select(SavedJob).where(SavedJob.user_id == user_id, SavedJob.job_id == job_id)
        )
        if existing is not None:
            if notes is not None:
                existing.notes = notes
                await self._session.flush()
            return existing

        saved = SavedJob(user_id=user_id, job_id=job_id, notes=notes)
        self._session.add(saved)
        await self._session.flush()
        return saved

    async def unsave(self, *, user_id: uuid.UUID, job_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(SavedJob).where(SavedJob.user_id == user_id, SavedJob.job_id == job_id)
        )
        await self._session.flush()

    async def list_saved_jobs(
        self,
        *,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Job], int]:
        total = await self._session.scalar(
            select(func.count()).select_from(SavedJob).where(SavedJob.user_id == user_id)
        )
        rows = await self._session.scalars(
            select(Job)
            .join(SavedJob, SavedJob.job_id == Job.id)
            .where(SavedJob.user_id == user_id)
            .order_by(SavedJob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows.all()), int(total or 0)
