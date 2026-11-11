"""Health and readiness probe service separating infrastructure checks from routers."""

from __future__ import annotations

from datetime import UTC, datetime

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.v1.schemas.common import DependencyStatus, HealthResponse, ReadinessResponse
from app.core.config import Settings
from app.core.logging import get_logger
from app.database.connection import check_database_health

logger = get_logger(__name__)


async def check_redis_health(
    redis_url: str,
    timeout_seconds: float = 1.0,
) -> tuple[bool, str | None]:
    """Verify Redis connectivity with a bounded PING timeout."""
    client: aioredis.Redis | None = None
    try:
        client = aioredis.from_url(
            redis_url,
            socket_connect_timeout=timeout_seconds,
            socket_timeout=timeout_seconds,
        )
        pong = await client.ping()
        return bool(pong), None
    except Exception as exc:
        logger.warning(
            "Redis readiness check unavailable",
            extra={"exception_class": exc.__class__.__name__},
        )
        return False, exc.__class__.__name__
    finally:
        if client is not None:
            await client.aclose()


class HealthService:
    """Computes liveness and dependency readiness statuses."""

    def __init__(self, settings: Settings, engine: AsyncEngine) -> None:
        self._settings = settings
        self._engine = engine

    def get_liveness(self) -> HealthResponse:
        """Return immediate process liveness metadata."""
        return HealthResponse(
            status="ok",
            service=self._settings.app_name,
            version=self._settings.app_version,
            environment=self._settings.app_env,
            timestamp=datetime.now(UTC),
        )

    async def get_readiness(self) -> tuple[ReadinessResponse, bool]:
        """Probe PostgreSQL (critical) and Redis (background/cache) dependencies."""
        db_ok, db_err = await check_database_health(self._engine)
        redis_ok, redis_err = await check_redis_health(self._settings.redis_url)

        dependencies = {
            "database": DependencyStatus(
                status="healthy" if db_ok else "unhealthy",
                detail=db_err,
            ),
            "redis": DependencyStatus(
                status="healthy" if redis_ok else "unavailable",
                detail=redis_err,
            ),
        }

        if not db_ok:
            overall_status = "unavailable"
        elif not redis_ok:
            overall_status = "degraded"
        else:
            overall_status = "ready"

        payload = ReadinessResponse(
            status=overall_status,
            service=self._settings.app_name,
            version=self._settings.app_version,
            environment=self._settings.app_env,
            timestamp=datetime.now(UTC),
            dependencies=dependencies,
        )
        return payload, db_ok

