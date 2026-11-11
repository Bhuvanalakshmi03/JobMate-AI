"""Celery application configured from centralized JobMate AI Settings."""

from __future__ import annotations

from celery import Celery

from app.core.config import get_settings


def create_celery_app() -> Celery:
    """Create and configure the Celery worker application."""
    settings = get_settings()
    celery = Celery(
        "jobmate",
        broker=settings.redis_url,
        backend=settings.redis_url,
    )
    celery.conf.update(
        timezone="UTC",
        enable_utc=True,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        broker_connection_retry_on_startup=True,
    )
    return celery


celery_app = create_celery_app()


@celery_app.task(name="jobmate.health.ping")  # type: ignore[untyped-decorator]
def ping_worker() -> str:
    """Simple diagnostic ping task for worker readiness checks."""
    return "pong"

