"""Celery background tasks for asynchronous resume analysis."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.database.connection import create_db_engine, create_session_factory
from app.integrations.openai.client import OpenAIChatClient
from app.integrations.storage.local import LocalPrivateStorage
from app.modules.authentication.repository import UserRepository
from app.modules.resume.extractor import ResumeAnalystExtractor
from app.modules.resume.parser import ResumeParser
from app.modules.resume.service import ResumeService
from app.modules.resume.validator import ResumeExtractionValidator
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


async def _run_resume_analysis_async(
    *,
    resume_id_str: str,
    user_id_str: str,
    force: bool,
) -> dict[str, Any]:
    settings = get_settings()
    engine = create_db_engine(settings)
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            user = await UserRepository(session).get_by_id(uuid.UUID(user_id_str))
            if user is None:
                return {"status": "failed", "detail": "User not found"}

            service = ResumeService(
                session=session,
                settings=settings,
                storage=LocalPrivateStorage(settings.local_storage_path),
                parser=ResumeParser(settings),
                extractor=ResumeAnalystExtractor(OpenAIChatClient(settings)),
                validator=ResumeExtractionValidator(),
            )
            result = await service.analyze_resume(
                user=user,
                resume_id=uuid.UUID(resume_id_str),
                force=force,
            )
            await session.commit()
            return {
                "status": "completed",
                "resume_id": str(result.resume.id),
                "fact_count": len(result.facts),
            }
    finally:
        await engine.dispose()


@celery_app.task(name="jobmate.resume.analyze")  # type: ignore[untyped-decorator]
def analyze_resume_task(
    resume_id_str: str,
    user_id_str: str,
    force: bool = False,
) -> dict[str, Any]:
    """Execute resume AI extraction and analysis in a background worker."""
    logger.info(
        "Running background resume analysis task",
        extra={"resume_id": resume_id_str, "user_id": user_id_str},
    )
    return asyncio.run(
        _run_resume_analysis_async(
            resume_id_str=resume_id_str,
            user_id_str=user_id_str,
            force=force,
        )
    )
