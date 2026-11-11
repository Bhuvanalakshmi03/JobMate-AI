"""Celery background worker task for periodic due reminder dispatch."""

from __future__ import annotations

import asyncio

import app.models  # noqa: F401
from app.core.config import get_settings
from app.core.logging import get_logger
from app.database.connection import create_db_engine, create_session_factory
from app.modules.reminders.service import ReminderService
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


async def _dispatch_due_async() -> dict[str, int]:
    settings = get_settings()
    engine = create_db_engine(settings)
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            service = ReminderService(session=session)
            summary = await service.dispatch_due_reminders()
            await session.commit()
            return summary.model_dump()
    finally:
        await engine.dispose()


@celery_app.task(name="jobmate.reminders.dispatch_due")  # type: ignore[untyped-decorator]
def dispatch_due_reminders_task() -> dict[str, int]:
    """Process due reminders reliably via Celery worker."""
    logger.info("Executing due reminder worker dispatch sweep")
    return asyncio.run(_dispatch_due_async())
