"""Health and readiness API v1 routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.v1.schemas.common import HealthResponse, ReadinessResponse
from app.core.dependencies import SettingsDep
from app.services.health_service import HealthService

router = APIRouter(prefix="/health", tags=["Health"])


def get_health_service(
    request: Request,
    settings: SettingsDep,
) -> HealthService:
    """Build request-scoped HealthService from app state engine."""
    return HealthService(settings=settings, engine=request.app.state.db_engine)


HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]


@router.get(
    "",
    response_model=HealthResponse,
    summary="Liveness check",
)
async def get_health(service: HealthServiceDep) -> HealthResponse:
    """Return service liveness metadata."""
    return service.get_liveness()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Dependency readiness check",
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ReadinessResponse,
            "description": "Critical database dependency is unavailable",
        }
    },
)
async def get_readiness(
    response: Response,
    service: HealthServiceDep,
) -> ReadinessResponse:
    """Check connectivity to PostgreSQL and Redis."""
    payload, is_ready = await service.get_readiness()
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return payload

