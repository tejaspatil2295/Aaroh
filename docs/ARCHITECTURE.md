# AAROH architecture

## Overview

```
 Android app (Capacitor)  ─┐
 Web app (React, browser) ─┼── HTTPS ──>  nginx (web container) ── /api ──> FastAPI (api) ──> PostgreSQL
 future iOS (Capacitor)   ─┘                                                    │
                                                                                └──> LLM provider (Anthropic / OpenAI-compatible), optional
```

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 | Typed, fast to extend, auto-generated OpenAPI docs |
| Database | PostgreSQL 16 | Relational integrity across modules, JSONB for flexible fields |
| Auth | Argon2 password hashes, 15-min JWT access tokens, rotating refresh tokens stored as SHA-256 hashes with reuse detection | Stolen refresh tokens are revoked on reuse; passwords never stored reversibly |
| Web | React 19, TypeScript, Vite, Tailwind CSS 4, Recharts, TanStack Query | One component system, small bundles per screen |
| Android | Capacitor 8 wrapping the same React build | One UI codebase for web, Android and later iOS (see trade-off below) |
| Token storage | Web: httpOnly SameSite=strict cookie for refresh, access token in memory. Android: refresh token in Android Keystore-backed secure storage | No tokens in localStorage |
| Notifications | Capacitor Local Notifications (task reminders, morning/evening routine) | Works offline, no push server needed yet |
| AI | Provider interface (`backend/app/ai/providers.py`) | Swap providers without touching features |
| Deploy | Docker Compose: db, api, web (nginx), backup, optional Caddy for automatic HTTPS | One command on any VPS |

### Stack change from the brief: Capacitor instead of Expo

The brief preferred React Native + Expo. AAROH uses Capacitor around the React web app instead.

- **Why:** ten modules and ~11 screens would otherwise be built and maintained twice (React DOM and React Native). With Capacitor, every feature ships to web and Android at once, and iOS is `npx cap add ios`.
- **Trade-off:** UI is rendered in a WebView, so it is slightly less "native" than React Native, and heavy native integrations (Health Connect) need a Capacitor plugin rather than an Expo module. Both are acceptable for a personal dashboard-style app.
- **Escape hatch:** the API is client-agnostic. A React Native client can be added later against the same endpoints.

## Backend layout

```
backend/app/
  main.py          app, CORS, security headers, router registration
  config.py        env settings          defaults.py   default preferences & AI permissions
  db.py            engine/session        models.py     all tables (see below)
  security.py      hashing, JWT, Fernet  deps.py       auth + workspace context (Ctx)
  access.py        row-level access rules (every query goes through visible()/get_owned())
  crud.py          generic workspace-scoped CRUD router factory
  analytics.py     deterministic metrics used by dashboard, reports and AI context
  routers/         auth, users (profile/settings/export/delete), dashboard, planner (tasks/goals/habits/plan),
                   finance, journal (+photos), learning, fitness, work_side (work journal + side income), ai
  ai/              providers.py, context.py (privacy-filtered context), prompts.py (7 personas), offline.py, service.py
  seed.py          demo account with ~5 weeks of data
```

## Multi-user and data isolation

- Every user-owned row has `owner_id`, `workspace_id`, `visibility` (`private` | `shared`).
- On sign-up a user gets a personal `workspace` and a `workspace_members` row with role `owner`.
- `access.visible()` returns only rows in the active workspace that the caller owns, or that are marked `shared`. `get_owned()` 404s for anything else, so other users' IDs are indistinguishable from missing ones. Writes on shared rows need role owner/admin/member.
- Referenced IDs (goal, skill, subscription, opportunity) are checked against the same rules before saving.
- Phase 3 (partner/family): add invitation endpoints over the existing `workspace_invitations` table, create a `shared` workspace, and let users flip `visibility` on chosen tasks/budgets/goals. Journals and personal finance stay private because they live in each person's personal workspace.

## Database schema

All tables below except identity tables also carry `id (uuid)`, `owner_id`, `workspace_id`, `visibility`, `created_at`, `updated_at`. Migrations: `backend/alembic/versions/`.

| Area | Table | Key columns |
|---|---|---|
| Identity | `users` | email (unique), password_hash, full_name, about, is_active |
| | `user_settings` | preferences (JSONB), ai_permissions (JSONB), ai_provider, ai_model, ai_base_url, ai_api_key_encrypted |
| | `workspaces`, `workspace_members`, `workspace_invitations` | kind personal/shared, role owner/admin/member/viewer |
| | `refresh_tokens` | token_hash, family_id, expires_at, revoked_at |
| Planning | `goals` | area, status, target_date, metric_unit, start/target/current_value |
| | `milestones` | goal_id, due_date, done |
| | `tasks` | category, priority, status, due_date, scheduled_start, estimate_minutes, reminder_at, recurrence, parent_id, goal_id, tags, postponed_count |
| | `habits`, `habit_logs` | target_per_week; (habit_id, date) unique |
| Finance | `transactions` | kind expense/income, amount NUMERIC(12,2), currency (INR default), category, date, subscription_id, opportunity_id |
| | `budgets` | month YYYY-MM, category (`__total__` = overall), amount |
| | `subscriptions` | amount, billing_cycle, next_due_date, active |
| | `financial_goals` | target_amount, saved_amount, target_date |
| Journal | `journal_entries` | kind, entry_date, mood, energy, tags, decision_outcome, hide_from_ai |
| | `attachments` | entity_type/entity_id, content_type, storage_path (photos) |
| Learning | `skills`, `roadmap_items`, `learning_logs`, `knowledge_notes`, `resources`, `learning_items`, `interview_items` | levels 0-5, roadmap order/done, minutes per day, snippets, courses/projects/certs, confidence 1-5 |
| Fitness | `body_metrics`, `workouts`, `workout_sets`, `daily_activity`, `food_logs` | weight/body fat, sets×reps×kg, steps/water/sleep (unique per day), calories/protein |
| Work | `work_logs` | project, summary, tasks_completed, problems, solutions, learnings, pending, hours |
| Side income | `opportunities` | category, status, investment, est_monthly_low/high, hours_per_week, skills, validation_notes, execution_plan, ai_evaluation |
| AI | `ai_conversations`, `ai_messages`, `ai_insights` | persona; provider/model/is_fallback on every output |

Health Connect / Google Fit: `workouts.source/external_id` and `daily_activity.source` plus `POST /fitness/import` (idempotent by external_id) are the integration seam. A Capacitor Health Connect plugin on the device would read records and post them there.

## Intelligence layer

1. **Analytics (`analytics.py`)**: productivity score, streaks, 30-day habit consistency, missed-task patterns by category and weekday, monthly finance, spending drift vs last month, subscription load, protein/steps adherence, weight trend, skill gaps, work hours by project. Pure computation over the user's rows.
2. **Smart scheduling (`POST /tasks/plan`)**: places open tasks into free time inside the user's configured day window, avoiding already-scheduled tasks, scoring by overdue, due date, priority, in-progress and how often a task has been postponed. Preview or apply.
3. **Context builder (`ai/context.py`)**: turns analytics plus recent records into a compact text context, only for modules the user allowed. Journal is opt-in; entries can be individually hidden. `GET /ai/context-preview` shows exactly what would be sent.
4. **Personas (`ai/prompts.py`)**: Life Coach, Career Mentor, Technical Teacher, Financial Coach, Fitness Companion, Journal Companion, Side-Hustle Advisor, all under shared guardrails (no shaming or manipulation, not a therapist, crisis line Tele-MANAS 14416, no income promises).
5. **Insights (`ai/service.py`)**: morning briefing, evening review, weekly/monthly reviews, task suggestions, learning recommendations, finance/fitness reports, journal patterns, work weekly report, habit analysis. Cached per period, regenerable.
6. **Offline mode**: without a provider, insights and chat return rule-based summaries that are always labelled "Offline insights" and stored with `is_fallback=true`. Features that need generation (task breakdown, opportunity evaluation) return 503 with a clear message instead of faking output.

## Security notes

- Passwords: Argon2id. Login/register are rate-limited per IP (in-process; move to Redis when running several API replicas).
- AI keys: user-supplied keys are encrypted with Fernet (key derived from `ENCRYPTION_KEY`) and never returned by the API.
- Uploads: images only (JPEG/PNG/WEBP/HEIC), size-capped, stored per user, served only through authorized endpoints.
- Headers: nosniff, frame deny, no-referrer, `Cache-Control: no-store` on API responses.
- HTTPS: terminate with the bundled Caddy profile (automatic Let's Encrypt) or your own proxy; set `COOKIE_SECURE=true`.
- Data rights: `GET /users/me/export` (full JSON export), `DELETE /users/me` (password + "DELETE" confirmation, removes rows and photos).
- Backups: the `backup` service writes a gzip'd `pg_dump` daily to `./backups`, keeping 14 days.
