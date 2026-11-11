# JobMate AI — Database Schema

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

### Phase 7+ — Google Calendar & Session-Managed Co-Pilot Chat (`20261111_0008`)
- `oauth_states` extensions: Added `flow_type` (`"login"` | `"calendar_connect"`) and nullable `user_id` (FK -> `users.id`) for incremental OAuth consent reuse.
- `google_calendar_connections`: Per-user encrypted OAuth credentials (`id`, `user_id` FK -> `users.id` unique, `google_email`, `scopes`, `encrypted_access_token`, `encrypted_refresh_token`, `token_expires_at`, `created_at`, `updated_at`).
- `copilot_conversations`: Persistent Co-Pilot chat sessions (`id`, `user_id` FK -> `users.id`, `title`, `is_archived`, `last_message_at`, `created_at`, `updated_at`, index `ix_copilot_conversations_user_recent`).
- `copilot_messages`: Multi-turn conversation log (`id`, `conversation_id` FK -> `copilot_conversations.id`, `user_id` FK -> `users.id`, `role`, `content`, `tool_calls`, `approval_ids`, `tokens_used`, `created_at`, index `ix_copilot_messages_conv_created`).

### Phase 8 — Interview Preparation (`20261111_0009`)
- `interview_sessions`: Tailored mock interview sessions (`id`, `user_id` FK -> `users.id`, `job_id` FK -> `jobs.id`, `application_id` FK -> `applications.id`, `title`, `target_role`, `company_name`, `focus_area`, `difficulty`, `status`, `question_count`, `overall_score`, `created_at`, `updated_at`).
- `interview_questions`: Ordered session prompts (`id`, `session_id` FK -> `interview_sessions.id`, `user_id` FK -> `users.id`, `order_index`, `category`, `prompt`, `expected_topics`, `difficulty`, `guidance`, `created_at`).
- `interview_answers`: Candidate responses (`id`, `question_id` FK -> `interview_questions.id` unique, `session_id` FK -> `interview_sessions.id`, `user_id` FK -> `users.id`, `answer_text`, `time_spent_seconds`, `submitted_at`, `created_at`, `updated_at`).
- `interview_feedback`: Documented rubric evaluations and improvement plans (`id`, `session_id` FK -> `interview_sessions.id` unique, `user_id` FK -> `users.id`, `overall_score`, `rubric_scores`, `strengths`, `weaknesses`, `question_evaluations`, `skill_improvement_plan`, `summary`, `model_used`, `tokens_used`, `evaluated_at`, `created_at`, `updated_at`).

### Phase 9 — Career Memory & Reminders (`20261111_0010`)
- `career_memory`: User-controlled long-term career preferences, goals, strengths, and working notes (`id`, `user_id` FK -> `users.id`, `category`, `title`, `content`, `source`, `memory_key`, `is_approved`, `is_active`, `created_at`, `updated_at`, unique `uq_career_memory_user_key` on `(user_id, memory_key)`, index `ix_career_memory_user_active`).
- `reminders`: Deduplicated timezone-aware reminder and notification queue (`id`, `user_id` FK -> `users.id`, `application_id` FK -> `applications.id` nullable ondelete `SET NULL`, `job_id` FK -> `jobs.id` nullable ondelete `SET NULL`, `title`, `message`, `reminder_type`, `dedup_key`, `scheduled_for`, `user_timezone`, `channel`, `status`, `attempts`, `max_attempts`, `last_error`, `sent_at`, `next_retry_at`, `created_at`, `updated_at`, unique `uq_reminders_user_dedup` on `(user_id, dedup_key)`, indexes `ix_reminders_user_status_sched` and `ix_reminders_due_lookup`).
