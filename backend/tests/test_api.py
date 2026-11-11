from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

from .conftest import make_user

API = "/api/v1"
D0 = datetime.now(ZoneInfo("Asia/Kolkata")).date()
TODAY = D0.isoformat()


# ---------------------------------------------------------------- auth
def test_register_login_refresh_rotation_and_reuse_detection(client):
    u = make_user(client)
    assert client.get(f"{API}/users/me", headers=u["headers"]).json()["email"] == u["email"]
    bad = client.post(f"{API}/auth/login", json={"email": u["email"], "password": "wrong-password"})
    assert bad.status_code == 401
    ok = client.post(f"{API}/auth/login", json={"email": u["email"], "password": "S3cure-pass!"})
    assert ok.status_code == 200
    rt1 = ok.json()["refresh_token"]
    r2 = client.post(f"{API}/auth/refresh", json={"refresh_token": rt1})
    assert r2.status_code == 200
    rt2 = r2.json()["refresh_token"]
    # Reusing the rotated token revokes the whole family, including rt2.
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": rt1}).status_code == 401
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": rt2}).status_code == 401


def test_refresh_via_cookie_and_logout(client):
    u = make_user(client)
    r = client.post(f"{API}/auth/login", json={"email": u["email"], "password": "S3cure-pass!"})
    assert "aaroh_refresh" in r.cookies or client.cookies.get("aaroh_refresh")
    r2 = client.post(f"{API}/auth/refresh")
    assert r2.status_code == 200
    client.post(f"{API}/auth/logout")
    client.cookies.clear()
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": r2.json()["refresh_token"]}).status_code == 401


def test_requires_auth_and_validates_input(client, user):
    assert client.get(f"{API}/tasks").status_code == 401
    assert client.get(f"{API}/tasks", headers={"Authorization": "Bearer junk"}).status_code == 401
    assert client.post(f"{API}/auth/register", json={"email": "not-an-email", "password": "x"}).status_code == 422
    r = client.post(f"{API}/finance/transactions", headers=user["headers"], json={"amount": -5, "date": TODAY})
    assert r.status_code == 422
    r = client.post(f"{API}/tasks", headers=user["headers"], json={"title": "x", "priority": "galactic"})
    assert r.status_code == 422


# ---------------------------------------------------------------- isolation
def test_private_data_is_isolated_between_users(client):
    a, b = make_user(client, "A"), make_user(client, "B")
    j = client.post(f"{API}/journal", headers=a["headers"], json={"title": "secret", "body": "private thoughts", "entry_date": TODAY}).json()
    t = client.post(f"{API}/finance/transactions", headers=a["headers"], json={"amount": 500, "date": TODAY, "category": "dining"}).json()
    assert client.get(f"{API}/journal", headers=b["headers"]).json() == []
    assert client.get(f"{API}/finance/transactions", headers=b["headers"]).json() == []
    assert client.get(f"{API}/journal/{j['id']}", headers=b["headers"]).status_code == 404
    assert client.patch(f"{API}/journal/{j['id']}", headers=b["headers"], json={"title": "hacked"}).status_code == 404
    assert client.delete(f"{API}/finance/transactions/{t['id']}", headers=b["headers"]).status_code == 404
    assert client.get(f"{API}/finance/summary", headers=b["headers"]).json()["total_expense"] == 0
    # Cannot reference another user's goal either.
    g = client.post(f"{API}/goals", headers=a["headers"], json={"title": "A's goal"}).json()
    assert client.post(f"{API}/tasks", headers=b["headers"], json={"title": "t", "goal_id": g["id"]}).status_code == 404
    # Workspace header for someone else's workspace is rejected.
    assert client.get(f"{API}/tasks", headers={**b["headers"], "X-Workspace-Id": "00000000-0000-0000-0000-000000000000"}).status_code == 403


# ---------------------------------------------------------------- tasks & planning
def test_task_lifecycle_recurrence_and_postpone(client, user):
    h = user["headers"]
    t = client.post(f"{API}/tasks", headers=h, json={"title": "Standup", "recurrence": "daily", "due_date": TODAY, "category": "professional"}).json()
    done = client.post(f"{API}/tasks/{t['id']}/complete", headers=h).json()
    assert done["status"] == "done" and done["completed_at"]
    nxt = client.get(f"{API}/tasks", headers=h, params={"status": "todo", "q": "Standup"}).json()
    assert len(nxt) == 1 and nxt[0]["due_date"] == (D0 + timedelta(days=1)).isoformat()
    p = client.post(f"{API}/tasks", headers=h, json={"title": "Resume", "due_date": TODAY}).json()
    p2 = client.patch(f"{API}/tasks/{p['id']}", headers=h, json={"due_date": (D0 + timedelta(days=2)).isoformat()}).json()
    assert p2["postponed_count"] == 1
    cal = client.get(f"{API}/tasks/calendar", headers=h, params={"from": TODAY, "to": (D0 + timedelta(days=7)).isoformat()}).json()
    assert {x["title"] for x in cal} >= {"Standup", "Resume"}
    assert client.delete(f"{API}/tasks/{p['id']}", headers=h).status_code == 204


def test_smart_plan_orders_by_urgency_and_fits_window(client, user):
    h = user["headers"]
    tomorrow = (D0 + timedelta(days=1)).isoformat()
    client.post(f"{API}/tasks", headers=h, json={"title": "Low thing", "priority": "low", "estimate_minutes": 30, "due_date": tomorrow})
    client.post(f"{API}/tasks", headers=h, json={"title": "Urgent thing", "priority": "urgent", "estimate_minutes": 60, "due_date": tomorrow})
    client.post(f"{API}/tasks", headers=h, json={"title": "Huge thing", "priority": "medium", "estimate_minutes": 600, "due_date": tomorrow})
    r = client.post(f"{API}/tasks/plan", headers=h, json={"date": tomorrow, "start": "09:00", "end": "12:00", "apply": True}).json()
    titles = [x["title"] for x in r["plan"]]
    assert titles[0] == "Urgent thing" and "Low thing" in titles
    assert any(u["title"] == "Huge thing" for u in r["unscheduled"])
    urgent = client.get(f"{API}/tasks", headers=h, params={"q": "Urgent thing"}).json()[0]
    assert urgent["scheduled_start"] is not None


def test_goals_milestones_and_habits(client, user):
    h = user["headers"]
    g = client.post(f"{API}/goals", headers=h, json={"title": "Ship portfolio", "area": "career"}).json()
    m = client.post(f"{API}/milestones", headers=h, json={"goal_id": g["id"], "title": "MVP"}).json()
    client.post(f"{API}/milestones", headers=h, json={"goal_id": g["id"], "title": "Deploy"})
    client.patch(f"{API}/milestones/{m['id']}", headers=h, json={"done": True})
    prog = client.get(f"{API}/goals/progress", headers=h).json()[0]
    assert prog["progress"] == 0.5 and prog["next_milestone"] == "Deploy"
    hb = client.post(f"{API}/habits", headers=h, json={"name": "Read", "target_per_week": 7}).json()
    yesterday = (D0 - timedelta(days=1)).isoformat()
    client.post(f"{API}/habits/{hb['id']}/toggle", headers=h, params={"date": yesterday})
    assert client.post(f"{API}/habits/{hb['id']}/toggle", headers=h).json()["done"] is True
    st = client.get(f"{API}/habits/status", headers=h).json()[0]
    assert st["streak"] == 2 and st["done_today"]
    assert client.post(f"{API}/habits/{hb['id']}/toggle", headers=h).json()["done"] is False


# ---------------------------------------------------------------- finance
def test_finance_summary_budgets_and_subscriptions(client, user):
    h = user["headers"]
    month = D0.strftime("%Y-%m")
    client.post(f"{API}/finance/transactions", headers=h, json={"kind": "income", "amount": 50000, "date": TODAY, "category": "salary"})
    client.post(f"{API}/finance/transactions", headers=h, json={"amount": "1200.50", "date": TODAY, "category": "food_delivery"})
    client.post(f"{API}/finance/transactions", headers=h, json={"amount": 800, "date": TODAY, "category": "groceries"})
    client.post(f"{API}/finance/budgets", headers=h, json={"month": month, "amount": 10000})
    client.post(f"{API}/finance/budgets", headers=h, json={"month": month, "category": "food_delivery", "amount": 1000})
    assert client.post(f"{API}/finance/budgets", headers=h, json={"month": month, "amount": 5}).status_code == 409
    client.post(f"{API}/finance/subscriptions", headers=h, json={"name": "Netflix", "amount": 649})
    client.post(f"{API}/finance/subscriptions", headers=h, json={"name": "Course", "amount": 1200, "billing_cycle": "yearly"})
    s = client.get(f"{API}/finance/summary", headers=h).json()
    assert s["total_expense"] == 2000.5 and s["total_income"] == 50000
    assert s["budget"] == 10000 and abs(s["budget_used_pct"] - 0.2) < 0.001
    assert s["over_budget_categories"] == ["food_delivery"]
    assert s["subscriptions"]["monthly_total"] == 749.0
    assert any("over its budget" in o for o in s["observations"])
    assert len(client.get(f"{API}/finance/trends", headers=h, params={"months": 3}).json()) == 3
    assert client.get(f"{API}/finance/transactions", headers=h, params={"kind": "expense", "q": "food"}).json()[0]["category"] == "food_delivery"


# ---------------------------------------------------------------- journal
def test_journal_search_tags_and_photo(client, user):
    h = user["headers"]
    e = client.post(f"{API}/journal", headers=h, json={"title": "Trek", "body": "Rajmachi in the rain", "kind": "travel", "entry_date": TODAY, "mood": 5, "tags": ["travel", "friends"]}).json()
    client.post(f"{API}/journal", headers=h, json={"title": "Work", "body": "Long day", "entry_date": TODAY, "mood": 2, "tags": ["work"]})
    assert [x["title"] for x in client.get(f"{API}/journal", headers=h, params={"q": "rajmachi"}).json()] == ["Trek"]
    assert client.get(f"{API}/journal/tags", headers=h).json()["travel"] == 1
    assert client.get(f"{API}/journal/mood", headers=h).json()["avg_mood"] == 3.5
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 100
    up = client.post(f"{API}/attachments", headers=h, params={"entity_type": "journal", "entity_id": e["id"]}, files={"file": ("p.png", png, "image/png")})
    assert up.status_code == 201
    assert client.get(f"{API}/attachments/{up.json()['id']}/file", headers=h).content == png
    bad = client.post(f"{API}/attachments", headers=h, params={"entity_type": "journal", "entity_id": e["id"]}, files={"file": ("x.exe", b"MZ", "application/octet-stream")})
    assert bad.status_code == 415
    assert client.get(f"{API}/journal", headers=h, params={"mood": "5"}).json()[0]["title"] == "Trek"


# ---------------------------------------------------------------- learning
def test_learning_hub(client, user):
    h = user["headers"]
    s = client.post(f"{API}/learning/skills", headers=h, json={"name": "System Design", "current_level": 2, "target_level": 4, "priority": "high"}).json()
    client.post(f"{API}/learning/roadmap", headers=h, json={"skill_id": s["id"], "title": "Caching", "done": True})
    client.post(f"{API}/learning/roadmap", headers=h, json={"skill_id": s["id"], "title": "Sharding"})
    client.post(f"{API}/learning/logs", headers=h, json={"date": TODAY, "minutes": 45, "skill_id": s["id"]})
    client.post(f"{API}/learning/notes", headers=h, json={"title": "Snippet", "kind": "snippet", "language": "python", "content": "print(1)"})
    client.post(f"{API}/learning/resources", headers=h, json={"title": "DDIA", "kind": "book"})
    client.post(f"{API}/learning/items", headers=h, json={"title": "Course", "status": "completed"})
    client.post(f"{API}/learning/interview", headers=h, json={"topic": "LRU cache", "confidence": 2})
    sm = client.get(f"{API}/learning/summary", headers=h).json()
    assert sm["today_minutes"] == 45 and sm["skill_gaps"][0]["skill"] == "System Design"
    assert sm["roadmap_progress"][s["id"]] == {"done": 1, "total": 2}
    assert sm["interview"]["weakest"] == ["LRU cache"] and sm["completed_items"] == 1
    assert client.get(f"{API}/learning/daily", headers=h, params={"days": 7}).json()[-1]["minutes"] == 45


# ---------------------------------------------------------------- fitness
def test_fitness_tracking(client, user):
    h = user["headers"]
    w = client.post(f"{API}/fitness/workouts", headers=h, json={"date": TODAY, "title": "Push", "duration_minutes": 60,
                                                                  "sets": [{"exercise": "Bench", "set_number": 1, "reps": 8, "weight_kg": 60}, {"exercise": "Bench", "set_number": 2, "reps": 8, "weight_kg": 62.5}]})
    assert w.status_code == 201 and len(w.json()["sets"]) == 2
    client.post(f"{API}/fitness/food", headers=h, json={"date": TODAY, "food": "Paneer", "protein_g": 30, "calories": 350})
    client.post(f"{API}/fitness/food", headers=h, json={"date": TODAY, "food": "Whey", "protein_g": 24, "calories": 120})
    client.put(f"{API}/fitness/activity/{TODAY}", headers=h, json={"steps": 9000})
    client.put(f"{API}/fitness/activity/{TODAY}", headers=h, json={"add_water_ml": 250})
    a = client.put(f"{API}/fitness/activity/{TODAY}", headers=h, json={"add_water_ml": 250}).json()
    assert a["water_ml"] == 500 and a["steps"] == 9000
    client.post(f"{API}/fitness/body", headers=h, json={"date": TODAY, "weight_kg": 82.4, "body_fat_pct": 20.1})
    s = client.get(f"{API}/fitness/summary", headers=h).json()
    assert s["today"]["protein_g"] == 54 and s["today"]["worked_out"] and s["week"]["latest_weight"] == 82.4
    assert client.get(f"{API}/fitness/exercises", headers=h).json()[0]["best_weight"] == 62.5
    imp = client.post(f"{API}/fitness/import", headers=h, json={"source": "health_connect", "records": [{"type": "steps", "date": TODAY, "value": 10000, "external_id": "s1"}]}).json()
    assert imp["updated"] == 1


# ---------------------------------------------------------------- work & side income
def test_work_journal_and_side_income(client, user):
    h = user["headers"]
    client.post(f"{API}/work/logs", headers=h, json={"date": TODAY, "project": "Billing", "summary": "Retries", "solutions": "Idempotency keys", "hours": 8})
    wk = client.get(f"{API}/work/weekly", headers=h).json()
    assert wk["hours"] == 8 and wk["hours_by_project"] == {"Billing": 8}
    assert client.get(f"{API}/work/logs", headers=h, params={"q": "idempotency"}).json()[0]["project"] == "Billing"
    o = client.post(f"{API}/side-income/opportunities", headers=h, json={"title": "Mentorship", "category": "upsc_mentorship", "hours_per_week": 4}).json()
    client.post(f"{API}/finance/transactions", headers=h, json={"kind": "income", "amount": 1500, "date": TODAY, "category": "teaching", "opportunity_id": o["id"]})
    s = client.get(f"{API}/side-income/summary", headers=h).json()
    assert s["total_revenue"] == 1500 and s["opportunities"][0]["revenue"] == 1500
    assert len(client.get(f"{API}/side-income/templates", headers=h).json()) >= 6
    # Evaluation requires a real AI provider; offline mode says so instead of faking it.
    assert client.post(f"{API}/side-income/opportunities/{o['id']}/evaluate", headers=h).status_code == 503


# ---------------------------------------------------------------- dashboard, settings, AI
def test_dashboard_settings_and_offline_ai(client, user):
    h = user["headers"]
    client.post(f"{API}/tasks", headers=h, json={"title": "Do it", "due_date": TODAY})
    d = client.get(f"{API}/dashboard", headers=h).json()
    assert d["tasks"]["due_today"][0]["title"] == "Do it" and 0 <= d["productivity"]["score"] <= 100
    st = client.patch(f"{API}/users/me/settings", headers=h, json={"preferences": {"daily_protein_g": 140}, "ai_permissions": {"finance": False}}).json()
    assert st["preferences"]["daily_protein_g"] == 140 and st["ai_permissions"]["finance"] is False
    assert client.patch(f"{API}/users/me/settings", headers=h, json={"preferences": {"bogus": 1}}).status_code == 422
    preview = client.get(f"{API}/ai/context-preview", headers=h).json()
    assert "finance" not in preview["modules"] and "## Finance" not in preview["context"]
    assert "## Personal journal" not in preview["context"]  # journal is opt-in
    chat = client.post(f"{API}/ai/chat", headers=h, json={"message": "What should I focus on?"}).json()
    assert chat["message"]["is_fallback"] is True and "Offline insights" in chat["message"]["content"]
    ins = client.post(f"{API}/ai/insights", headers=h, json={"kind": "evening_review"}).json()
    assert ins["is_fallback"] and ins["provider"] == "offline"
    assert client.post(f"{API}/tasks/breakdown", headers=h, json={"title": "Learn Kubernetes"}).status_code == 503


def test_openai_compatible_provider_uses_user_key_and_context(client, user, monkeypatch):
    h = user["headers"]
    client.patch(f"{API}/users/me", headers=h, json={"about": "Ex-UPSC aspirant turned developer"})
    st = client.patch(f"{API}/users/me/settings", headers=h, json={"ai_provider": "openai_compatible", "ai_model": "test-model", "ai_base_url": "http://llm.local/v1", "ai_api_key": "sk-test-123"}).json()
    assert st["ai_key_set"] and st["ai_effective"]["mode"] == "ai" and "sk-test" not in str(st)
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.update(url=url, body=json, headers=headers)
        content = '[{"title":"Install kind","estimate_minutes":30,"priority":"high","day_offset":0}]' if "JSON array" in json["messages"][-1]["content"] else "Focus on your resume."
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    monkeypatch.setattr("app.ai.providers.httpx.post", fake_post)
    r = client.post(f"{API}/ai/chat", headers=h, json={"message": "Help me", "persona": "career_mentor"}).json()
    assert r["message"]["content"] == "Focus on your resume." and r["message"]["provider"] == "openai_compatible"
    assert captured["url"] == "http://llm.local/v1/chat/completions" and captured["headers"]["Authorization"] == "Bearer sk-test-123"
    system = captured["body"]["messages"][0]["content"]
    assert "Ex-UPSC aspirant" in system and "Career Mentor" in system
    # Follow-up keeps history.
    client.post(f"{API}/ai/chat", headers=h, json={"message": "More", "persona": "career_mentor", "conversation_id": r["conversation"]["id"]})
    assert [m["content"] for m in captured["body"]["messages"][1:]] == ["Help me", "Focus on your resume.", "More"]
    b = client.post(f"{API}/tasks/breakdown", headers=h, json={"title": "Learn Kubernetes", "create": True, "category": "learning"}).json()
    assert b["items"][0]["title"] == "Install kind" and len(b["created"]) == 1


# ---------------------------------------------------------------- export & deletion
def test_export_and_delete_account(client):
    u = make_user(client)
    h = u["headers"]
    client.post(f"{API}/journal", headers=h, json={"title": "Mine", "entry_date": TODAY})
    client.post(f"{API}/fitness/workouts", headers=h, json={"date": TODAY, "title": "Legs", "sets": [{"exercise": "Squat", "reps": 5, "weight_kg": 80}]})
    ex = client.get(f"{API}/users/me/export", headers=h).json()
    assert ex["journal_entries"][0]["title"] == "Mine" and ex["workouts"][0]["sets"][0]["exercise"] == "Squat"
    assert "password_hash" not in ex["user"]
    assert client.request("DELETE", f"{API}/users/me", headers=h, json={"password": "wrong-password", "confirm": "DELETE"}).status_code == 400
    assert client.request("DELETE", f"{API}/users/me", headers=h, json={"password": "S3cure-pass!", "confirm": "DELETE"}).status_code == 204
    assert client.get(f"{API}/users/me", headers=h).status_code == 401
    assert client.post(f"{API}/auth/login", json={"email": u["email"], "password": "S3cure-pass!"}).status_code == 401
