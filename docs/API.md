# AAROH API reference

173 operations across 96 paths. The live, interactive reference (try requests with your token) is served by the backend at **`/api/docs`** (Swagger UI) and **`/api/redoc`**. The machine-readable spec is in [`openapi.json`](openapi.json); regenerate it with:

```bash
cd backend && python -c "import json;from app.main import app;json.dump(app.openapi(),open('../docs/openapi.json','w'),indent=1)"
```

## Conventions

- Base path: `/api/v1`. JSON in and out. Dates are `YYYY-MM-DD`, timestamps ISO-8601 with timezone.
- Auth: `POST /auth/login` returns `{access_token, refresh_token}`. Send `Authorization: Bearer <access_token>`. Access tokens last 15 minutes.
- Refresh: `POST /auth/refresh` with `{"refresh_token": "..."}` (mobile) or the httpOnly `aaroh_refresh` cookie (web). Tokens rotate on every refresh; reusing an old one revokes the whole session family.
- Workspace: optional `X-Workspace-Id` header. Defaults to the user's personal workspace.
- Collections share one shape: `GET` (filters, `q` search, `from`/`to` date range, `limit`, `offset`), `POST`, `GET /{id}`, `PATCH /{id}` (partial), `DELETE /{id}` (204).
- Errors: `{"detail": "..."}` or FastAPI's validation list with status 422. 401 unauthenticated, 404 not found or not yours, 409 conflict, 429 rate-limited, 502/503 AI provider issues.

## Endpoints by module

### auth
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
### account
- `GET /api/v1/users/me`
- `PATCH /api/v1/users/me`
- `DELETE /api/v1/users/me`
- `POST /api/v1/users/me/password`
- `GET /api/v1/users/me/settings`
- `PATCH /api/v1/users/me/settings`
- `GET /api/v1/users/me/export`
### dashboard
- `GET /api/v1/dashboard`
### ai
- `GET /api/v1/ai/status`
- `GET /api/v1/ai/context-preview`
- `POST /api/v1/ai/chat`
- `GET /api/v1/ai/conversations`
- `GET /api/v1/ai/conversations/{cid}/messages`
- `DELETE /api/v1/ai/conversations/{cid}`
- `POST /api/v1/ai/insights`
- `GET /api/v1/ai/insights`
### tasks
- `GET /api/v1/tasks/calendar`
- `POST /api/v1/tasks/plan`
- `POST /api/v1/tasks/{task_id}/complete`
- `POST /api/v1/tasks/breakdown`
- `POST /api/v1/habits/{habit_id}/toggle`
- `GET /api/v1/habits/status`
- `GET /api/v1/goals/progress`
- `GET /api/v1/tasks`
- `POST /api/v1/tasks`
- `GET /api/v1/tasks/{item_id}`
- `PATCH /api/v1/tasks/{item_id}`
- `DELETE /api/v1/tasks/{item_id}`
### goals
- `GET /api/v1/goals`
- `POST /api/v1/goals`
- `GET /api/v1/goals/{item_id}`
- `PATCH /api/v1/goals/{item_id}`
- `DELETE /api/v1/goals/{item_id}`
- `GET /api/v1/milestones`
- `POST /api/v1/milestones`
- `GET /api/v1/milestones/{item_id}`
- `PATCH /api/v1/milestones/{item_id}`
- `DELETE /api/v1/milestones/{item_id}`
### habits
- `GET /api/v1/habits`
- `POST /api/v1/habits`
- `GET /api/v1/habits/{item_id}`
- `PATCH /api/v1/habits/{item_id}`
- `DELETE /api/v1/habits/{item_id}`
- `GET /api/v1/habit-logs`
- `POST /api/v1/habit-logs`
- `GET /api/v1/habit-logs/{item_id}`
- `PATCH /api/v1/habit-logs/{item_id}`
- `DELETE /api/v1/habit-logs/{item_id}`
### finance
- `GET /api/v1/finance/categories`
- `GET /api/v1/finance/summary`
- `GET /api/v1/finance/trends`
- `GET /api/v1/finance/transactions`
- `POST /api/v1/finance/transactions`
- `GET /api/v1/finance/transactions/{item_id}`
- `PATCH /api/v1/finance/transactions/{item_id}`
- `DELETE /api/v1/finance/transactions/{item_id}`
- `GET /api/v1/finance/budgets`
- `POST /api/v1/finance/budgets`
- `GET /api/v1/finance/budgets/{item_id}`
- `PATCH /api/v1/finance/budgets/{item_id}`
- `DELETE /api/v1/finance/budgets/{item_id}`
- `GET /api/v1/finance/subscriptions`
- `POST /api/v1/finance/subscriptions`
- `GET /api/v1/finance/subscriptions/{item_id}`
- `PATCH /api/v1/finance/subscriptions/{item_id}`
- `DELETE /api/v1/finance/subscriptions/{item_id}`
- `GET /api/v1/finance/goals`
- `POST /api/v1/finance/goals`
- `GET /api/v1/finance/goals/{item_id}`
- `PATCH /api/v1/finance/goals/{item_id}`
- `DELETE /api/v1/finance/goals/{item_id}`
### investments
- `GET /api/v1/investments/asset-classes`
- `GET /api/v1/investments/summary`
- `GET /api/v1/investments/holdings`
- `POST /api/v1/investments/holdings`
- `GET /api/v1/investments/holdings/{item_id}`
- `PATCH /api/v1/investments/holdings/{item_id}`
- `DELETE /api/v1/investments/holdings/{item_id}`
- `GET /api/v1/investments/liabilities`
- `POST /api/v1/investments/liabilities`
- `GET /api/v1/investments/liabilities/{item_id}`
- `PATCH /api/v1/investments/liabilities/{item_id}`
- `DELETE /api/v1/investments/liabilities/{item_id}`
### journal
- `GET /api/v1/journal/tags`
- `GET /api/v1/journal/mood`
- `GET /api/v1/journal/by-tag/{tag}`
- `POST /api/v1/attachments`
- `GET /api/v1/attachments`
- `GET /api/v1/attachments/{att_id}/file`
- `DELETE /api/v1/attachments/{att_id}`
- `GET /api/v1/journal`
- `POST /api/v1/journal`
- `GET /api/v1/journal/{item_id}`
- `PATCH /api/v1/journal/{item_id}`
- `DELETE /api/v1/journal/{item_id}`
### learning
- `GET /api/v1/learning/summary`
- `GET /api/v1/learning/daily`
- `GET /api/v1/learning/skills`
- `POST /api/v1/learning/skills`
- `GET /api/v1/learning/skills/{item_id}`
- `PATCH /api/v1/learning/skills/{item_id}`
- `DELETE /api/v1/learning/skills/{item_id}`
- `GET /api/v1/learning/roadmap`
- `POST /api/v1/learning/roadmap`
- `GET /api/v1/learning/roadmap/{item_id}`
- `PATCH /api/v1/learning/roadmap/{item_id}`
- `DELETE /api/v1/learning/roadmap/{item_id}`
- `GET /api/v1/learning/logs`
- `POST /api/v1/learning/logs`
- `GET /api/v1/learning/logs/{item_id}`
- `PATCH /api/v1/learning/logs/{item_id}`
- `DELETE /api/v1/learning/logs/{item_id}`
- `GET /api/v1/learning/notes`
- `POST /api/v1/learning/notes`
- `GET /api/v1/learning/notes/{item_id}`
- `PATCH /api/v1/learning/notes/{item_id}`
- `DELETE /api/v1/learning/notes/{item_id}`
- `GET /api/v1/learning/resources`
- `POST /api/v1/learning/resources`
- `GET /api/v1/learning/resources/{item_id}`
- `PATCH /api/v1/learning/resources/{item_id}`
- `DELETE /api/v1/learning/resources/{item_id}`
- `GET /api/v1/learning/items`
- `POST /api/v1/learning/items`
- `GET /api/v1/learning/items/{item_id}`
- `PATCH /api/v1/learning/items/{item_id}`
- `DELETE /api/v1/learning/items/{item_id}`
- `GET /api/v1/learning/interview`
- `POST /api/v1/learning/interview`
- `GET /api/v1/learning/interview/{item_id}`
- `PATCH /api/v1/learning/interview/{item_id}`
- `DELETE /api/v1/learning/interview/{item_id}`
### fitness
- `GET /api/v1/fitness/summary`
- `GET /api/v1/fitness/series`
- `GET /api/v1/fitness/exercises`
- `GET /api/v1/fitness/workouts`
- `POST /api/v1/fitness/workouts`
- `GET /api/v1/fitness/workouts/{wid}`
- `PUT /api/v1/fitness/workouts/{wid}`
- `DELETE /api/v1/fitness/workouts/{wid}`
- `PUT /api/v1/fitness/activity/{day}`
- `GET /api/v1/fitness/activity`
- `POST /api/v1/fitness/import`
- `GET /api/v1/fitness/body`
- `POST /api/v1/fitness/body`
- `GET /api/v1/fitness/body/{item_id}`
- `PATCH /api/v1/fitness/body/{item_id}`
- `DELETE /api/v1/fitness/body/{item_id}`
- `GET /api/v1/fitness/food`
- `POST /api/v1/fitness/food`
- `GET /api/v1/fitness/food/{item_id}`
- `PATCH /api/v1/fitness/food/{item_id}`
- `DELETE /api/v1/fitness/food/{item_id}`
### work
- `GET /api/v1/work/weekly`
- `GET /api/v1/work/projects`
- `GET /api/v1/work/logs`
- `POST /api/v1/work/logs`
- `GET /api/v1/work/logs/{item_id}`
- `PATCH /api/v1/work/logs/{item_id}`
- `DELETE /api/v1/work/logs/{item_id}`
### side-income
- `GET /api/v1/side-income/templates`
- `GET /api/v1/side-income/summary`
- `POST /api/v1/side-income/opportunities/{opp_id}/evaluate`
- `GET /api/v1/side-income/opportunities`
- `POST /api/v1/side-income/opportunities`
- `GET /api/v1/side-income/opportunities/{item_id}`
- `PATCH /api/v1/side-income/opportunities/{item_id}`
- `DELETE /api/v1/side-income/opportunities/{item_id}`
### meta
- `GET /api/health`