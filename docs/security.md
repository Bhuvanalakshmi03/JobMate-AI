# CareerPilot AI — Security Controls

## Authentication & Sessions
- **OAuth 2.0 / OIDC:** Uses single-use hashed CSRF `state`, OIDC `nonce` verification, PKCE (`S256`), and Google ID token verification checking `iss`, `aud`, `exp`, and `email_verified`.
- **Open Redirect Prevention:** Post-login `redirect_to` parameters allow only relative single-slash paths (`/`).
- **Revocable Sessions:** Signed HS256 JWTs carry a `sid` (session UUID) backed by SHA-256 `token_hash` records in `user_sessions`.
- **Development Auth Guard:** `DEV_AUTH_ENABLED=true` is rejected by `Settings` validation in `staging` and `production`.

## Authorization & Data Isolation
- Every query in `ProfileRepository`, `SkillRepository`, `ResumeRepository`, `ResumeFactRepository`, `SavedJobRepository`, and `JobMatchRepository` scopes strictly to `current_user.id`.

## Resume Upload, Storage & AI Security
- **File Validation:** Enforces `.pdf`/`.docx` extensions, size/page bounds, MIME checks, binary magic signatures, and DOCX zip-bomb bounds.
- **Private Storage:** Originals are saved under UUID-based keys via `LocalPrivateStorage` with strict path-traversal rejection and `O_EXCL` non-overwriting creation.
- **AI Prompt Injection & Fact Grounding:** Resume text is isolated inside `<untrusted_resume_text>` delimiters; `ResumeExtractionValidator` validates schemas and grounds excerpts against extracted text.
- **Job Discovery Integrity & Fair Matching:** `OpenAIWebSearchJobProvider` filters out invalid/placeholder URLs and treats external job descriptions as untrusted data. Job matching uses configurable deterministic weights + semantic similarity without sensitive personal attributes or proxies.

## Input Validation & Logging
- IANA timezones validated via `zoneinfo.ZoneInfo`; external links restricted to `http://` and `https://`.
- Structured JSON logs recursively redact sensitive keys (`token`, `secret`, `api_key`, `password`, `resume_text`, `raw_text`).
- Centralized exception handling omits internal stack traces from API responses.
