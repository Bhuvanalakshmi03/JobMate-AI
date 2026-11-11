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

### Phase 6 (`20261111_0006`)
- `applications`: Tracked student job applications (`id`, `user_id` FK -> `users.id`, `job_id` FK -> `jobs.id` nullable ondelete `SET NULL`, `tailored_resume_id` FK -> `generated_documents.id`, `cover_letter_id` FK -> `generated_documents.id`, `company_name`, `role_title`, `job_url`, `location`, `status`, `applied_at`, `deadline_at`, `follow_up_at`, `notes`, `created_at`, `updated_at`, unique `uq_applications_user_job` on `(user_id, job_id)`, indexes `ix_applications_user_status` and `ix_applications_user_deadline`).
- `application_history`: Immutable status transition timeline (`id`, `application_id` FK -> `applications.id`, `user_id` FK -> `users.id`, `from_status`, `to_status`, `note`, `changed_at`, index `ix_app_history_app_changed`).

### Phase 7 (`20261111_0007`)
- `workflow_runs`: Durable LangGraph workflow checkpoints and telemetry (`id`, `user_id` FK -> `users.id`, `job_id` FK -> `jobs.id`, `application_id` FK -> `applications.id`, `task_type`, `user_request`, `current_stage`, `status`, `state_snapshot`, `agent_outputs`, `validation_results`, `pending_approval_id`, `execution_trace`, `total_tokens_used`, `error_detail`, `created_at`, `updated_at`, index `ix_workflow_runs_user_status`).
- `approvals`: Pending and decided human approval records (`id`, `user_id` FK -> `users.id`, `workflow_run_id` FK -> `workflow_runs.id`, `application_id` FK -> `applications.id`, `action_type`, `target_destination`, `title`, `payload`, `status`, `decision_note`, `decided_at`, `executed_at`, `execution_result`, `created_at`, `updated_at`, indexes `ix_approvals_user_status`, `ix_approvals_workflow_run`).
