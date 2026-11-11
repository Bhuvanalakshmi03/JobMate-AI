# CareerPilot AI — Database Schema

## Primary Database Standards
- **Engine:** External/managed PostgreSQL (SQLite is restricted to isolated unit tests and rejected in `staging`/`production` configuration validation).
- **Primary Keys:** UUID v4 (`sqlalchemy.Uuid(as_uuid=True)`).
- **Timestamps:** Stored in UTC (`UTCDateTime` / `TIMESTAMPTZ`). User timezone is stored separately in `users.timezone`.
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
- `resumes`: Uploaded resume metadata (`id`, `user_id` FK -> `users.id`, `original_filename`, `storage_key` unique, `content_type`, `file_extension`, `file_size_bytes`, `sha256_hash`, `page_count`, `extracted_text`, `parse_status`, `error_message`, `completeness_score`, `analysis_summary`, `analyzed_at`, `created_at`, `updated_at`).
- `resume_facts`: Extracted facts awaiting or holding verification (`id`, `resume_id` FK -> `resumes.id`, `user_id` FK -> `users.id`, `fact_type`, `title`, `organization`, `start_date`, `end_date`, `description`, `structured_data`, `source_section`, `evidence_excerpt`, `confidence`, `verification_status`, `is_verified`, `verified_at`, `created_at`, `updated_at`).
