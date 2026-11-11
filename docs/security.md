# JobMate AI — Security Controls

## Authentication & Sessions
- **OAuth 2.0 / OIDC:** Uses single-use hashed CSRF `state`, OIDC `nonce` verification, PKCE (`S256`), and Google ID token verification checking `iss`, `aud`, `exp`, and `email_verified`.
- **Open Redirect Prevention:** Post-login `redirect_to` parameters allow only relative single-slash paths (`/`).
- **Revocable Sessions:** Signed HS256 JWTs carry a `sid` (session UUID) backed by SHA-256 `token_hash` records in `user_sessions`.
- **Development Auth Guard:** `DEV_AUTH_ENABLED=true` is rejected by `Settings` validation in `staging` and `production`.

## Authorization & Data Isolation
- Every query across `profile`, `resume`, `jobs/saved`, `matching`, and `documents` repositories scopes strictly to `current_user.id`.

## Resume, Job & Document AI Security
- **File Validation & Private Storage:** Validates `.pdf`/`.docx` extensions, size/page bounds, MIME types, magic bytes, and zip-bomb bounds; saves originals under non-overwriting UUID paths without execution.
- **Anti-Hallucination & Factuality Gate:** Document generation loads ONLY verified `resume_facts` (`is_verified=True` and `verification_status != "rejected"`), verified `user_skills`, and `user_profiles`. `DocumentFactualityValidator` blocks any generated resume/letter/note containing unverified employers, unverified skills, or invented numerical metrics (`%`, `$`, `x`).
- **Prompt Injection Defense:** Both untrusted resume text and scraped job descriptions are isolated inside explicit delimiters with instruction-ignoring rules.
- **Safe Export Rendering:** ATS PDF HTML templates escape all user text via `html.escape`, and download headers sanitize filenames.

## Input Validation & Logging
- IANA timezones validated via `zoneinfo.ZoneInfo`; external links restricted to `http://` and `https://`.
- Structured JSON logs recursively redact sensitive keys (`token`, `secret`, `api_key`, `password`, `resume_text`, `raw_text`).
- Centralized exception handling omits internal stack traces from API responses.

## Career Memory Privacy, Reminders & Account Lifecycle (Phase 9)
- **Explicit Privacy Consent Gating:** Persistent Career Memory creation/update and Co-Pilot prompt injection are blocked unless `user_profiles.ai_consent_given=true`; notification opt-in is tracked via `notification_consent`.
- **Full Memory Ownership & Control:** Users can inspect, edit, approve/deactivate, delete individual entries, or wipe all `career_memory` rows at any time via `/api/v1/memory/*`.
- **Deduplicated & Bounded Reminder Delivery:** Unique `(user_id, dedup_key)` constraint prevents duplicate reminder spam, and failed dispatches transition safely to `RETRY_QUEUED` up to `max_attempts` before `FAILED`.
- **Personal Data Export & Account Deletion:** `GET /api/v1/auth/export` exports user-scoped records without internal hashes/secrets; `DELETE /api/v1/auth/account` deletes stored private resume files, revokes cookies, and cascades all database records.
