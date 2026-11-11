# CareerPilot AI — Architecture Overview

## Pattern
CareerPilot AI uses a **Modular Monolithic Architecture** (`backend/app/`) paired with a **Feature-Modular React Frontend** (`frontend/src/`).

## Backend Layer Boundaries

### Core & Database Infrastructure (Phase 1)
- `app/main.py`: FastAPI application factory (`create_app`), CORS configuration, middleware registration, exception handler wiring, and engine lifespan management.
- `app/core/`:
  - `config.py`: Validated Pydantic Settings (`Settings`, `get_settings`) normalizing cloud PostgreSQL SSL URLs (`async_database_config`, `sync_database_url`), external Redis/ChromaDB settings, and `staging`/`production` security invariants.
  - `logging.py`: Structured JSON logging (`StructuredJsonFormatter`) with `contextvars` correlation (`request_id`, `workflow_id`, `user_id`) and recursive redaction (`sanitize_log_value`).
  - `exceptions.py`: Typed `AppError` hierarchy and centralized FastAPI error handlers producing consistent `ErrorResponse` payloads without stack trace leakage.
  - `security.py`: SHA-256 token hashing, PKCE S256 generation, and HS256 JWT session issuance/validation.
  - `dependencies.py`: Shared FastAPI dependency providers (`get_app_settings`, `get_db_session`, `get_request_id`).
- `app/database/`: Async SQLAlchemy 2.0 engine, `UTCDateTime`/`UUIDPrimaryKeyMixin` mixins, and Alembic migrations.
- `app/observability/middleware.py`: `RequestContextMiddleware` propagating `X-Request-ID`, adding baseline security headers, and logging latency.

### Domain Modules & Integrations (Phase 2)
- `app/integrations/oauth/google.py`: Google OAuth 2.0 / OIDC adapter (`GoogleOAuthClient`) behind `OAuthProviderProtocol`, validating authorization code exchange, issuer, audience, `email_verified`, and OIDC `nonce`.
- `app/modules/authentication/`:
  - Models (`User`, `UserSession`, `OAuthState`), repositories, `AuthService`, request auth dependencies (`CurrentAuthDep`, `CurrentUserDep`), and `/api/v1/auth/*` routes.
- `app/modules/profile/`:
  - Models (`UserProfile`, `UserSkill`), user-scoped repositories, `ProfileService`, and `/api/v1/profile/*` routes.
- `app/repositories/audit_repository.py`: Shared immutable audit logging repository.

## Frontend Layer Boundaries
- `src/services/`: Centralized `api-client.ts`, `health-service.ts`, `auth-service.ts`, `profile-service.ts`.
- `src/features/authentication/`: `AuthProvider`/`useAuth`, `ProtectedRoute`, and `LoginPage` (Google OAuth + dev-flagged sign-in).
- `src/features/profile/`: `ProfilePage`, `SkillsManager`, and TanStack Query profile/skills hooks.
- `src/features/dashboard/`: `FoundationStatusPage` wired to `/api/v1/health` and `/api/v1/health/ready`.
