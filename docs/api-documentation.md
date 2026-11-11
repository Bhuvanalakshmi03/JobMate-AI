# CareerPilot AI — API v1 Documentation

All backend routes are versioned under `/api/v1`. Protected routes require a valid session cookie (`careerpilot_session`) or `Authorization: Bearer <token>` header.

## Health & Auth Endpoints (Phases 1–2)
- `GET /api/v1/health`, `GET /api/v1/health/ready`
- `GET /api/v1/auth/config`, `GET /api/v1/auth/google`, `GET /api/v1/auth/google/callback`, `POST /api/v1/auth/dev-login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`
- `GET /api/v1/profile`, `POST /api/v1/profile`, `PUT /api/v1/profile`, `GET /api/v1/profile/skills`, `PUT /api/v1/profile/skills`

## Resume Intelligence Endpoints (Phase 3)
- `POST /api/v1/resumes/upload`, `GET /api/v1/resumes`, `GET /api/v1/resumes/{resume_id}`, `POST /api/v1/resumes/{resume_id}/analyze`, `GET /api/v1/resumes/{resume_id}/analysis`, `PATCH /api/v1/resumes/{resume_id}/facts`, `DELETE /api/v1/resumes/{resume_id}`

## Job Discovery & Matching Endpoints (Phase 4)
- `GET /api/v1/jobs/search`, `GET /api/v1/jobs/recommended`, `GET /api/v1/jobs/saved`, `GET /api/v1/jobs/{job_id}`, `POST /api/v1/jobs/{job_id}/match`, `POST /api/v1/jobs/{job_id}/save`, `DELETE /api/v1/jobs/{job_id}/save`

## Document Generation Endpoints (Phase 5)
- `POST /api/v1/documents/tailor-resume` — Generate job-specific ATS-friendly resume strictly from verified facts (`201 Created`).
- `POST /api/v1/documents/cover-letter` — Generate job-specific cover letter grounded in verified facts (`201 Created`).
- `POST /api/v1/documents/application-note` — Generate short recruiter/application note (`201 Created`).
- `GET /api/v1/documents` — List generated documents owned by authenticated user (`?job_id=...&document_type=...`).
- `GET /api/v1/documents/{document_id}` — Get document details and full version history.
- `PATCH /api/v1/documents/{document_id}` — Edit document content, preserving prior versions when `create_new_version=true`.
- `GET /api/v1/documents/{document_id}/download` — Export document as `pdf`, `docx`, or `md`.

## Application Tracking Endpoints (Phase 6)
Allowed statuses: `SAVED`, `PREPARING`, `AWAITING_APPROVAL`, `SUBMITTED`, `INTERVIEW_SCHEDULED`, `REJECTED`, `OFFER_RECEIVED`, `WITHDRAWN`.
- `GET /api/v1/applications` — List tracked applications owned by authenticated user (`?status=...&limit=...&offset=...`).
- `GET /api/v1/applications/summary` — Get pipeline counts by status (`counts_by_status`) and `upcoming_deadlines`.
- `POST /api/v1/applications` — Create a tracked application linked to a discovered job or custom entry (`201 Created`).
- `GET /api/v1/applications/{application_id}` — Get application details, `allowed_next_statuses`, and transition `history`.
- `PATCH /api/v1/applications/{application_id}` — Update metadata, deadlines, linked documents, or notes (status changes require `/transition`).
- `POST /api/v1/applications/{application_id}/transition` — Transition status via backend state-machine validation with optional `note`.
- `DELETE /api/v1/applications/{application_id}` — Delete a tracked application (`204 No Content`).

## Multi-Agent & RAG Endpoints (Phase 7)
- `POST /api/v1/agents/workflows` — Trigger a LangGraph multi-agent workflow (`auto`, `job_discovery`, `application_prep`, `career_advisory`) (`201 Created`).
- `GET /api/v1/agents/workflows` — List workflow runs owned by the authenticated user.
- `GET /api/v1/agents/workflows/{workflow_id}` — Inspect workflow status, specialist outputs, validation flags, and execution trace.
- `POST /api/v1/agents/rag/sync` — Index verified profile, skills, resume facts, and documents into vector storage.
- `POST /api/v1/agents/rag/query` — Query user-isolated semantic RAG context.

## Human Approval Endpoints (Phase 7)
- `GET /api/v1/approvals` — List approval requests (`?status=PENDING|APPROVED|REJECTED|EXECUTED...`).
- `POST /api/v1/approvals` — Prepare a standalone human-gated external action approval (`201 Created`).
- `GET /api/v1/approvals/{approval_id}` — Inspect exact target destination, payload, and execution status.
- `POST /api/v1/approvals/{approval_id}/approve` — Confirm and execute a pending external action (`submit_application` or `create_calendar_event`) and resume linked workflow.
- `POST /api/v1/approvals/{approval_id}/reject` — Reject a pending external action and prevent execution.

## Google Calendar Endpoints (`20261111_0008`)
- `GET /api/v1/calendar/status` — Check whether the current user has connected Google Calendar (`connected`, `google_email`, `scopes`, `token_expires_at`).
- `GET /api/v1/calendar/connect` — Initiate incremental Google Calendar OAuth consent (`?mode=json&redirect_to=/copilot`), reusing `/api/v1/auth/google/callback`.
- `GET /api/v1/calendar/events` — Read upcoming primary Google Calendar events (`?days_ahead=14&max_results=15`).
- `POST /api/v1/calendar/events` — Directly create a Google Calendar event (`201 Created`; Co-Pilot tools use `propose_calendar_event` -> human approval first).
- `DELETE /api/v1/calendar/disconnect` — Remove stored Google Calendar connection and encrypted tokens (`204 No Content`).

## Session-Managed Co-Pilot Chat Endpoints (`20261111_0008`)
- `GET /api/v1/copilot/conversations` — List chat sessions owned by the authenticated user.
- `POST /api/v1/copilot/conversations` — Create a new chat session (`201 Created`).
- `GET /api/v1/copilot/conversations/{conversation_id}` — Load full conversation transcript, executed tool logs, and linked approval items.
- `PATCH /api/v1/copilot/conversations/{conversation_id}` — Rename or archive a chat session.
- `DELETE /api/v1/copilot/conversations/{conversation_id}` — Delete a chat session and its messages (`204 No Content`).
- `POST /api/v1/copilot/conversations/{conversation_id}/messages` — Send a user turn, run OpenAI multi-turn function calling across 13 user-scoped tools, persist tool logs + proposed approvals, and return the assistant reply.

## Workspace Seeding Script
```bash
cd backend && .venv/bin/python -m scripts.seed_user_data --email mukilan069@gmail.com
```
Idempotently seeds curated jobs, `JobMatch` scores, verified grounded documents, multi-stage applications, pending approvals, and a starter Co-Pilot chat conversation without overwriting existing resumes or `ResumeFact`s.
