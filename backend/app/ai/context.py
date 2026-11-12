"""Builds the personal-data context the AI sees, honouring the user's AI privacy toggles."""
import json
from datetime import date, timedelta

from .. import analytics as A
from ..defaults import DEFAULT_AI_PERMISSIONS
from ..deps import Ctx
from ..models import Task


def permissions(ctx: Ctx) -> dict:
    p = dict(DEFAULT_AI_PERMISSIONS)
    if ctx.user.settings and ctx.user.settings.ai_permissions:
        p.update(ctx.user.settings.ai_permissions)
    return p


def _task_line(t: Task) -> str:
    bits = [t.title, f"[{t.category}/{t.priority}]"]
    if t.due_date:
        bits.append(f"due {t.due_date.isoformat()}")
    if t.status == "in_progress":
        bits.append("(in progress)")
    if t.postponed_count:
        bits.append(f"postponed {t.postponed_count}x")
    return " ".join(bits)


def _j(data) -> str:
    return json.dumps(data, default=str, ensure_ascii=False)


def build_context(ctx: Ctx, focus: set[str] | None = None) -> tuple[str, list[str]]:
    """Return (context_text, modules_included). `focus` limits to a subset of modules."""
    perms = permissions(ctx)
    day = A.today(ctx)
    p = A.prefs(ctx)
    allowed = [m for m, ok in perms.items() if ok and (focus is None or m in focus or m == "profile")]
    out: list[str] = [f"Today is {day.strftime('%A %d %B %Y')} (timezone {p['timezone']}). Currency: {p['currency']}."]

    if "profile" in allowed:
        u = ctx.user
        out.append(f"## Profile\nName: {u.full_name or 'not set'}\nAbout: {u.about or 'not provided'}")
        targets = {k: p[k] for k in ("daily_learning_minutes", "weekly_learning_hours", "daily_protein_g", "daily_calories", "daily_water_ml", "daily_steps", "weekly_gym_sessions", "monthly_budget", "day_start", "day_end")}
        out.append(f"User-configured targets: {_j(targets)}")
    if "tasks" in allowed:
        ts = A.task_stats(ctx, day)
        lines = [f"Open tasks: {ts['open']} (in progress {ts['in_progress']}); by category {_j(ts['open_by_category'])}"]
        lines.append("Overdue: " + ("; ".join(_task_line(t) for t in ts["overdue"][:10]) or "none"))
        lines.append("Due today: " + ("; ".join(_task_line(t) for t in ts["due_today"][:10]) or "none"))
        lines.append("Completed today: " + ("; ".join(t.title for t in ts["done_today"][:10]) or "none"))
        if ts["frequently_postponed"]:
            lines.append("Repeatedly postponed: " + "; ".join(_task_line(t) for t in ts["frequently_postponed"]))
        lines.append(f"Missed-task patterns (28d): {_j(A.missed_task_patterns(ctx, day))}")
        out.append("## Tasks\n" + "\n".join(lines))
    if "goals" in allowed:
        out.append(f"## Goals\n{_j(A.goal_progress(ctx))}\n## Habits\n{_j([{k: h[k] for k in ('name', 'streak', 'this_week', 'target_per_week', 'consistency_30d', 'done_today')} for h in A.habit_status(ctx, day)])}")
    if "finance" in allowed:
        month = day.strftime("%Y-%m")
        fm = A.finance_month(ctx, month)
        fm.pop("daily", None)
        out.append(
            f"## Finance (this month)\n{_j(fm)}\nSubscriptions: {_j(A.subscriptions_monthly(ctx))}\nObservations: {_j(A.spending_flags(ctx, month))}"
        )
    if "investments" in allowed:
        inv = A.investments_summary(ctx, day, record_snapshot=False)
        inv["history"] = inv["history"][-6:]
        out.append(f"## Investments & net worth (values entered by the user)\n{_j(inv)}")
    if "fitness" in allowed:
        out.append(f"## Fitness\nToday: {_j(A.fitness_day(ctx, day))}\nLast 7 days: {_j(A.fitness_week(ctx, day))}")
    if "learning" in allowed:
        out.append(f"## Learning\n{_j(A.learning_summary(ctx, day))}")
    if "work" in allowed:
        out.append(f"## Work journal (last 7 days)\n{_j(A.work_week(ctx, day))}")
    if "journal" in allowed:
        js = A.journal_summary(ctx, day)
        out.append(f"## Personal journal (last 30 days, entries marked hidden are excluded)\n{_j(js)}")
    if "side_income" in allowed:
        out.append(f"## Side-income opportunities\n{_j(A.side_income_summary(ctx))}")
    blocked = [m for m, ok in perms.items() if not ok]
    if blocked:
        out.append(f"(The user has not shared these modules with the AI: {', '.join(blocked)}. Do not guess about them.)")
    return "\n\n".join(out), allowed


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())
