"""Unit tests for centralized configuration and startup validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.config import Settings


def test_settings_defaults_valid_in_development() -> None:
    settings = Settings(app_env="development")
    assert settings.app_name == "CareerPilot AI"
    assert settings.sync_database_url.startswith("postgresql+psycopg2://")
    assert settings.cors_allowed_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_settings_parses_comma_and_json_cors_origins() -> None:
    csv_settings = Settings(
        cors_allowed_origins="https://app.careerpilot.ai, https://staging.careerpilot.ai"
    )
    assert csv_settings.cors_allowed_origins == [
        "https://app.careerpilot.ai",
        "https://staging.careerpilot.ai",
    ]

    json_settings = Settings(cors_allowed_origins='["https://one.test", "https://two.test"]')
    assert json_settings.cors_allowed_origins == ["https://one.test", "https://two.test"]


def test_settings_rejects_default_secret_in_production() -> None:
    with pytest.raises(PydanticValidationError, match="APP_SECRET_KEY"):
        Settings(
            app_env="production",
            app_secret_key="change-me-in-local-dev-only-minimum-32-chars",
            database_url="postgresql+asyncpg://user:pass@db:5432/careerpilot",
            debug=False,
        )


def test_settings_rejects_debug_mode_in_production() -> None:
    with pytest.raises(PydanticValidationError, match="DEBUG must be false"):
        Settings(
            app_env="production",
            app_secret_key="a-very-strong-random-production-signing-key-987654",
            database_url="postgresql+asyncpg://user:pass@db:5432/careerpilot",
            debug=True,
        )


def test_settings_rejects_sqlite_in_production() -> None:
    with pytest.raises(PydanticValidationError, match="SQLite is not permitted"):
        Settings(
            app_env="production",
            app_secret_key="a-very-strong-random-production-signing-key-987654",
            database_url="sqlite+aiosqlite:///./prod.db",
            debug=False,
        )


def test_settings_rejects_unsupported_database_scheme() -> None:
    with pytest.raises(PydanticValidationError, match="DATABASE_URL"):
        Settings(database_url="mysql://user:pass@localhost/careerpilot")


def test_settings_normalizes_cloud_postgres_ssl_urls() -> None:
    settings = Settings(
        database_url="postgres://user:pass@ep-cool.neon.tech:5432/careerpilot?sslmode=require&channel_binding=require"
    )
    async_url, connect_args = settings.async_database_config
    assert async_url == "postgresql+asyncpg://user:pass@ep-cool.neon.tech:5432/careerpilot"
    assert connect_args == {"ssl": "require"}
    assert (
        settings.sync_database_url
        == "postgresql+psycopg2://user:pass@ep-cool.neon.tech:5432/careerpilot?sslmode=require&channel_binding=require"
    )


def test_settings_rejects_dev_auth_in_production() -> None:
    with pytest.raises(PydanticValidationError, match="DEV_AUTH_ENABLED"):
        Settings(
            app_env="production",
            app_secret_key="a-very-strong-random-production-signing-key-987654",
            database_url="postgresql+asyncpg://user:pass@db:5432/careerpilot",
            debug=False,
            dev_auth_enabled=True,
        )

