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
- `GET /api/v1/profile`, `POST /api/v1/profile`, `PUT /api/v1/profile` — Career profile CRUD and preferences.
- `GET /api/v1/profile/skills`, `PUT /api/v1/profile/skills` — Normalized skills management.

## Resume Intelligence Endpoints (Phase 3)
- `POST /api/v1/resumes/upload`, `GET /api/v1/resumes`, `GET /api/v1/resumes/{resume_id}`, `POST /api/v1/resumes/{resume_id}/analyze`, `GET /api/v1/resumes/{resume_id}/analysis`, `PATCH /api/v1/resumes/{resume_id}/facts`, `DELETE /api/v1/resumes/{resume_id}`.

## Job Discovery & Matching Endpoints (Phase 4)
- `GET /api/v1/jobs/search` — Search cached/persisted jobs or run live OpenAI Web Search discovery (`q`, `location`, `work_mode`, `experience_level`, `skills`, `refresh`, `limit`, `offset`).
- `GET /api/v1/jobs/recommended` — Rank active jobs using explainable weighted + semantic matching.
- `GET /api/v1/jobs/saved` — List saved jobs for authenticated user.
- `GET /api/v1/jobs/{job_id}` — Fetch full normalized job details, saved state, and match preview.
- `POST /api/v1/jobs/{job_id}/match` — Compute and persist factor-by-factor explainable match score.
- `POST /api/v1/jobs/{job_id}/save` — Bookmark a job for the authenticated user.
- `DELETE /api/v1/jobs/{job_id}/save` — Remove a saved job bookmark.
