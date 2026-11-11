# CareerPilot AI — Architecture Overview

## Pattern
CareerPilot AI uses a **Modular Monolithic Architecture** (`backend/app/`) paired with a **Feature-Modular React Frontend** (`frontend/src/`).

## Backend Layer Boundaries

### Core & Database Infrastructure (Phase 1)
- `app/main.py`: FastAPI application factory (`create_app`), CORS configuration, middleware registration, exception handler wiring, and engine lifespan management.
- `app/core/`:
  - `config.py`: Validated Pydantic Settings (`Settings`, `get_settings`) normalizing cloud PostgreSQL SSL URLs (`async_database_config`, `sync_database_url`), external Redis/ChromaDB settings, upload bounds, and `staging`/`production` security invariants.
  - `logging.py`: Structured JSON logging (`StructuredJsonFormatter`) with `contextvars` correlation (`request_id`, `workflow_id`, `user_id`) and recursive redaction (`sanitize_log_value`).
  - `exceptions.py`: Typed `AppError` hierarchy and centralized FastAPI error handlers producing consistent `ErrorResponse` payloads without stack trace leakage.
  - `security.py`: SHA-256 token hashing, PKCE S256 generation, and HS256 JWT session issuance/validation.
  - `dependencies.py`: Shared FastAPI dependency providers (`get_app_settings`, `get_db_session`, `get_request_id`).
- `app/database/`: Async SQLAlchemy 2.0 engine, `UTCDateTime`/`UUIDPrimaryKeyMixin` mixins, and Alembic migrations.
- `app/observability/middleware.py`: `RequestContextMiddleware` propagating `X-Request-ID`, adding baseline security headers, and logging latency.

### Domain Modules & Integrations (Phases 2–3)
- `app/integrations/oauth/google.py`: Google OAuth 2.0 / OIDC adapter (`GoogleOAuthClient`) behind `OAuthProviderProtocol`.
- `app/integrations/storage/local.py`: Private non-overwriting file storage (`LocalPrivateStorage`) behind `StorageBackendProtocol` with path-traversal protection.
- `app/integrations/document_parser/extractor.py`: PDF/DOCX signature validation, zip-bomb bounds, and text extraction using PyMuPDF and `python-docx`.
- `app/integrations/openai/client.py`: Centralized OpenAI chat client (`OpenAIChatClient`) behind `LLMClientProtocol` enforcing configured model, token limits, timeouts, and bounded retries.
- `app/modules/authentication/`: `User`, `UserSession`, `OAuthState`, `AuthService`, and `/api/v1/auth/*` routes.
- `app/modules/profile/`: `UserProfile`, `UserSkill`, `ProfileService`, and `/api/v1/profile/*` routes.
- `app/modules/resume/`: Separated `models.py`, `schemas.py`, `repository.py`, `parser.py`, `extractor.py`, `validator.py`, `tasks.py`, `service.py`, and `/api/v1/resumes/*` routes.
- `app/repositories/audit_repository.py`: Shared immutable audit logging repository.

## Frontend Layer Boundaries
- `src/services/`: Centralized `api-client.ts`, `health-service.ts`, `auth-service.ts`, `profile-service.ts`, `resume-service.ts`.
- `src/features/authentication/`: `AuthProvider`/`useAuth`, `ProtectedRoute`, and `LoginPage`.
- `src/features/profile/`: `ProfilePage`, `SkillsManager`, and TanStack Query profile/skills hooks.
- `src/features/resume/`: `ResumesPage`, `ResumeAnalysisPage`, `ResumeFactCard`, and TanStack Query resume hooks.
- `src/features/dashboard/`: `FoundationStatusPage` wired to `/api/v1/health` and `/api/v1/health/ready`.
