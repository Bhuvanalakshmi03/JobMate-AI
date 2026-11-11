# CareerPilot AI — API v1 Documentation

All backend routes are versioned under `/api/v1`. Protected routes require a valid session cookie (`careerpilot_session`) or `Authorization: Bearer <token>` header.

## Error Envelope
Every `4xx`/`5xx` error returns:
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Human-readable message",
    "details": null,
    "request_id": "uuid",
    "timestamp": "2026-11-11T12:00:00+00:00"
  }
}
```

## Health Endpoints (Phase 1)
- `GET /api/v1/health` — Process liveness probe.
- `GET /api/v1/health/ready` — Dependency readiness probe verifying PostgreSQL (`SELECT 1`) and Redis (`PING`). Returns `503` if PostgreSQL is unreachable.

## Authentication Endpoints (Phase 2)
- `GET /api/v1/auth/config` — Public auth capability flags (`google_oauth_enabled`, `dev_auth_enabled`).
- `GET /api/v1/auth/google` — Initiates Google OAuth 2.0 / OIDC login with PKCE S256, CSRF state, and OIDC nonce (`?mode=redirect|json`, `?redirect_to=/...`).
- `GET /api/v1/auth/google/callback` — Validates single-use OAuth state, verifies Google ID token, upserts user, creates revocable `user_sessions` record, sets HTTP-only cookie, and redirects or returns `AuthSessionResponse`.
- `POST /api/v1/auth/dev-login` — Development/testing-only login (rejected with `403` unless `APP_ENV in (development, testing)` and `DEV_AUTH_ENABLED=true`).
- `POST /api/v1/auth/logout` — Revokes active session record and clears cookie.
- `GET /api/v1/auth/me` — Returns current authenticated user profile summary.

## Profile & Skills Endpoints (Phase 2)
- `GET /api/v1/profile` — Fetch authenticated user's career profile (`404` if not yet created).
- `POST /api/v1/profile` — Create authenticated user's initial career profile (`409` if already exists).
- `PUT /api/v1/profile` — Create or update authenticated user's career profile, preferences, timezone, and consent flags.
- `GET /api/v1/profile/skills` — List authenticated user's normalized skills.
- `PUT /api/v1/profile/skills` — Atomically replace and deduplicate authenticated user's skills.
