"""Offline mode: used when no AI provider is configured.

These are NOT AI responses. They are clearly labelled summaries computed from the user's
data with simple rules, so the app stays useful without an API key.
"""
from datetime import timedelta

from .. import analytics as A
from ..deps import Ctx
from .context import permissions

LABEL = "**Offline insights** (no AI provider configured, so this is a rule-based summary of your data. Add an API key in Settings > AI for full Aaroh AI.)"


def _pct(x):
    return f"{round(x * 100)}%" if x is not None else "n/a"


def insight(ctx: Ctx, kind: str) -> str:
    day = A.today(ctx)
    perms = permissions(ctx)
    lines: list[str] = [LABEL, ""]
    if kind in ("morning_briefing", "evening_review", "task_suggestions", "weekly_review", "monthly_review", "habit_analysis") and perms.get("tasks", True):
        ts = A.task_stats(ctx, day)
        ranked = sorted(ts["overdue"] + ts["due_today"], key=lambda t: (-A.PRIORITY_WEIGHT[t.priority], t.due_date))
        if kind == "evening_review":
            lines.append(f"- Completed today: {len(ts['done_today'])} task(s). Still open for today: {len(ts['due_today'])}. Overdue: {len(ts['overdue'])}.")
        else:
            lines.append("**Top priorities**")
            lines += [f"- {t.title} ({t.priority}, due {t.due_date})" for t in ranked[:3]] or ["- No tasks due. Pick one goal milestone to move forward."]
        for t in ts["frequently_postponed"][:2]:
            lines.append(f"- You have postponed \"{t.title}\" {t.postponed_count} times. Consider splitting it into a 25-minute first step.")
        pat = A.missed_task_patterns(ctx, day)
        worst = sorted(pat["miss_rate_by_category"].items(), key=lambda kv: -kv[1])[:1]
        if worst and worst[0][1] >= 0.4:
            lines.append(f"- {worst[0][0].title()} tasks slipped {_pct(worst[0][1])} of the time in the last 4 weeks.")
    if perms.get("goals", True) and kind in ("morning_briefing", "evening_review", "weekly_review", "habit_analysis", "monthly_review"):
        habits = A.habit_status(ctx, day)
        pending = [h["name"] for h in habits if not h["done_today"]]
        if pending and kind != "habit_analysis":
            lines.append(f"- Habits not yet done today: {', '.join(pending[:4])}.")
        if kind in ("habit_analysis", "weekly_review", "monthly_review"):
            lines.append("**Habits (30-day consistency)**")
            lines += [f"- {h['name']}: {_pct(h['consistency_30d'])}, streak {h['streak']}" for h in habits]
    if perms.get("fitness", True) and kind in ("morning_briefing", "evening_review", "fitness_insights", "weekly_review", "monthly_review"):
        fd = A.fitness_day(ctx, day)
        fw = A.fitness_week(ctx, day)
        lines.append(f"- Protein today {fd['protein_g']} / {fd['protein_target']} g; water {fd['water_ml']} / {fd['water_target']} ml; steps {fd['steps']} / {fd['steps_target']}.")
        if kind != "morning_briefing":
            lines.append(f"- Last 7 days: {fw['gym_sessions']} gym session(s) of {fw['gym_target']} planned; protein target hit on {fw['protein_target_days_hit']} day(s); avg steps {fw['avg_steps'] or 'n/a'}.")
            if fw["weight_change_30d"] is not None:
                lines.append(f"- Weight change over ~30 days: {fw['weight_change_30d']:+} kg.")
    if perms.get("learning", True) and kind in ("morning_briefing", "evening_review", "learning_recommendation", "weekly_review", "monthly_review"):
        ls = A.learning_summary(ctx, day)
        lines.append(f"- Learning this week: {ls['week_minutes']} of {ls['week_target_minutes']} min target.")
        if kind == "learning_recommendation":
            lines.append("**Largest skill gaps (by your priority and target level)**")
            lines += [f"- {g['skill']}: level {g['current']} → {g['target']} ({g['priority']} priority)" for g in ls["skill_gaps"][:5]]
            if ls["interview"]["weakest"]:
                lines.append(f"- Weakest interview topics: {', '.join(ls['interview']['weakest'])}.")
    if perms.get("finance", True) and kind in ("evening_review", "finance_insights", "weekly_review", "monthly_review"):
        month = day.strftime("%Y-%m")
        fm = A.finance_month(ctx, month)
        today_spend = fm["daily"].get(day.isoformat(), 0)
        if kind == "evening_review":
            lines.append(f"- Spent today: ₹{today_spend:,.0f}. Month to date: ₹{fm['total_expense']:,.0f} ({_pct(fm['budget_used_pct'])} of budget).")
        else:
            lines.append(f"**Money this month**: spent ₹{fm['total_expense']:,.0f}, earned ₹{fm['total_income']:,.0f}, savings rate {_pct(fm['savings_rate'])}.")
            lines += [f"- {k.replace('_', ' ').title()}: ₹{v:,.0f}" for k, v in list(fm["by_category"].items())[:5]]
            lines += [f"- {flag}" for flag in A.spending_flags(ctx, month)]
    if perms.get("work", True) and kind == "work_weekly_report":
        ww = A.work_week(ctx, day)
        lines.append(f"**Work week**: {ww['days_logged']} day(s) logged, {ww['hours']} h. Hours by project: {ww['hours_by_project']}")
        for e in ww["entries"]:
            lines.append(f"- {e['date']} {e['project']}: {e['summary']}" + (f" | Solved: {e['solutions']}" if e["solutions"] else ""))
        pend = [e["pending"] for e in ww["entries"] if e["pending"]]
        if pend:
            lines.append(f"**Pending**: {pend[-1]}")
    if kind == "journal_patterns":
        if not perms.get("journal"):
            lines.append("- Journal access is turned off for AI in Settings > Privacy.")
        else:
            js = A.journal_summary(ctx, day)
            lines.append(f"- {js['entries']} entries in 30 days; average mood {js['avg_mood'] or 'n/a'} / 5.")
            if js["top_tags"]:
                lines.append(f"- Most frequent themes: {', '.join(js['top_tags'])}.")
    if len(lines) == 2:
        lines.append("- Not enough data or module access yet for this summary. Log a few days of activity and try again.")
    return "\n".join(lines)


def chat_reply(ctx: Ctx, persona: str) -> str:
    kind = {
        "finance_coach": "finance_insights",
        "fitness_companion": "fitness_insights",
        "tech_teacher": "learning_recommendation",
        "career_mentor": "learning_recommendation",
        "journal_companion": "journal_patterns",
        "side_hustle_advisor": None,
    }.get(persona, "morning_briefing")
    if kind is None:
        s = A.side_income_summary(ctx)
        body = [LABEL, "", f"- Tracking {len(s['opportunities'])} opportunities; revenue so far ₹{s['total_revenue']:,.0f}, costs ₹{s['total_costs']:,.0f}."]
        body += [f"- {o['title']} ({o['status']}): next action: {o['next_action'] or 'not set'}" for o in s["opportunities"][:6]]
        return "\n".join(body)
    return insight(ctx, kind) + "\n\n_Conversational answers need an AI provider; the summary above is based on your role's data._"


def week_range(day):
    return day - timedelta(days=6), day
