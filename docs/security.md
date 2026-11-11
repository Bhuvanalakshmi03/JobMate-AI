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
