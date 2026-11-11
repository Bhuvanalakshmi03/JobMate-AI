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
- `users`, `oauth_states`, `user_sessions`, `user_profiles`, `user_skills`.

### Phase 3 (`20261111_0003`)
- `resumes`, `resume_facts`.

### Phase 4 (`20261111_0004`)
- `jobs`, `saved_jobs`, `job_matches`.

### Phase 5 (`20261111_0005`)
- `generated_documents`: Versioned tailored resumes, cover letters, and application notes (`id`, `user_id` FK -> `users.id`, `job_id` FK -> `jobs.id`, `source_resume_id` FK -> `resumes.id`, `document_type`, `title`, `version_group_id`, `version`, `content_markdown`, `structured_content`, `factuality_report`, `is_user_edited`, `model_used`, `tokens_used`, `created_at`, `updated_at`, unique `(version_group_id, version)`).
