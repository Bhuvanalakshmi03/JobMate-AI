# JobMate AI — Architecture Overview

## Pattern
JobMate AI uses a **Modular Monolithic Architecture** (`backend/app/`) paired with a **Feature-Modular React Frontend** (`frontend/src/`).

## Backend Layer Boundaries

### Core & Database Infrastructure (Phase 1)
- `app/main.py`: FastAPI application factory (`create_app`), CORS configuration, middleware registration, exception handler wiring, and engine lifespan management.
- `app/core/`: Validated Pydantic Settings (`config.py`), structured JSON logging (`logging.py`), centralized exceptions (`exceptions.py`), SHA-256/PKCE/JWT security (`security.py`), and dependencies (`dependencies.py`).
- `app/database/`: Async SQLAlchemy 2.0 engine, `UTCDateTime`/`UUIDPrimaryKeyMixin` mixins, and Alembic migrations.
- `app/observability/middleware.py`: `RequestContextMiddleware` propagating `X-Request-ID`, baseline security headers, and latency telemetry.

### Domain Modules & Integrations (Phases 2–7)
- `app/integrations/oauth/google.py`: Google OAuth 2.0 / OIDC adapter (`GoogleOAuthClient`).
- `app/integrations/storage/local.py`: Private non-overwriting file storage (`LocalPrivateStorage`).
- `app/integrations/document_parser/extractor.py`: PDF/DOCX signature validation and text extraction via PyMuPDF and `python-docx`.
- `app/integrations/openai/client.py`: Centralized OpenAI client (`OpenAIChatClient`) supporting chat JSON completions, live `web_search` tool calls, and dense embeddings (`embed_texts`).
- `app/integrations/job_search/openai_web_search.py`: Live web-search job discovery adapter (`OpenAIWebSearchJobProvider`).
- `app/integrations/chroma/store.py`: Dedicated vector-store interface (`VectorStoreProtocol`, `ChromaVectorStore` HTTP v2 client, `InMemoryVectorStore`).
- `app/integrations/calendar/google_calendar.py`: Google Calendar API v3 client (`GoogleCalendarClient`, `CalendarProviderProtocol`) for upcoming event reads and human-approved event creation.
- `app/modules/authentication/`: `User`, `UserSession`, `OAuthState` (supports login & incremental `calendar_connect` flow), `AuthService`, and `/api/v1/auth/*`.
- `app/modules/profile/`: `UserProfile`, `UserSkill`, `ProfileService`, and `/api/v1/profile/*`.
- `app/modules/resume/`: `Resume`, `ResumeFact`, separated parser/extractor/validator/tasks/service, and `/api/v1/resumes/*`.
- `app/modules/jobs/`: `Job`, `SavedJob`, canonical fingerprint deduplication, Redis search caching, `JobDiscoveryService`, and `/api/v1/jobs/*`.
- `app/modules/matching/`: `JobMatch`, deterministic configurable weighted scorer (`scorer.py`) + semantic embedding similarity (`JobMatchingService`).
- `app/modules/documents/`: `GeneratedDocument`, verified-fact-only generator (`generator.py`), anti-hallucination validator (`validator.py`), ATS PDF/DOCX/MD exporter (`exporter.py`), versioned `DocumentService`, and `/api/v1/documents/*`.
- `app/modules/applications/`: `Application`, `ApplicationHistory`, controlled status transition state machine (`state_machine.py`), `ApplicationRepository`, `ApplicationService`, and `/api/v1/applications/*`.
- `app/modules/rag/`: Text normalization/chunking (`chunker.py`), content hashing, prompt-injection sanitization, and user-isolated `RAGService`.
- `app/agents/`: LangGraph `StateGraph` orchestrator (`graph.py`), typed `CareerPilotAgentState` (`state.py`), step/token/retry/trace policies (`policies.py`), independent prompts (`prompts/`), least-privilege user toolset (`tools/registry.py`), and 9 specialist nodes (`nodes/`).
- `app/modules/agents/`: `WorkflowRun`, `AgentOrchestrationService` (workflow checkpoint pause/resume), and `/api/v1/agents/*`.
- `app/modules/approvals/`: `ApprovalRequest`, `ApprovalService` enforcing human confirmation before external side effects (including `submit_application` and `create_calendar_event`), and `/api/v1/approvals/*`.
- `app/modules/calendar/`: `GoogleCalendarConnection` (Fernet-encrypted token storage + automatic refresh), `CalendarService`, and `/api/v1/calendar/*`.
- `app/modules/copilot/`: `CopilotConversation`, `CopilotMessage`, 13 user-scoped OpenAI tools (`toolkit.py`), `CopilotChatService`, and `/api/v1/copilot/*`.
- `backend/scripts/seed_user_data.py`: Idempotent realistic workspace data seeder preserving existing resumes and `ResumeFact` records.
- `app/repositories/audit_repository.py`: Shared immutable audit logging repository.

## Frontend Layer Boundaries
- `src/services/`: Centralized `api-client.ts`, `health-service.ts`, `auth-service.ts`, `profile-service.ts`, `resume-service.ts`, `job-service.ts`, `document-service.ts`, `application-service.ts`, `agent-service.ts`, `approval-service.ts`, `calendar-service.ts`, `copilot-service.ts`.
- `src/features/authentication/`: `AuthProvider`/`useAuth`, `ProtectedRoute`, `LoginPage`.
- `src/features/profile/`: `ProfilePage`, `SkillsManager`, profile/skills hooks.
- `src/features/resume/`: `ResumesPage`, `ResumeAnalysisPage`, `ResumeFactCard`, resume hooks.
- `src/features/jobs/`: `JobsPage`, `JobDetailsPage`, `JobCard`, `JobFilters`, `MatchScore`, job/match hooks.
- `src/features/documents/`: `DocumentsPage`, `DocumentEditorPage`, document generation/version hooks.
- `src/features/applications/`: `ApplicationsPage`, `ApplicationDetailsPage`, application hooks and date utilities.
- `src/features/agents/`: `AgentCopilotPage` (tabbed Co-Pilot Chat & Calendar + LangGraph Workflows & RAG), workflow/RAG hooks.
- `src/features/calendar/`: `WeeklyCalendarPage`, `WeeklyCalendarCard` (strict 7-day upcoming schedule + pending calendar proposals), and `useCalendar` hooks for Google Calendar connection status, upcoming events, and OAuth connect/disconnect.
- `src/features/copilot/`: `CopilotChatPanel` and `useCopilotChat` hooks for session management, tool-calling transcripts, and inline approval cards.
- `src/features/approvals/`: `ApprovalsPage`, human approval decision hooks.
- `src/features/dashboard/`: `FoundationStatusPage`.
