# CareerPilot AI — Database Schema

## Primary Database Standards
- **Engine:** External/managed PostgreSQL (SQLite is restricted to isolated unit tests and rejected in `staging`/`production` configuration validation).
- **Primary Keys:** UUID v4 (`sqlalchemy.Uuid(as_uuid=True)`).
- **Timestamps:** Stored in UTC (`UTCDateTime` / `TIMESTAMPTZ`). User timezone is stored separately in `users.timezone`.
- **Migrations:** Managed exclusively through Alembic (`backend/app/database/migrations/`).

## Implemented Tables

### Phase 1 (`20261110_0001`)
- `audit_logs`: Immutable security and workflow event log (`id`, `user_id`, `event_type`, `resource_type`, `resource_id`, `request_id`, `ip_address`, `details`, `created_at`).

### Phase 2 (`20261111_0002`)
- `users`: Registered accounts (`id`, `email` unique, `full_name`, `avatar_url`, `oauth_provider`, `oauth_subject`, unique `(oauth_provider, oauth_subject)`, `is_active`, `timezone`, `last_login_at`, `created_at`, `updated_at`).
- `oauth_states`: Single-use short-lived OAuth state, OIDC nonce, and PKCE verifier records (`id`, `state_hash` unique, `nonce`, `code_verifier`, `redirect_to`, `expires_at`, `consumed_at`, `created_at`).
- `user_sessions`: Revocable server-side sessions (`id`, `user_id` FK -> `users.id`, `token_hash` unique, `expires_at`, `revoked_at`, `is_demo_auth`, `user_agent`, `ip_address`, `created_at`).
- `user_profiles`: Structured career profile and consent preferences (`id`, `user_id` unique FK -> `users.id`, `headline`, `summary`, `phone`, `location`, `university`, `degree`, `graduation_year`, `experience_level`, `years_of_experience`, `target_roles`, `preferred_locations`, `work_mode_preferences`, `linkedin_url`, `github_url`, `portfolio_url`, `ai_consent_given`, `notification_consent`, `profile_verified`, `extra_preferences`, `created_at`, `updated_at`).
- `user_skills`: Normalized per-user skills (`id`, `user_id` FK -> `users.id`, `name`, `normalized_name`, `category`, `proficiency`, `years_experience`, `is_verified`, `source`, unique `(user_id, normalized_name, category)`, `created_at`, `updated_at`).
