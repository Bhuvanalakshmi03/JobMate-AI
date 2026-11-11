# CareerPilot AI — API v1 Documentation

All backend routes are versioned under `/api/v1`. Protected routes require a valid session cookie (`careerpilot_session`) or `Authorization: Bearer <token>` header.

## Health Endpoints (Phase 1)
- `GET /api/v1/health` — Process liveness probe.
- `GET /api/v1/health/ready` — Dependency readiness probe verifying PostgreSQL and Redis.

## Authentication Endpoints (Phase 2)
- `GET /api/v1/auth/config` — Public auth capability flags (`google_oauth_enabled`, `dev_auth_enabled`).
- `GET /api/v1/auth/google` — Initiates Google OAuth 2.0 / OIDC login with PKCE S256, state, and nonce.
- `GET /api/v1/auth/google/callback` — Verifies OAuth callback, issues revocable session, and sets HTTP-only cookie.
- `POST /api/v1/auth/dev-login` — Development/testing-only login (rejected with `403` unless `DEV_AUTH_ENABLED=true` in `development`/`testing`).
- `POST /api/v1/auth/logout` — Revokes active session record and clears cookie.
- `GET /api/v1/auth/me` — Returns current authenticated user metadata.

## Profile & Skills Endpoints (Phase 2)
- `GET /api/v1/profile` — Fetch authenticated user's career profile (`404` if not created).
- `POST /api/v1/profile` — Create authenticated user's initial career profile (`409` if already exists).
- `PUT /api/v1/profile` — Create or update career profile, preferences, timezone, and consent flags.
- `GET /api/v1/profile/skills` — List authenticated user's normalized skills.
- `PUT /api/v1/profile/skills` — Atomically replace and deduplicate authenticated user's skills.

## Resume Intelligence Endpoints (Phase 3)
- `POST /api/v1/resumes/upload` — Validate file signature, size, and pages, store privately, and extract text (`201 Created`).
- `GET /api/v1/resumes` — List uploaded resumes owned by the authenticated user.
- `GET /api/v1/resumes/{resume_id}` — Fetch resume details, parsed text, and fact counts.
- `POST /api/v1/resumes/{resume_id}/analyze` — Run AI extraction and analysis (caches unchanged analyzed resumes unless `?force=true`; supports `?async_mode=true` via Celery).
- `GET /api/v1/resumes/{resume_id}/analysis` — Retrieve analysis summary and extracted facts for review.
- `PATCH /api/v1/resumes/{resume_id}/facts` — Verify, edit, or reject extracted facts and optionally sync verified facts to `user_profiles` and `user_skills`.
- `DELETE /api/v1/resumes/{resume_id}` — Delete resume metadata, facts, and stored file.
