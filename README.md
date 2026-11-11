# CareerPilot AI

Intelligent Placement Co-Pilot for Students (PS-06), built with a modular monolithic architecture combining FastAPI, PostgreSQL, Redis/Celery, LangGraph, OpenAI, ChromaDB, Adzuna, and a React + TypeScript frontend.

See [`docs/IMPLEMENTATION_SPEC.md`](docs/IMPLEMENTATION_SPEC.md) for the complete architecture, roadmap, and production requirements.

## Project Layout

- `backend/` — FastAPI application, SQLAlchemy 2.0 models, Alembic migrations, Celery workers, LangGraph agents, and Pytest suite
- `frontend/` — React + TypeScript + Vite + Tailwind CSS application
- `docs/` — Architecture, API, database, security, testing, and specification documents

## Local Development Setup

### 1. Configure External Services & Credentials
Copy `.env.example` to `.env` and populate connection credentials for your PostgreSQL database, Redis instance, ChromaDB endpoint, and Google OAuth client:
```bash
cp .env.example .env
```

### 2. Backend Setup & Migrations
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Verify health endpoints:
- `GET http://localhost:8000/api/v1/health`
- `GET http://localhost:8000/api/v1/health/ready`

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 4. Quality Checks & Tests
```bash
# Backend
backend/.venv/bin/pytest backend/tests
backend/.venv/bin/ruff check backend
backend/.venv/bin/mypy backend/app

# Frontend
cd frontend && npm test && npm run typecheck && npm run build
```
