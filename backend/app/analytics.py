"""Deterministic analytics shared by the dashboard, reports and the AI context builder.

Everything here is computed from the user's own records; nothing is invented.
"""
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from .access import visible
from .deps import Ctx
from .models import (
    BodyMetric,
    DailyActivity,
    FoodLog,
    Goal,
    Habit,
    HabitLog,
    InterviewItem,
    JournalEntry,
    LearningItem,
    LearningLog,
    Milestone,
    Opportunity,
    Skill,
    Subscription,
    Task,
    Transaction,
    Budget,
    Workout,
    WorkLog,
)

PRIORITY_WEIGHT = {"urgent": 4, "high": 3, "medium": 2, "low": 1}


def prefs(ctx: Ctx) -> dict:
    from .defaults import DEFAULT_PREFERENCES

    p = dict(DEFAULT_PREFERENCES)
    if ctx.user.settings and ctx.user.settings.preferences:
        p.update(ctx.user.settings.preferences)
    return p


def tz(ctx: Ctx) -> ZoneInfo:
    try:
        return ZoneInfo(prefs(ctx).get("timezone") or "Asia/Kolkata")
    except Exception:
        return ZoneInfo("Asia/Kolkata")


def today(ctx: Ctx) -> date:
    return datetime.now(tz(ctx)).date()


def f(x) -> float:
    return float(x) if x is not None else 0.0


def _all(ctx: Ctx, model, *conds, order=None):
    stmt = select(model).where(visible(model, ctx), *conds)
    if order is not None:
        stmt = stmt.order_by(order)
    return ctx.db.scalars(stmt).all()


# ---------------------------------------------------------------- tasks
def task_stats(ctx: Ctx, day: date) -> dict:
    tasks = _all(ctx, Task, Task.status != "cancelled")
    open_tasks = [t for t in tasks if t.status in ("todo", "in_progress")]
    local = tz(ctx)
    done_today = [t for t in tasks if t.completed_at and t.completed_at.astimezone(local).date() == day]
    due_today = [t for t in open_tasks if t.due_date == day]
    overdue = [t for t in open_tasks if t.due_date and t.due_date < day]
    scheduled_today = [t for t in open_tasks if t.scheduled_start and t.scheduled_start.astimezone(local).date() == day]
    by_cat = Counter(t.category for t in open_tasks)
    return {
        "open": len(open_tasks),
        "in_progress": sum(1 for t in open_tasks if t.status == "in_progress"),
        "due_today": due_today,
        "overdue": overdue,
        "done_today": done_today,
        "scheduled_today": scheduled_today,
        "open_by_category": dict(by_cat),
        "frequently_postponed": sorted([t for t in open_tasks if t.postponed_count >= 2], key=lambda t: -t.postponed_count)[:5],
    }


def missed_task_patterns(ctx: Ctx, day: date, days: int = 28) -> dict:
    """Which categories/priorities slip past their due dates most often."""
    start = day - timedelta(days=days)
    tasks = _all(ctx, Task, Task.due_date >= start, Task.due_date < day)
    missed = [t for t in tasks if t.status in ("todo", "in_progress") or (t.completed_at and t.completed_at.date() > t.due_date)]
    total_by_cat = Counter(t.category for t in tasks)
    missed_by_cat = Counter(t.category for t in missed)
    weekday = Counter(t.due_date.strftime("%A") for t in missed)
    return {
        "window_days": days,
        "tasks_due": len(tasks),
        "missed_or_late": len(missed),
        "miss_rate_by_category": {
            c: round(missed_by_cat[c] / n, 2) for c, n in total_by_cat.items() if n >= 2
        },
        "missed_by_weekday": dict(weekday.most_common(3)),
    }


# ---------------------------------------------------------------- habits
def habit_status(ctx: Ctx, day: date) -> list[dict]:
    habits = _all(ctx, Habit, Habit.active.is_(True), order=Habit.created_at)
    start = day - timedelta(days=120)
    logs = _all(ctx, HabitLog, HabitLog.date >= start, HabitLog.date <= day)
    by_habit: dict = defaultdict(set)
    for log in logs:
        by_habit[log.habit_id].add(log.date)
    week_start = day - timedelta(days=day.weekday())
    out = []
    for h in habits:
        dates = by_habit[h.id]
        streak, cursor = 0, day if day in dates else day - timedelta(days=1)
        while cursor in dates:
            streak += 1
            cursor -= timedelta(days=1)
        last30 = sum(1 for d in dates if d > day - timedelta(days=30))
        expected30 = round(h.target_per_week * 30 / 7)
        out.append(
            {
                "id": str(h.id),
                "name": h.name,
                "area": h.area,
                "target_per_week": h.target_per_week,
                "done_today": day in dates,
                "streak": streak,
                "this_week": sum(1 for d in dates if d >= week_start),
                "consistency_30d": round(min(last30 / expected30, 1.0), 2) if expected30 else 0,
                "last_7": [(day - timedelta(days=i)) in dates for i in range(6, -1, -1)],
            }
        )
    return out


# ---------------------------------------------------------------- finance
def month_bounds(month: str) -> tuple[date, date]:
    y, m = map(int, month.split("-"))
    start = date(y, m, 1)
    end = date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)
    return start, end


def finance_month(ctx: Ctx, month: str) -> dict:
    start, end = month_bounds(month)
    txs = _all(ctx, Transaction, Transaction.date >= start, Transaction.date <= end)
    expenses = [t for t in txs if t.kind == "expense"]
    income = [t for t in txs if t.kind == "income"]
    by_cat: dict[str, float] = defaultdict(float)
    for t in expenses:
        by_cat[t.category] += f(t.amount)
    daily: dict[str, float] = defaultdict(float)
    for t in expenses:
        daily[t.date.isoformat()] += f(t.amount)
    budgets = _all(ctx, Budget, Budget.month == month)
    total_budget = next((f(b.amount) for b in budgets if b.category == "__total__"), None)
    if total_budget is None:
        total_budget = f(prefs(ctx).get("monthly_budget")) or None
    cat_budgets = {b.category: f(b.amount) for b in budgets if b.category != "__total__"}
    spent = sum(by_cat.values())
    earned = sum(f(t.amount) for t in income)
    side_income = sum(f(t.amount) for t in income if t.opportunity_id)
    return {
        "month": month,
        "total_expense": round(spent, 2),
        "total_income": round(earned, 2),
        "side_income": round(side_income, 2),
        "net_savings": round(earned - spent, 2),
        "savings_rate": round((earned - spent) / earned, 3) if earned else None,
        "budget": total_budget,
        "budget_used_pct": round(spent / total_budget, 3) if total_budget else None,
        "by_category": dict(sorted(((k, round(v, 2)) for k, v in by_cat.items()), key=lambda kv: -kv[1])),
        "category_budgets": cat_budgets,
        "over_budget_categories": [c for c, b in cat_budgets.items() if by_cat.get(c, 0) > b],
        "daily": dict(sorted(daily.items())),
        "transaction_count": len(txs),
    }


def subscriptions_monthly(ctx: Ctx) -> dict:
    factor = {"weekly": 52 / 12, "monthly": 1, "quarterly": 1 / 3, "yearly": 1 / 12}
    subs = _all(ctx, Subscription, Subscription.active.is_(True))
    items = [{"name": s.name, "monthly": round(f(s.amount) * factor.get(s.billing_cycle, 1), 2), "next_due": s.next_due_date} for s in subs]
    return {"count": len(items), "monthly_total": round(sum(i["monthly"] for i in items), 2), "items": items}


DISCRETIONARY = {"food_delivery", "dining", "shopping", "entertainment", "subscriptions", "travel", "gadgets", "other"}


def spending_flags(ctx: Ctx, month: str) -> list[str]:
    """Plain-language observations about spending, computed from data (no AI)."""
    cur = finance_month(ctx, month)
    y, m = map(int, month.split("-"))
    prev_month = f"{y - (m == 1)}-{(m - 2) % 12 + 1:02d}"
    prev = finance_month(ctx, prev_month)
    flags = []
    for cat, amt in cur["by_category"].items():
        p = prev["by_category"].get(cat, 0)
        if p and amt > p * 1.3 and amt - p > 500:
            flags.append(f"{cat.replace('_', ' ').title()} is up {round((amt / p - 1) * 100)}% vs last month (₹{amt:,.0f} vs ₹{p:,.0f}).")
    for cat in cur["over_budget_categories"]:
        flags.append(f"{cat.replace('_', ' ').title()} is over its budget.")
    if cur["budget_used_pct"] and cur["budget_used_pct"] > 0.9:
        flags.append(f"{round(cur['budget_used_pct'] * 100)}% of the monthly budget is used.")
    disc = sum(v for k, v in cur["by_category"].items() if k in DISCRETIONARY)
    if cur["total_expense"] and disc / cur["total_expense"] > 0.35:
        flags.append(f"Discretionary categories are {round(disc / cur['total_expense'] * 100)}% of spending this month.")
    subs = subscriptions_monthly(ctx)
    if subs["monthly_total"] > 0:
        flags.append(f"{subs['count']} active subscriptions cost about ₹{subs['monthly_total']:,.0f}/month.")
    return flags


# ---------------------------------------------------------------- fitness
def fitness_day(ctx: Ctx, day: date) -> dict:
    p = prefs(ctx)
    food = _all(ctx, FoodLog, FoodLog.date == day)
    act = next(iter(_all(ctx, DailyActivity, DailyActivity.date == day)), None)
    workouts = _all(ctx, Workout, Workout.date == day)
    protein = sum(f(x.protein_g) for x in food)
    return {
        "protein_g": round(protein, 1),
        "protein_target": p["daily_protein_g"],
        "calories": sum(x.calories for x in food),
        "calorie_target": p["daily_calories"],
        "water_ml": act.water_ml if act else 0,
        "water_target": p["daily_water_ml"],
        "steps": act.steps if act else 0,
        "steps_target": p["daily_steps"],
        "sleep_hours": f(act.sleep_hours) if act and act.sleep_hours is not None else None,
        "workouts": [{"title": w.title, "status": w.status, "duration": w.duration_minutes} for w in workouts],
        "worked_out": any(w.status == "done" for w in workouts),
    }


def fitness_week(ctx: Ctx, end: date) -> dict:
    start = end - timedelta(days=6)
    p = prefs(ctx)
    workouts = _all(ctx, Workout, Workout.date >= start, Workout.date <= end)
    done = [w for w in workouts if w.status == "done"]
    food = _all(ctx, FoodLog, FoodLog.date >= start, FoodLog.date <= end)
    acts = _all(ctx, DailyActivity, DailyActivity.date >= start, DailyActivity.date <= end)
    protein_by_day: dict = defaultdict(float)
    cal_by_day: dict = defaultdict(int)
    for x in food:
        protein_by_day[x.date] += f(x.protein_g)
        cal_by_day[x.date] += x.calories
    logged_days = len(protein_by_day)
    metrics = _all(ctx, BodyMetric, BodyMetric.weight_kg.is_not(None), order=BodyMetric.date)
    recent = [m for m in metrics if m.date >= end - timedelta(days=30)]
    weight_change = round(f(recent[-1].weight_kg) - f(recent[0].weight_kg), 2) if len(recent) >= 2 else None
    return {
        "gym_sessions": sum(1 for w in done if w.attended_gym),
        "workouts_done": len(done),
        "workouts_skipped": sum(1 for w in workouts if w.status == "skipped"),
        "gym_target": p["weekly_gym_sessions"],
        "avg_protein_g": round(sum(protein_by_day.values()) / logged_days, 1) if logged_days else None,
        "protein_target_days_hit": sum(1 for v in protein_by_day.values() if v >= p["daily_protein_g"]),
        "avg_calories": round(sum(cal_by_day.values()) / logged_days) if logged_days else None,
        "food_logged_days": logged_days,
        "avg_steps": round(sum(a.steps for a in acts) / len(acts)) if acts else None,
        "avg_water_ml": round(sum(a.water_ml for a in acts) / len(acts)) if acts else None,
        "latest_weight": f(metrics[-1].weight_kg) if metrics else None,
        "latest_body_fat": f(metrics[-1].body_fat_pct) if metrics and metrics[-1].body_fat_pct is not None else None,
        "weight_change_30d": weight_change,
    }


# ---------------------------------------------------------------- learning
def learning_summary(ctx: Ctx, day: date) -> dict:
    p = prefs(ctx)
    week_start = day - timedelta(days=day.weekday())
    logs = _all(ctx, LearningLog, LearningLog.date >= day - timedelta(days=27), LearningLog.date <= day)
    skills = {s.id: s for s in _all(ctx, Skill)}
    by_skill: dict = defaultdict(int)
    for log in logs:
        by_skill[skills[log.skill_id].name if log.skill_id in skills else (log.topic or "General")] += log.minutes
    week_minutes = sum(log.minutes for log in logs if log.date >= week_start)
    gaps = sorted(
        (
            {"skill": s.name, "current": s.current_level, "target": s.target_level, "gap": s.target_level - s.current_level, "status": s.status, "priority": s.priority}
            for s in skills.values()
            if s.target_level > s.current_level
        ),
        key=lambda g: (-PRIORITY_WEIGHT.get(g["priority"], 2), -g["gap"]),
    )
    interviews = _all(ctx, InterviewItem)
    items = _all(ctx, LearningItem)
    return {
        "today_minutes": sum(log.minutes for log in logs if log.date == day),
        "daily_target_minutes": p["daily_learning_minutes"],
        "week_minutes": week_minutes,
        "week_target_minutes": int(p["weekly_learning_hours"] * 60),
        "minutes_by_skill_28d": dict(sorted(by_skill.items(), key=lambda kv: -kv[1])),
        "days_learned_28d": len({log.date for log in logs}),
        "skill_gaps": gaps[:8],
        "interview": {
            "total": len(interviews),
            "confident": sum(1 for i in interviews if i.status == "confident"),
            "weakest": [i.topic for i in sorted(interviews, key=lambda i: i.confidence)[:5]],
        },
        "courses_in_progress": [i.title for i in items if i.status == "in_progress"],
        "completed_items": sum(1 for i in items if i.status == "completed"),
    }


# ---------------------------------------------------------------- goals
def goal_progress(ctx: Ctx) -> list[dict]:
    goals = _all(ctx, Goal, Goal.status == "active", order=Goal.target_date)
    ms = _all(ctx, Milestone)
    by_goal: dict = defaultdict(list)
    for m in ms:
        by_goal[m.goal_id].append(m)
    out = []
    for g in goals:
        mlist = by_goal[g.id]
        if g.target_value is not None and g.current_value is not None:
            start = f(g.start_value)
            span = f(g.target_value) - start
            pct = (f(g.current_value) - start) / span if span else 1.0
        elif mlist:
            pct = sum(m.done for m in mlist) / len(mlist)
        else:
            pct = None
        out.append(
            {
                "id": str(g.id),
                "title": g.title,
                "area": g.area,
                "target_date": g.target_date.isoformat() if g.target_date else None,
                "progress": round(max(0.0, min(pct, 1.0)), 2) if pct is not None else None,
                "milestones_done": sum(m.done for m in mlist),
                "milestones_total": len(mlist),
                "next_milestone": next((m.title for m in sorted(mlist, key=lambda m: (m.due_date or date.max)) if not m.done), None),
            }
        )
    return out


# ---------------------------------------------------------------- work
def work_week(ctx: Ctx, end: date) -> dict:
    start = end - timedelta(days=6)
    logs = _all(ctx, WorkLog, WorkLog.date >= start, WorkLog.date <= end, order=WorkLog.date)
    by_project: dict = defaultdict(float)
    for log in logs:
        by_project[log.project or "General"] += f(log.hours)
    return {
        "days_logged": len({log.date for log in logs}),
        "hours": round(sum(f(log.hours) for log in logs), 1),
        "hours_by_project": dict(by_project),
        "entries": [
            {
                "date": log.date.isoformat(), "project": log.project, "summary": log.summary,
                "completed": log.tasks_completed, "problems": log.problems, "solutions": log.solutions,
                "learnings": log.learnings, "pending": log.pending,
            }
            for log in logs
        ],
    }


# ---------------------------------------------------------------- journal
def journal_summary(ctx: Ctx, end: date, days: int = 30, include_hidden: bool = False) -> dict:
    conds = [JournalEntry.entry_date >= end - timedelta(days=days), JournalEntry.entry_date <= end]
    if not include_hidden:
        conds.append(JournalEntry.hide_from_ai.is_(False))
    entries = _all(ctx, JournalEntry, *conds, order=JournalEntry.entry_date)
    moods = [e.mood for e in entries if e.mood]
    tags = Counter(t for e in entries for t in (e.tags or []))
    return {
        "entries": len(entries),
        "avg_mood": round(sum(moods) / len(moods), 2) if moods else None,
        "mood_series": [{"date": e.entry_date.isoformat(), "mood": e.mood} for e in entries if e.mood],
        "top_tags": dict(tags.most_common(8)),
        "kinds": dict(Counter(e.kind for e in entries)),
        "recent": [
            {"date": e.entry_date.isoformat(), "kind": e.kind, "title": e.title, "mood": e.mood, "body": e.body[:600], "outcome": e.decision_outcome[:300]}
            for e in entries[-12:]
        ],
    }


# ---------------------------------------------------------------- side income
def side_income_summary(ctx: Ctx) -> dict:
    opps = _all(ctx, Opportunity, order=Opportunity.created_at)
    txs = _all(ctx, Transaction, Transaction.opportunity_id.is_not(None))
    rev: dict = defaultdict(float)
    cost: dict = defaultdict(float)
    for t in txs:
        (rev if t.kind == "income" else cost)[t.opportunity_id] += f(t.amount)
    return {
        "opportunities": [
            {
                "id": str(o.id), "title": o.title, "category": o.category, "status": o.status,
                "hours_per_week": f(o.hours_per_week) or None, "est_low": f(o.est_monthly_low) or None,
                "est_high": f(o.est_monthly_high) or None, "revenue": round(rev[o.id], 2), "costs": round(cost[o.id], 2),
                "next_action": o.next_action, "progress_pct": o.progress_pct,
            }
            for o in opps
        ],
        "total_revenue": round(sum(rev.values()), 2),
        "total_costs": round(sum(cost.values()), 2),
        "active_hours_per_week": round(sum(f(o.hours_per_week) for o in opps if o.status in ("active", "validating")), 1),
    }


# ---------------------------------------------------------------- productivity score
def productivity_score(ctx: Ctx, day: date) -> dict:
    """0-100 composite. Components without data/targets are excluded rather than counted as zero."""
    p = prefs(ctx)
    ts = task_stats(ctx, day)
    habits = habit_status(ctx, day)
    learn = learning_summary(ctx, day)
    fit = fitness_day(ctx, day)
    parts: dict[str, tuple[float, float]] = {}  # name -> (score 0..1, weight)
    planned = len(ts["due_today"]) + len(ts["done_today"])
    if planned:
        parts["tasks"] = (len(ts["done_today"]) / planned, 0.4)
    daily_habits = [h for h in habits]
    if daily_habits:
        parts["habits"] = (sum(h["done_today"] for h in daily_habits) / len(daily_habits), 0.25)
    if p["daily_learning_minutes"]:
        parts["learning"] = (min(learn["today_minutes"] / p["daily_learning_minutes"], 1.0), 0.15)
    fit_bits = [min(fit["protein_g"] / fit["protein_target"], 1.0) if fit["protein_target"] else 0]
    fit_bits.append(1.0 if fit["worked_out"] else min(fit["steps"] / fit["steps_target"], 1.0) if fit["steps_target"] else 0)
    parts["fitness"] = (sum(fit_bits) / len(fit_bits), 0.2)
    total_w = sum(w for _, w in parts.values())
    score = round(sum(s * w for s, w in parts.values()) / total_w * 100) if total_w else 0
    return {"score": score, "components": {k: round(s * 100) for k, (s, _) in parts.items()}}


def day_window(ctx: Ctx, day: date) -> tuple[datetime, datetime]:
    p = prefs(ctx)
    local = tz(ctx)
    start = datetime.combine(day, time.fromisoformat(p.get("day_start", "09:00")), local)
    end = datetime.combine(day, time.fromisoformat(p.get("day_end", "21:00")), local)
    return start, end


def utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc)


def dec(x) -> Decimal:
    return Decimal(str(x))
