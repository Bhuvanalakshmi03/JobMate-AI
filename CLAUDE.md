# CareerPilot AI — Engineering Rules & Context

Primary specification: `docs/IMPLEMENTATION_SPEC.md`

## Core Architecture
- Modular Monolithic Architecture with Multi-Agent Orchestration (LangGraph).
- **Frontend:** `frontend/` — React + TypeScript + Vite + Tailwind CSS + React Router + TanStack Query.
- **Backend:** `backend/app/` — FastAPI + SQLAlchemy 2.0 (async) + Alembic + PostgreSQL + Celery/Redis + ChromaDB + OpenAI + Adzuna.
- **Strict Separation:** Routers/schemas (`api/v1/`, `modules/*/router.py`) -> Domain services (`modules/*/service.py`) -> Repositories (`modules/*/repository.py`) -> Models (`models/`, `modules/*/models.py`) -> External adapters (`integrations/`).

## Non-Negotiable Constraints
- Never place business logic in `main.py` or API routers.
- Never hardcode credentials or expose backend secrets to frontend code.
- Never invent resume facts, skills, metrics, or mock job listings in production workflows.
- Always enforce account-level ownership checks on private resources.
- External actions (application submission, recruiter emails, external uploads) require explicit human approval bound to exact payload and destination.
- Store timestamps in UTC; use UUID primary keys; manage schema changes exclusively via Alembic migrations.
- Do not log raw resume contents, tokens, or PII.
- Write unit/integration tests and update `docs/` alongside every implemented phase.

## Common Commands
- Backend tests: `backend/.venv/bin/pytest backend/tests`
- Backend lint & type check: `backend/.venv/bin/ruff check backend && backend/.venv/bin/mypy backend/app`
- Alembic migrations (from `backend/`): `.venv/bin/alembic upgrade head`
- Backend dev server (from `backend/`): `.venv/bin/uvicorn app.main:app --reload --port 8000`
- Frontend dev: `cd frontend && npm run dev`
- Frontend tests: `cd frontend && npm test`
