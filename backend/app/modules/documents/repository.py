"""Repository for versioned generated documents scoped by authenticated user."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.documents.models import GeneratedDocument


class DocumentRepository:
    """Data access layer for GeneratedDocument records scoped by user_id."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        job_id: uuid.UUID | None,
        source_resume_id: uuid.UUID | None,
        document_type: str,
        title: str,
        version_group_id: uuid.UUID,
        version: int,
        content_markdown: str,
        structured_content: dict[str, Any] | None,
        factuality_report: dict[str, Any],
        is_user_edited: bool,
        model_used: str | None,
        tokens_used: int | None,
    ) -> GeneratedDocument:
        doc = GeneratedDocument(
            user_id=user_id,
            job_id=job_id,
            source_resume_id=source_resume_id,
            document_type=document_type,
            title=title,
            version_group_id=version_group_id,
            version=version,
            content_markdown=content_markdown,
            structured_content=structured_content,
            factuality_report=factuality_report,
            is_user_edited=is_user_edited,
            model_used=model_used,
            tokens_used=tokens_used,
        )
        self._session.add(doc)
        await self._session.flush()
        return doc

    async def get_by_id_for_user(
        self,
        *,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> GeneratedDocument | None:
        return await self._session.scalar(
            select(GeneratedDocument).where(
                GeneratedDocument.id == document_id,
                GeneratedDocument.user_id == user_id,
            )
        )

    async def list_versions(
        self,
        *,
        version_group_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[GeneratedDocument]:
        rows = await self._session.scalars(
            select(GeneratedDocument)
            .where(
                GeneratedDocument.version_group_id == version_group_id,
                GeneratedDocument.user_id == user_id,
            )
            .order_by(GeneratedDocument.version.desc())
        )
        return list(rows.all())

    async def get_latest_version_number(
        self,
        *,
        version_group_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> int:
        val = await self._session.scalar(
            select(func.max(GeneratedDocument.version)).where(
                GeneratedDocument.version_group_id == version_group_id,
                GeneratedDocument.user_id == user_id,
            )
        )
        return int(val or 0)

    async def list_for_user(
        self,
        *,
        user_id: uuid.UUID,
        job_id: uuid.UUID | None = None,
        document_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[GeneratedDocument], int]:
        stmt = select(GeneratedDocument).where(GeneratedDocument.user_id == user_id)
        count_stmt = (
            select(func.count())
            .select_from(GeneratedDocument)
            .where(GeneratedDocument.user_id == user_id)
        )
        if job_id is not None:
            stmt = stmt.where(GeneratedDocument.job_id == job_id)
            count_stmt = count_stmt.where(GeneratedDocument.job_id == job_id)
        if document_type:
            stmt = stmt.where(GeneratedDocument.document_type == document_type)
            count_stmt = count_stmt.where(GeneratedDocument.document_type == document_type)

        total = await self._session.scalar(count_stmt)
        rows = await self._session.scalars(
            stmt.order_by(GeneratedDocument.created_at.desc()).limit(limit).offset(offset)
        )
        return list(rows.all()), int(total or 0)
