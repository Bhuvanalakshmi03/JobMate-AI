"""Unit tests for centralized exception handling and safe error responses."""

from __future__ import annotations

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

from app.core.config import Settings
from app.core.exceptions import AuthorizationError, NotFoundError
from app.main import create_app


class SamplePayload(BaseModel):
    count: int


def _build_test_app(settings: Settings) -> FastAPI:
    app = create_app(settings=settings)

    @app.get("/test/not-found")
    async def trigger_not_found() -> None:
        raise NotFoundError("Resume not found")

    @app.get("/test/forbidden")
    async def trigger_forbidden() -> None:
        raise AuthorizationError()

    @app.post("/test/validate")
    async def trigger_validation(body: SamplePayload) -> dict[str, int]:
        return {"count": body.count}

    @app.get("/test/crash")
    async def trigger_crash() -> None:
        raise RuntimeError("sensitive internal db connection string password=secret")

    return app


async def test_app_error_returns_consistent_envelope(test_settings: Settings) -> None:
    app = _build_test_app(test_settings)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/test/not-found", headers={"X-Request-ID": "req-404"})

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["message"] == "Resume not found"
    assert body["error"]["request_id"] == "req-404"
    assert response.headers["X-Request-ID"] == "req-404"


async def test_validation_error_returns_422_envelope(test_settings: Settings) -> None:
    app = _build_test_app(test_settings)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/test/validate", json={"count": "not-an-int"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "REQUEST_VALIDATION_ERROR"
    assert isinstance(body["error"]["details"], list)


async def test_unhandled_exception_does_not_leak_stack_trace(test_settings: Settings) -> None:
    app = _build_test_app(test_settings)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/test/crash")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "RuntimeError" not in response.text
    assert "password=secret" not in response.text
    assert "Traceback" not in response.text

