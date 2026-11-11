"""Tasks, goals, milestones, habits, calendar and smart scheduling."""
import calendar
from datetime import date as _Date
from typing import Optional
import json
import re
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from .. import analytics as A
from .. import schemas as S
from ..access import get_owned, visible
from ..ai.service import complete
from ..crud import assert_ref, crud_router
from ..deps import Ctx, get_ctx
from ..models import Goal, Habit, HabitLog, Milestone, Task

TaskOut = S.read(S.TaskIn, "TaskOut", completed_at=(datetime | None, None), postponed_count=(int, 0))
GoalOut = S.read(S.GoalIn, "GoalOut")
MilestoneOut = S.read(S.MilestoneIn, "MilestoneOut", completed_at=(datetime | None, None))
HabitOut = S.read(S.HabitIn, "HabitOut")
HabitLogOut = S.read(S.HabitLogIn, "HabitLogOut")

router = APIRouter(tags=["tasks"])


def _task_hook(obj: Task, ctx: Ctx, data: dict) -> None:
    assert_ref(Goal, data.get("goal_id"), ctx)
    if data.get("parent_id"):
        assert_ref(Task, data["parent_id"], ctx)
        if obj.id is not None and data["parent_id"] == obj.id:
            raise HTTPException(422, "A task cannot be its own parent")
    if "due_date" in data and obj.due_date and data["due_date"] and data["due_date"] > obj.due_date:
        obj.postponed_count = (obj.postponed_count or 0) + 1
    if "status" in data:
        if data["status"] == "done" and obj.status != "done":
            obj.completed_at = datetime.now(timezone.utc)
        elif data["status"] != "done":
            obj.completed_at = None


def _task_after(obj: Task, ctx: Ctx, data: dict) -> None:
    if data.get("status") == "done":
        spawn_next_occurrence(obj, ctx)


def next_due(d: date, rule: str) -> date | None:
    if rule == "daily":
        return d + timedelta(days=1)
    if rule == "weekdays":
        n = d + timedelta(days=1)
        while n.weekday() >= 5:
            n += timedelta(days=1)
        return n
    if rule == "weekly":
        return d + timedelta(days=7)
    if rule == "monthly":
        y, m = d.year + (d.month == 12), d.month % 12 + 1
        return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))
    return None


def spawn_next_occurrence(t: Task, ctx: Ctx) -> Task | None:
    if t.recurrence == "none":
        return None
    base = t.due_date or A.today(ctx)
    nd = next_due(base, t.recurrence)
    exists = ctx.db.scalar(
        select(Task).where(visible(Task, ctx), Task.title == t.title, Task.due_date == nd, Task.recurrence == t.recurrence)
    )
    if exists:
        return None
    shift = (nd - base) if nd else timedelta()
    new = Task(
        owner_id=t.owner_id, workspace_id=t.workspace_id, visibility=t.visibility, title=t.title,
        description=t.description, category=t.category, priority=t.priority, status="todo", due_date=nd,
        scheduled_start=(t.scheduled_start + shift) if t.scheduled_start else None,
        reminder_at=(t.reminder_at + shift) if t.reminder_at else None,
        estimate_minutes=t.estimate_minutes, recurrence=t.recurrence, goal_id=t.goal_id, tags=list(t.tags or []),
    )
    ctx.db.add(new)
    ctx.db.commit()
    return new


# ---------------------------------------------------------------- custom task endpoints (before CRUD routes)
@router.get("/tasks/calendar", response_model=list[TaskOut], summary="Tasks due or scheduled in a date range")
def calendar_view(start: date = Query(alias="from"), end: date = Query(alias="to"), ctx: Ctx = Depends(get_ctx)):
    if (end - start).days > 62:
        raise HTTPException(422, "Range too large (max 62 days)")
    local = A.tz(ctx)
    s_dt = datetime.combine(start, datetime.min.time(), local)
    e_dt = datetime.combine(end + timedelta(days=1), datetime.min.time(), local)
    stmt = select(Task).where(
        visible(Task, ctx),
        Task.status != "cancelled",
        ((Task.due_date >= start) & (Task.due_date <= end)) | ((Task.scheduled_start >= s_dt) & (Task.scheduled_start < e_dt)),
    ).order_by(Task.scheduled_start.nulls_last(), Task.due_date)
    return ctx.db.scalars(stmt).all()


class PlanIn(BaseModel):
    date: Optional[_Date] = None
    start: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    end: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    apply: bool = False


@router.post("/tasks/plan", summary="Smart daily plan: fit open tasks into free time by priority and urgency")
def plan_day(payload: PlanIn, ctx: Ctx = Depends(get_ctx)):
    day = payload.date or A.today(ctx)
    p = A.prefs(ctx)
    local = A.tz(ctx)
    win_start, win_end = A.day_window(ctx, day)
    if payload.start:
        win_start = datetime.combine(day, datetime.strptime(payload.start, "%H:%M").time(), local)
    if payload.end:
        win_end = datetime.combine(day, datetime.strptime(payload.end, "%H:%M").time(), local)
    now = datetime.now(local)
    if day == now.date() and now > win_start:
        win_start = (now + timedelta(minutes=15 - now.minute % 15)).replace(second=0, microsecond=0)
    tasks = ctx.db.scalars(select(Task).where(visible(Task, ctx), Task.status.in_(["todo", "in_progress"]))).all()
    fixed = sorted(
        [t for t in tasks if t.scheduled_start and t.scheduled_start.astimezone(local).date() == day],
        key=lambda t: t.scheduled_start,
    )
    busy = [(t.scheduled_start.astimezone(local), t.scheduled_start.astimezone(local) + timedelta(minutes=t.estimate_minutes or 30)) for t in fixed]

    def score(t: Task) -> float:
        s = A.PRIORITY_WEIGHT[t.priority] * 10
        if t.due_date:
            days = (t.due_date - day).days
            s += 30 if days < 0 else 20 if days == 0 else max(0, 10 - days)
        s += min(t.postponed_count, 3) * 3  # bring avoided tasks forward
        s += 2 if t.status == "in_progress" else 0
        return s

    candidates = sorted(
        [t for t in tasks if t not in fixed and (t.due_date is None or t.due_date <= day + timedelta(days=7))],
        key=score, reverse=True,
    )
    plan, unscheduled = [], []
    cursor = win_start
    brk = timedelta(minutes=p.get("break_minutes", 15))
    for t in candidates:
        dur = timedelta(minutes=t.estimate_minutes or 30)
        slot = cursor
        placed = False
        while slot + dur <= win_end:
            clash = next(((b0, b1) for b0, b1 in busy if slot < b1 and slot + dur > b0), None)
            if clash:
                slot = clash[1]
                continue
            plan.append({"task_id": str(t.id), "title": t.title, "priority": t.priority, "category": t.category, "start": slot.isoformat(), "end": (slot + dur).isoformat(), "reason": _reason(t, day)})
            busy.append((slot, slot + dur))
            cursor = slot + dur + (brk if dur >= timedelta(minutes=45) else timedelta())
            placed = True
            if payload.apply:
                t.scheduled_start = slot.astimezone(timezone.utc)
            break
        if not placed:
            unscheduled.append({"task_id": str(t.id), "title": t.title, "priority": t.priority})
    if payload.apply:
        ctx.db.commit()
    for t in fixed:
        plan.append({"task_id": str(t.id), "title": t.title, "priority": t.priority, "category": t.category, "start": t.scheduled_start.astimezone(local).isoformat(), "end": (t.scheduled_start.astimezone(local) + timedelta(minutes=t.estimate_minutes or 30)).isoformat(), "reason": "Already scheduled", "fixed": True})
    plan.sort(key=lambda x: x["start"])
    free = (win_end - win_start).total_seconds() / 60
    used = sum((datetime.fromisoformat(x["end"]) - datetime.fromisoformat(x["start"])).total_seconds() / 60 for x in plan)
    return {"date": day.isoformat(), "window": [win_start.isoformat(), win_end.isoformat()], "plan": plan, "unscheduled": unscheduled[:20], "planned_minutes": round(used), "available_minutes": round(max(free, 0)), "applied": payload.apply}


def _reason(t: Task, day: date) -> str:
    if t.due_date and t.due_date < day:
        return f"Overdue since {t.due_date.isoformat()}"
    if t.due_date == day:
        return "Due today"
    if t.postponed_count >= 2:
        return f"Postponed {t.postponed_count} times"
    return f"{t.priority.title()} priority"


@router.post("/tasks/{task_id}/complete", response_model=TaskOut)
def complete_task(task_id: uuid.UUID, ctx: Ctx = Depends(get_ctx)):
    t = get_owned(Task, task_id, ctx, write=True)
    if t.status != "done":
        t.status = "done"
        t.completed_at = datetime.now(timezone.utc)
        ctx.db.commit()
        spawn_next_occurrence(t, ctx)
    return t


class BreakdownIn(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    context: str = Field(default="", max_length=2000)
    goal_id: uuid.UUID | None = None
    category: S.TaskCategory = "personal"
    create: bool = False


@router.post("/tasks/breakdown", summary="AI: break a goal or big task into actionable sub-tasks")
def breakdown(payload: BreakdownIn, ctx: Ctx = Depends(get_ctx)):
    assert_ref(Goal, payload.goal_id, ctx)
    prompt = (
        f"Break this into 4-8 concrete, actionable tasks that each take 15-120 minutes:\n\"{payload.title}\"\n"
        f"Extra context: {payload.context or 'none'}\n"
        "Reply with ONLY a JSON array, no prose. Each item: {\"title\": str, \"estimate_minutes\": int, \"priority\": \"low|medium|high\", \"day_offset\": int (days from today to schedule it)}."
    )
    res = complete(ctx, "life_coach", [{"role": "user", "content": prompt}], focus={"profile", "goals", "tasks"})
    if res is None:
        raise HTTPException(503, "Breaking tasks down needs an AI provider. Add one in Settings > AI.")
    m = re.search(r"\[.*\]", res.text, re.S)
    try:
        items = json.loads(m.group(0)) if m else []
    except json.JSONDecodeError:
        items = []
    clean = []
    for it in items[:10]:
        if isinstance(it, dict) and str(it.get("title", "")).strip():
            clean.append({
                "title": str(it["title"])[:300],
                "estimate_minutes": max(5, min(int(it.get("estimate_minutes") or 30), 480)),
                "priority": it.get("priority") if it.get("priority") in ("low", "medium", "high") else "medium",
                "day_offset": max(0, min(int(it.get("day_offset") or 0), 90)),
            })
    if not clean:
        raise HTTPException(502, "The AI response could not be parsed into tasks. Try rephrasing.")
    created = []
    if payload.create:
        today = A.today(ctx)
        parent = Task(owner_id=ctx.user_id, workspace_id=ctx.workspace_id, title=payload.title, category=payload.category, goal_id=payload.goal_id, priority="high")
        ctx.db.add(parent)
        ctx.db.flush()
        for it in clean:
            t = Task(owner_id=ctx.user_id, workspace_id=ctx.workspace_id, title=it["title"], category=payload.category, priority=it["priority"], estimate_minutes=it["estimate_minutes"], due_date=today + timedelta(days=it["day_offset"]), parent_id=parent.id, goal_id=payload.goal_id)
            ctx.db.add(t)
            created.append(t)
        ctx.db.commit()
    return {"items": clean, "created": [str(t.id) for t in created], "provider": res.provider, "model": res.model}


# ---------------------------------------------------------------- habits
@router.post("/habits/{habit_id}/toggle", summary="Mark or unmark a habit for a day")
def toggle_habit(habit_id: uuid.UUID, day: date | None = Query(default=None, alias="date"), ctx: Ctx = Depends(get_ctx)):
    h = get_owned(Habit, habit_id, ctx, write=True)
    d = day or A.today(ctx)
    log = ctx.db.scalar(select(HabitLog).where(HabitLog.habit_id == h.id, HabitLog.date == d))
    if log:
        ctx.db.delete(log)
        done = False
    else:
        ctx.db.add(HabitLog(owner_id=ctx.user_id, workspace_id=ctx.workspace_id, habit_id=h.id, date=d))
        done = True
    ctx.db.commit()
    return {"habit_id": str(h.id), "date": d.isoformat(), "done": done}


@router.get("/habits/status", summary="Habits with streaks and consistency")
def habits_status(ctx: Ctx = Depends(get_ctx)):
    return A.habit_status(ctx, A.today(ctx))


@router.get("/goals/progress", summary="Active goals with computed progress")
def goals_progress(ctx: Ctx = Depends(get_ctx)):
    return A.goal_progress(ctx)


def _milestone_hook(obj: Milestone, ctx: Ctx, data: dict) -> None:
    if "goal_id" in data:
        assert_ref(Goal, data["goal_id"], ctx)
    if "done" in data:
        obj.completed_at = datetime.now(timezone.utc) if data["done"] else None


def _habitlog_hook(obj, ctx: Ctx, data: dict) -> None:
    assert_ref(Habit, data.get("habit_id"), ctx)


routers = [
    router,
    crud_router(Task, S.TaskIn, S.partial(S.TaskIn, "TaskPatch"), TaskOut, prefix="/tasks", tag="tasks",
                filters=("status", "category", "priority", "goal_id", "parent_id"), date_field="due_date",
                search_fields=("title", "description"), order_by=(Task.due_date.nulls_last(), Task.created_at.desc()),
                before_save=_task_hook, after_save=_task_after),
    crud_router(Goal, S.GoalIn, S.partial(S.GoalIn, "GoalPatch"), GoalOut, prefix="/goals", tag="goals",
                filters=("status", "area"), search_fields=("title",), order_by=(Goal.target_date.nulls_last(),)),
    crud_router(Milestone, S.MilestoneIn, S.partial(S.MilestoneIn, "MilestonePatch"), MilestoneOut, prefix="/milestones",
                tag="goals", filters=("goal_id", "done"), order_by=(Milestone.due_date.nulls_last(),), before_save=_milestone_hook),
    crud_router(Habit, S.HabitIn, S.partial(S.HabitIn, "HabitPatch"), HabitOut, prefix="/habits", tag="habits",
                filters=("active", "area"), order_by=(Habit.created_at,)),
    crud_router(HabitLog, S.HabitLogIn, S.partial(S.HabitLogIn, "HabitLogPatch"), HabitLogOut, prefix="/habit-logs",
                tag="habits", filters=("habit_id",), date_field="date", order_by=(HabitLog.date.desc(),), before_save=_habitlog_hook),
]
