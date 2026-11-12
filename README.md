# AAROH – Your Personal Life OS

A personal life operating system: tasks and calendar, goals and habits, money, investments and net worth, journal, a software-engineering learning hub, fitness and nutrition, a professional work journal, a UPSC-knowledge and side-income hub, and Aaroh AI, a companion that reads (only) the data you allow and turns it into briefings, reviews and practical next steps.

Web app + Android app (one React codebase via Capacitor) on a FastAPI + PostgreSQL backend.

## Status

| Area | State |
|---|---|
| Backend: 11 modules, auth, AI layer, migrations | Done; 20 API tests pass (`backend/tests`) |
| Web app: 11 screens, light/dark, mobile layout | Done; 18 end-to-end browser journeys pass (`web/e2e/run.mjs`) |
| Free one-click hosting (Render + Neon via `render.yaml`) | Single-service image verified locally; see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md#0-free-hosting-render--neon-no-server-to-manage) |
| Docker Compose stack (db, api, web, backups, optional HTTPS) | Built and verified locally |
| Android project (Capacitor) | Generated with icons, secure token storage, local notifications |
| APK | Builds in GitHub Actions (`.github/workflows/ci.yml`) or locally with the Android SDK; see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| Real LLM | Anthropic and OpenAI-compatible providers implemented; needs your API key. Offline mode is clearly labelled otherwise |

## Quick start (development)

Requirements: Python 3.12+, Node 22, PostgreSQL 16.

```bash
# database
createuser -P aaroh            # password: aaroh
createdb -O aaroh aaroh

# backend
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env           # for dev set ENVIRONMENT=development, COOKIE_SECURE=false, DATABASE_URL=...@localhost
alembic upgrade head
python -m app.seed             # demo data
uvicorn app.main:app --reload  # http://localhost:8000/api/docs

# web
cd ../web
npm install
npm run dev                    # http://localhost:5173 (proxies /api to :8000)
```

Or everything in Docker: `cp .env.example .env && cp backend/.env.example backend/.env` (fill in keys), then `docker compose up -d --build` and open http://localhost:8080.

### Demo account

`demo@aaroh.app` / `Aaroh@2026`. Created by `python -m app.seed` with ~5 weeks of realistic data: tasks (including overdue and repeatedly postponed ones), habits with streaks, two months of INR transactions, budgets, subscriptions, skills and roadmaps, learning logs, workouts with sets, food and activity logs, weight trend, work journal, journal entries with moods, and side-income opportunities. Re-running the seed recreates the demo user.

## Tests

```bash
cd backend && DATABASE_URL=postgresql+psycopg://aaroh:aaroh@localhost:5432/aaroh_test python -m pytest -q
cd web && npm run build                                  # type-check + build
cd web && BASE_URL=http://localhost:5173 node e2e/run.mjs   # needs Playwright, a running stack and the seeded demo user
```

API tests (20) cover auth (rotation and token-reuse detection), cross-user data isolation, every module's CRUD and summaries, smart planning, recurrence, photo uploads, settings and privacy filtering, offline AI, the OpenAI-compatible provider, the Anthropic SDK request shape, export and account deletion.

## Using AI

Set a provider in `backend/.env` (server-wide) or in **Settings → AI provider** (per user, key stored encrypted). Supported: Anthropic (default model `claude-opus-5-5`) and any OpenAI-compatible API (OpenAI, Groq, OpenRouter, Together, Ollama, LM Studio). **Settings → Privacy** controls which modules the AI may read; journal access is off by default and individual entries can be hidden. "Preview exactly what the AI sees" shows the context sent with each request.

## Project layout

```
backend/   FastAPI app, Alembic migrations, tests, seed data
web/       React + TypeScript app, Capacitor Android project (web/android), e2e journeys
docs/      ARCHITECTURE.md (design + DB schema), API.md + openapi.json, DEPLOYMENT.md
scripts/   backup.sh
docker-compose.yml
```

## Extending

- **New module:** add models in `backend/app/models.py`, schemas in `schemas.py`, register `crud_router(...)` plus any summary endpoints in a router, `alembic revision --autogenerate`, then a page in `web/src/pages` using `useList`/`useCrud` and `EntityForm`.
- **New AI capability:** add a prompt in `ai/prompts.py` (`INSIGHT_PROMPTS` + `INSIGHT_FOCUS`), the kind to `InsightKind` in `schemas.py`, and an `offline.py` branch; render with `<InsightCard kind="..."/>`.
- **New LLM provider:** implement `complete(system, messages, max_tokens)` in `ai/providers.py` and add it to `resolve_config`.
- **Partner / shared workspace (Phase 3):** schema is ready (`workspaces`, `workspace_members`, `workspace_invitations`, `visibility`); add invite/accept endpoints and a workspace switcher that sends `X-Workspace-Id`.
- **iOS:** `cd web && npx cap add ios` on a Mac.
- **Health Connect:** a Capacitor Health Connect plugin can read steps/workouts/weight and post them to `POST /api/v1/fitness/import`.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for design decisions and trade-offs.
