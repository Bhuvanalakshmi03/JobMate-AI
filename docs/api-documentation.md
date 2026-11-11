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
