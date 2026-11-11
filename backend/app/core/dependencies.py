"""Shared FastAPI dependency providers."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings


def get_app_settings() -> Settings:
    """Return validated application settings."""
    return get_settings()


def get_request_id(request: Request) -> str | None:
    """Extract request correlation ID bound by RequestContextMiddleware."""
    return getattr(request.state, "request_id", None)


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Provide a request-scoped database session from app state."""
    session_factory = request.app.state.db_session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]

