"""Centralized environment configuration and validation."""

from __future__ import annotations

import json
import ssl
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

AppEnvironment = Literal["development", "testing", "staging", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

_INSECURE_SECRET_MARKERS = (
    "change-me",
    "secret",
    "dev-secret",
    "placeholder",
    "example",
)

ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Typed, validated application configuration sourced from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(str(ROOT_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    app_name: str = Field(default="JobMate AI", min_length=1)
    app_version: str = Field(default="0.1.0", min_length=1)
    app_env: AppEnvironment = "development"
    app_secret_key: str = Field(
        default="change-me-in-local-dev-only-minimum-32-chars",
        min_length=16,
    )
    debug: bool = False

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://careerpilot:careerpilot@localhost:5432/careerpilot",
        min_length=1,
    )
    db_pool_size: int = Field(default=10, ge=1, le=100)
    db_max_overflow: int = Field(default=20, ge=0, le=100)
    db_echo: bool = False

    # Redis / Worker
    redis_url: str = Field(default="redis://localhost:6379/0", min_length=1)

    # LLM Provider Switch ("openai" | "claude")
    llm_mode: Literal["openai", "claude"] = "openai"

    # OpenAI (LLM intelligence, embeddings, and web-search job discovery)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_timeout_seconds: int = Field(default=90, ge=1, le=300)
    openai_max_tokens: int = Field(default=4096, ge=128, le=32768)

    # Anthropic Claude (alternative LLM intelligence, tool calling, JSON, and web search)
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-5-5"
    claude_timeout_seconds: int = Field(default=120, ge=1, le=300)
    claude_max_tokens: int = Field(default=16384, ge=128, le=65536)
    enable_hybrid_openai_embeddings: bool = False

    # Google OAuth 2.0 / OIDC
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    # Session & Auth
    session_ttl_seconds: int = Field(default=604800, ge=300, le=2592000)
    oauth_state_ttl_seconds: int = Field(default=600, ge=60, le=3600)
    session_cookie_name: str = Field(default="jobmate_session", min_length=1)
    session_cookie_secure: bool = False
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    session_cookie_domain: str | None = None
    dev_auth_enabled: bool = False

    # ChromaDB
    chroma_url: str = "http://localhost:8001"
    chroma_api_key: str = ""
    chroma_tenant: str = "default_tenant"
    chroma_database: str = "default_database"

    # Storage
    storage_provider: Literal["local", "s3"] = "local"
    storage_bucket: str = ""
    local_storage_path: str = "./storage"
    max_resume_size_bytes: int = Field(default=5 * 1024 * 1024, ge=1024, le=25 * 1024 * 1024)
    max_resume_pages: int = Field(default=15, ge=1, le=50)

    # Frontend & CORS
    frontend_url: str = "http://localhost:5173"
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    # Monitoring & Timeouts
    log_level: LogLevel = "INFO"
    request_timeout_seconds: int = Field(default=30, ge=1, le=300)

    @field_validator("llm_mode", mode="before")
    @classmethod
    def normalize_llm_mode(cls, value: object) -> str:
        """Normalize LLM_MODE before Literal validation."""
        if isinstance(value, str):
            return value.strip().lower()
        raise ValueError("LLM_MODE must be 'openai' or 'claude'")

    @field_validator("session_cookie_domain", mode="before")
    @classmethod
    def normalize_cookie_domain(cls, value: object) -> str | None:
        """Convert blank SESSION_COOKIE_DOMAIN values to None for host-only cookies."""
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: object) -> str:
        """Normalize log level to uppercase before Literal validation."""
        if isinstance(value, str):
            return value.strip().upper()
        raise ValueError("LOG_LEVEL must be a string")

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        """Accept either comma-separated strings or JSON arrays for CORS origins."""
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            return [item.strip() for item in stripped.split(",") if item.strip()]
        raise ValueError("CORS_ALLOWED_ORIGINS must be a comma-separated string or list")

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        """Ensure DATABASE_URL uses a supported SQLAlchemy database scheme."""
        allowed_prefixes = (
            "postgres://",
            "postgresql://",
            "postgresql+asyncpg://",
            "postgresql+psycopg://",
            "postgresql+psycopg2://",
            "sqlite://",
            "sqlite+aiosqlite://",
        )
        if not value.startswith(allowed_prefixes):
            raise ValueError(
                "DATABASE_URL must start with a supported PostgreSQL or SQLite SQLAlchemy scheme"
            )
        return value

    @model_validator(mode="after")
    def validate_environment_security(self) -> Settings:
        """Enforce stricter invariants in staging and production environments."""
        if self.app_env in ("staging", "production"):
            lowered_secret = self.app_secret_key.lower()
            if len(self.app_secret_key) < 32 or any(
                marker in lowered_secret for marker in _INSECURE_SECRET_MARKERS
            ):
                raise ValueError(
                    "APP_SECRET_KEY must be at least 32 characters and non-default "
                    f"in {self.app_env}"
                )
            if self.database_url.startswith("sqlite"):
                raise ValueError(f"SQLite is not permitted in {self.app_env}; use PostgreSQL")
            if self.dev_auth_enabled:
                raise ValueError(f"DEV_AUTH_ENABLED must be false in {self.app_env}")
        if self.app_env == "production" and self.debug:
            raise ValueError("DEBUG must be false in production")
        return self

    @property
    def async_database_config(self) -> tuple[str, dict[str, Any]]:
        """Return async SQLAlchemy URL and driver connect_args normalized for asyncpg/aiosqlite."""
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql+psycopg2://"):
            url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)

        if not url.startswith("postgresql+asyncpg://"):
            return url, {}

        parsed = urlparse(url)
        query_items = parse_qsl(parsed.query, keep_blank_values=True)
        filtered_query: list[tuple[str, str]] = []
        connect_args: dict[str, Any] = {}

        for key, val in query_items:
            lowered = key.lower()
            if lowered == "sslmode":
                mode = val.lower()
                if mode in ("verify-ca", "verify-full"):
                    connect_args["ssl"] = ssl.create_default_context()
                elif mode in ("require", "prefer", "allow"):
                    connect_args["ssl"] = "require"
                elif mode == "disable":
                    connect_args["ssl"] = False
            elif lowered == "channel_binding":
                continue
            else:
                filtered_query.append((key, val))

        normalized_url = urlunparse(parsed._replace(query=urlencode(filtered_query)))
        return normalized_url, connect_args

    @property
    def sync_database_url(self) -> str:
        """Return synchronous SQLAlchemy URL for Alembic migrations."""
        url = self.database_url
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg2://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg2://", 1)
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        if url.startswith("sqlite+aiosqlite://"):
            return url.replace("sqlite+aiosqlite://", "sqlite://", 1)
        return url

    @property
    def is_sqlite(self) -> bool:
        """Whether the configured database backend is SQLite (testing/local unit runs only)."""
        return self.database_url.startswith("sqlite")

    @property
    def google_oauth_configured(self) -> bool:
        """Whether Google OAuth client credentials are configured."""
        return bool(self.google_client_id.strip() and self.google_client_secret.strip())

    @property
    def is_claude_mode(self) -> bool:
        """Whether LLM_MODE selects Anthropic Claude as the primary LLM provider."""
        return self.llm_mode == "claude"

    @property
    def active_llm_api_key(self) -> str:
        """Return API key for the active LLM_MODE provider."""
        if self.is_claude_mode:
            return self.anthropic_api_key.strip()
        return self.openai_api_key.strip()

    @property
    def active_llm_model(self) -> str:
        """Return primary chat/tool model configured for active LLM_MODE."""
        return self.claude_model if self.is_claude_mode else self.openai_model

    @property
    def active_llm_max_tokens(self) -> int:
        """Return configured max tokens budget for active LLM_MODE."""
        return self.claude_max_tokens if self.is_claude_mode else self.openai_max_tokens

    @property
    def ai_llm_configured(self) -> bool:
        """Whether the selected primary LLM provider has an API key configured."""
        return bool(self.active_llm_api_key)

    @property
    def embeddings_configured(self) -> bool:
        """Whether dense vector embeddings (OpenAI) are enabled and configured."""
        return bool(self.openai_api_key.strip()) and (
            not self.is_claude_mode or self.enable_hybrid_openai_embeddings
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached validated Settings instance."""
    return Settings()


def clear_settings_cache() -> None:
    """Clear cached Settings instance (intended for isolated test suites)."""
    get_settings.cache_clear()
