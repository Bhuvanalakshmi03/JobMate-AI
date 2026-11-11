"""Async SQLAlchemy engine, session factory, and health check helpers."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_db_engine(settings: Settings) -> AsyncEngine:
    """Create configured SQLAlchemy async engine with connection pooling for PostgreSQL."""
    async_url, raw_connect_args = settings.async_database_config
    connect_args = dict(raw_connect_args)
    engine_kwargs: dict[str, object] = {
        "echo": settings.db_echo,
        "pool_pre_ping": True,
    }
    if not settings.is_sqlite:
        if async_url.startswith("postgresql+asyncpg://"):
            connect_args.setdefault("timeout", 15)
            connect_args.setdefault("command_timeout", 30)
        engine_kwargs["pool_size"] = settings.db_pool_size
        engine_kwargs["max_overflow"] = settings.db_max_overflow
        engine_kwargs["pool_recycle"] = 300
        engine_kwargs["pool_timeout"] = 15
    if connect_args:
        engine_kwargs["connect_args"] = connect_args

    return create_async_engine(async_url, **engine_kwargs)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create async session factory bound to the given engine."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def check_database_health(engine: AsyncEngine) -> tuple[bool, str | None]:
    """Verify database connectivity with a lightweight SELECT 1 probe."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:
        logger.error(
            "Database readiness check failed",
            extra={"exception_class": exc.__class__.__name__},
        )
        return False, exc.__class__.__name__
