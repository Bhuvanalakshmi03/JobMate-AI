# CareerPilot AI — Testing Guide

## Backend Test Suite
- **Framework:** Pytest + `pytest-asyncio` + HTTPX (`ASGITransport`).
- **Location:** `backend/tests/`
- **Run unit tests:**
  ```bash
  backend/.venv/bin/pytest backend/tests
  ```
- **Lint & type check:**
  ```bash
  backend/.venv/bin/ruff check backend
  backend/.venv/bin/mypy backend/app
  ```

## Frontend Test Suite
- **Framework:** Vitest + React Testing Library + jsdom.
- **Location:** `frontend/tests/`
- **Run tests & build:**
  ```bash
  cd frontend && npm test && npm run build
  ```

