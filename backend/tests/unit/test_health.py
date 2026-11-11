"""Unit tests for v1 health and readiness endpoints."""

from __future__ import annotations

import httpx
import pytest


async def test_liveness_endpoint_returns_ok(async_client: httpx.AsyncClient) -> None:
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "CareerPilot AI"
    assert data["environment"] == "testing"
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"


async def test_readiness_reports_healthy_db_and_unavailable_redis(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_redis_check(_url: str, timeout_seconds: float = 1.0) -> tuple[bool, str | None]:
        return False, "ConnectionError"

    monkeypatch.setattr("app.services.health_service.check_redis_health", fake_redis_check)

    response = await async_client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["dependencies"]["database"]["status"] == "healthy"
    assert data["dependencies"]["redis"]["status"] == "unavailable"


async def test_readiness_reports_ready_when_all_dependencies_healthy(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_redis_ok(_url: str, timeout_seconds: float = 1.0) -> tuple[bool, str | None]:
        return True, None

    monkeypatch.setattr("app.services.health_service.check_redis_health", fake_redis_ok)

    response = await async_client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["dependencies"]["database"]["status"] == "healthy"
    assert data["dependencies"]["redis"]["status"] == "healthy"


async def test_readiness_returns_503_when_database_fails(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_db_fail(_engine: object) -> tuple[bool, str | None]:
        return False, "OperationalError"

    async def fake_redis_ok(_url: str, timeout_seconds: float = 1.0) -> tuple[bool, str | None]:
        return True, None

    monkeypatch.setattr("app.services.health_service.check_database_health", fake_db_fail)
    monkeypatch.setattr("app.services.health_service.check_redis_health", fake_redis_ok)

    response = await async_client.get("/api/v1/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unavailable"
    assert data["dependencies"]["database"]["status"] == "unhealthy"
    assert data["dependencies"]["database"]["detail"] == "OperationalError"

