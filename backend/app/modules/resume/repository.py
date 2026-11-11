"""Repositories for resumes and extracted resume facts with strict user isolation."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.resume.models import Resume, ResumeFact


class ResumeRepository:
    """Data access layer for Resume records scoped by user_id."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        resume_id: uuid.UUID,
        user_id: uuid.UUID,
        original_filename: str,
        storage_key: str,
        content_type: str,
        file_extension: str,
        file_size_bytes: int,
        sha256_hash: str,
        page_count: int | None,
        extracted_text: str | None,
        parse_status: str,
        error_message: str | None = None,
    ) -> Resume:
        record = Resume(
            id=resume_id,
            user_id=user_id,
            original_filename=original_filename,
            storage_key=storage_key,
            content_type=content_type,
            file_extension=file_extension,
            file_size_bytes=file_size_bytes,
            sha256_hash=sha256_hash,
            page_count=page_count,
            extracted_text=extracted_text,
            parse_status=parse_status,
            error_message=error_message,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def list_by_user(
        self,
        *,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Resume], int]:
        total_val = await self._session.scalar(
            select(func.count()).select_from(Resume).where(Resume.user_id == user_id)
        )
        rows = await self._session.scalars(
            select(Resume)
            .where(Resume.user_id == user_id)
            .order_by(Resume.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows.all()), int(total_val or 0)

    async def get_by_id_for_user(
        self,
        *,
        resume_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Resume | None:
        return await self._session.scalar(
            select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        )

    async def get_by_id(self, resume_id: uuid.UUID) -> Resume | None:
        return await self._session.scalar(select(Resume).where(Resume.id == resume_id))

    async def delete_record(self, resume: Resume) -> None:
        await self._session.delete(resume)
        await self._session.flush()


class ResumeFactRepository:
    """Data access layer for ResumeFact records scoped by resume_id and user_id."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_resume(
        self,
        *,
        resume_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[ResumeFact]:
        rows = await self._session.scalars(
            select(ResumeFact)
            .where(ResumeFact.resume_id == resume_id, ResumeFact.user_id == user_id)
            .order_by(ResumeFact.fact_type.asc(), ResumeFact.created_at.asc())
        )
        return list(rows.all())

    async def list_verified_for_resume(
        self,
        *,
        resume_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[ResumeFact]:
        rows = await self._session.scalars(
            select(ResumeFact)
            .where(
                ResumeFact.resume_id == resume_id,
                ResumeFact.user_id == user_id,
                ResumeFact.is_verified.is_(True),
            )
            .order_by(ResumeFact.fact_type.asc(), ResumeFact.created_at.asc())
        )
        return list(rows.all())

    async def replace_unverified_extracted_facts(
        self,
        *,
        resume_id: uuid.UUID,
        user_id: uuid.UUID,
        facts: list[dict[str, Any]],
    ) -> list[ResumeFact]:
        await self._session.execute(
            delete(ResumeFact).where(
                ResumeFact.resume_id == resume_id,
                ResumeFact.user_id == user_id,
            )
        )
        await self._session.flush()

        created: list[ResumeFact] = []
        for item in facts:
            fact = ResumeFact(resume_id=resume_id, user_id=user_id, **item)
            self._session.add(fact)
            created.append(fact)

        await self._session.flush()
        return created

    async def count_stats(
        self,
        *,
        resume_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> tuple[int, int]:
        total = await self._session.scalar(
            select(func.count())
            .select_from(ResumeFact)
            .where(ResumeFact.resume_id == resume_id, ResumeFact.user_id == user_id)
        )
        verified = await self._session.scalar(
            select(func.count())
            .select_from(ResumeFact)
            .where(
                ResumeFact.resume_id == resume_id,
                ResumeFact.user_id == user_id,
                ResumeFact.is_verified.is_(True),
            )
        )
        return int(total or 0), int(verified or 0)
