"""FastAPI application factory and lifecycle initialization."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.routers import api_v1_router
from app.core.config import Settings, get_settings
from app.core.dependencies import get_app_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.database.connection import create_db_engine, create_session_factory
from app.observability.middleware import RequestContextMiddleware

logger = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the JobMate AI FastAPI application."""
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        engine = create_db_engine(resolved_settings)
        application.state.settings = resolved_settings
        application.state.db_engine = engine
        application.state.db_session_factory = create_session_factory(engine)
        if not resolved_settings.is_sqlite:
            try:
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
            except Exception as exc:
                logger.warning(
                    "Database connection warmup probe failed",
                    extra={"exception_class": exc.__class__.__name__},
                )
        logger.info(
            "JobMate AI backend started",
            extra={
                "app_env": resolved_settings.app_env,
                "version": resolved_settings.app_version,
            },
        )
        try:
            yield
        finally:
            await engine.dispose()
            logger.info("JobMate AI backend stopped")

    application = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        docs_url="/api/docs" if resolved_settings.app_env != "production" else None,
        redoc_url="/api/redoc" if resolved_settings.app_env != "production" else None,
        openapi_url="/api/openapi.json" if resolved_settings.app_env != "production" else None,
        lifespan=lifespan,
    )

    if settings is not None:
        application.dependency_overrides[get_app_settings] = lambda: resolved_settings

    cors_origins = list(resolved_settings.cors_allowed_origins)
    for required_origin in (
        resolved_settings.frontend_url.strip().rstrip("/"),
        "https://jobmate.techcreed.in",
    ):
        if required_origin and required_origin not in cors_origins:
            cors_origins.append(required_origin)

    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Idempotency-Key"],
    )

    register_exception_handlers(application)
    application.include_router(api_v1_router)

    return application


app = create_app()

