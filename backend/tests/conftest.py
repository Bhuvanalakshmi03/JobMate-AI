"""Shared Pytest fixtures for JobMate AI backend tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI

from app.core.config import Settings, clear_settings_cache
from app.main import create_app


@pytest.fixture(autouse=True)
def reset_settings_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate Settings from local .env files and clear Settings cache per test."""
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    clear_settings_cache()


@pytest.fixture
def test_db_path(tmp_path: Path) -> Path:
    """Provide an isolated temporary database file path per test."""
    return tmp_path / "test_jobmate.db"


@pytest.fixture
def test_settings(test_db_path: Path) -> Settings:
    """Provide isolated test Settings backed by a temporary SQLite database."""
    return Settings(
        app_env="testing",
        app_secret_key="test-secret-key-for-jobmate-unit-suite-123456",
        database_url=f"sqlite+aiosqlite:///{test_db_path}",
        redis_url="redis://127.0.0.1:6399/15",
        log_level="INFO",
    )


@pytest.fixture
def migrated_test_app(test_settings: Settings) -> FastAPI:
    """Run Alembic migrations against the test DB and return a configured FastAPI app."""
    backend_dir = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "app/database/migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", test_settings.sync_database_url)
    command.upgrade(alembic_cfg, "head")
    return create_app(settings=test_settings)


@pytest.fixture
async def async_client(migrated_test_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """Provide an async HTTPX client wired with FastAPI lifespan."""
    async with migrated_test_app.router.lifespan_context(migrated_test_app):
        transport = httpx.ASGITransport(app=migrated_test_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client

