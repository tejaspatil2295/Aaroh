from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select

from .. import analytics as A
from ..access import visible
from ..deps import Ctx, get_ctx
from ..models import AIInsight, Task, WorkLog

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _t(t: Task) -> dict:
    return {
        "id": str(t.id), "title": t.title, "category": t.category, "priority": t.priority, "status": t.status,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "scheduled_start": t.scheduled_start.isoformat() if t.scheduled_start else None,
        "estimate_minutes": t.estimate_minutes,
    }


@router.get("", summary="Everything for 'My life at a glance'")
def dashboard(ctx: Ctx = Depends(get_ctx)):
    day = A.today(ctx)
    month = day.strftime("%Y-%m")
    ts = A.task_stats(ctx, day)
    fm = A.finance_month(ctx, month)
    learn = A.learning_summary(ctx, day)
    work_today = ctx.db.scalars(select(WorkLog).where(visible(WorkLog, ctx), WorkLog.date == day)).all()
    insights = {}
    for kind in ("morning_briefing", "evening_review"):
        ins = ctx.db.scalars(
            select(AIInsight).where(visible(AIInsight, ctx), AIInsight.owner_id == ctx.user_id, AIInsight.kind == kind, AIInsight.period_start == day).order_by(AIInsight.created_at.desc())
        ).first()
        insights[kind] = {"content": ins.content, "is_fallback": ins.is_fallback, "created_at": ins.created_at.isoformat()} if ins else None
    week = []
    for i in range(6, -1, -1):
        d = day - timedelta(days=i)
        week.append({"date": d.isoformat(), "score": A.productivity_score(ctx, d)["score"]})
    upcoming = ctx.db.scalars(
        select(Task).where(visible(Task, ctx), Task.status.in_(["todo", "in_progress"]), Task.due_date > day, Task.due_date <= day + timedelta(days=7)).order_by(Task.due_date).limit(8)
    ).all()
    return {
        "date": day.isoformat(),
        "greeting_name": (ctx.user.full_name or "").split(" ")[0],
        "productivity": A.productivity_score(ctx, day),
        "productivity_week": week,
        "tasks": {
            "open": ts["open"],
            "in_progress": ts["in_progress"],
            "due_today": [_t(t) for t in ts["due_today"]],
            "overdue": [_t(t) for t in ts["overdue"]],
            "done_today": [_t(t) for t in ts["done_today"]],
            "scheduled_today": [_t(t) for t in sorted(ts["scheduled_today"], key=lambda t: t.scheduled_start)],
            "upcoming": [_t(t) for t in upcoming],
        },
        "finance": {
            "today_expense": fm["daily"].get(day.isoformat(), 0),
            "month_expense": fm["total_expense"],
            "month_income": fm["total_income"],
            "budget": fm["budget"],
            "budget_used_pct": fm["budget_used_pct"],
            "top_categories": dict(list(fm["by_category"].items())[:4]),
        },
        "fitness": A.fitness_day(ctx, day),
        "fitness_week": A.fitness_week(ctx, day),
        "learning": {k: learn[k] for k in ("today_minutes", "daily_target_minutes", "week_minutes", "week_target_minutes", "courses_in_progress")},
        "work_today": [{"project": w.project, "summary": w.summary, "hours": float(w.hours or 0)} for w in work_today],
        "goals": A.goal_progress(ctx)[:6],
        "habits": A.habit_status(ctx, day),
        "insights": insights,
    }
