# CareerPilot AI — Database Schema

## Primary Database Standards
- **Engine:** External/managed PostgreSQL (SQLite restricted to unit tests).
- **Primary Keys:** UUID v4 (`sqlalchemy.Uuid(as_uuid=True)`).
- **Timestamps:** Stored in UTC (`UTCDateTime` / `TIMESTAMPTZ`). User timezone stored separately in `users.timezone`.
- **Migrations:** Managed exclusively through Alembic (`backend/app/database/migrations/`).

## Implemented Tables

### Phase 1 (`20261110_0001`)
- `audit_logs`: Immutable security and workflow event log.

### Phase 2 (`20261111_0002`)
- `users`: Registered user accounts with OAuth identity uniqueness and separate `timezone`.
- `oauth_states`: Single-use short-lived OAuth CSRF state, OIDC nonce, and PKCE verifier records.
- `user_sessions`: Revocable server-side sessions (`token_hash` unique, `revoked_at`, `expires_at`).
- `user_profiles`: Structured career profile, job preferences, and AI/notification consent flags.
- `user_skills`: Normalized per-user skills (`unique (user_id, normalized_name, category)`).

### Phase 3 (`20261111_0003`)
- `resumes`: Uploaded resume metadata, extracted text, content hash, completeness score, and analysis summary.
- `resume_facts`: Extracted facts with source section, evidence excerpt, confidence, verification status, and verification timestamp.

### Phase 4 (`20261111_0004`)
- `jobs`: Normalized discovered job postings (`id`, `source_provider`, `canonical_fingerprint` unique, `title`, `company`, `location`, `work_mode`, `experience_level`, `employment_type`, `description`, `requirements_summary`, `required_skills`, `preferred_skills`, `education_requirements`, `min_years_experience`, `salary_range`, `external_url`, `source_domain`, `posted_at`, `retrieved_at`, `is_active`, `content_hash`, cached `embedding_vector`, `raw_metadata`, `created_at`, `updated_at`).
- `saved_jobs`: User bookmarks (`id`, `user_id` FK -> `users.id`, `job_id` FK -> `jobs.id`, `notes`, `created_at`, unique `(user_id, job_id)`).
- `job_matches`: Explainable match evaluations (`id`, `user_id` FK -> `users.id`, `job_id` FK -> `jobs.id`, `algorithm_version`, `overall_score`, `factor_scores`, `weights_used`, `matching_skills`, `missing_skills`, `match_explanation`, `recommended_preparation`, `computed_at`, `created_at`, `updated_at`, unique `(user_id, job_id)`).
