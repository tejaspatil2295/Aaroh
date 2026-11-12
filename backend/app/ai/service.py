from dataclasses import dataclass
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select

from .. import analytics as A
from ..access import visible
from ..deps import Ctx
from ..models import AIInsight
from . import offline
from .context import build_context
from .prompts import INSIGHT_FOCUS, INSIGHT_PROMPTS, system_for
from .providers import AIError, get_provider


@dataclass
class AIResult:
    text: str
    provider: str
    model: str
    is_fallback: bool


def complete(ctx: Ctx, persona: str, messages: list[dict], focus: set[str] | None = None, max_tokens: int = 2000) -> AIResult | None:
    """Run the configured LLM with the user's permitted context. Returns None in offline mode."""
    provider = get_provider(ctx.user.settings)
    if provider is None:
        return None
    context, _ = build_context(ctx, focus)
    try:
        text = provider.complete(system_for(persona, context), messages, max_tokens=max_tokens)
    except AIError as e:
        raise HTTPException(502, str(e)) from e
    return AIResult(text=text, provider=provider.name, model=provider.model, is_fallback=False)


def insight_period(ctx: Ctx, kind: str):
    day = A.today(ctx)
    if kind in ("weekly_review", "fitness_insights", "work_weekly_report", "habit_analysis"):
        return day - timedelta(days=day.weekday())
    if kind in ("monthly_review", "finance_insights", "investment_review"):
        return day.replace(day=1)
    return day


def generate_insight(ctx: Ctx, kind: str, force: bool = False) -> AIInsight:
    period = insight_period(ctx, kind)
    existing = ctx.db.scalars(
        select(AIInsight)
        .where(visible(AIInsight, ctx), AIInsight.kind == kind, AIInsight.period_start == period, AIInsight.owner_id == ctx.user_id)
        .order_by(AIInsight.created_at.desc())
    ).first()
    if existing and not force:
        return existing
    result = complete(
        ctx,
        persona={
            "finance_insights": "finance_coach", "fitness_insights": "fitness_companion",
            "learning_recommendation": "tech_teacher", "journal_patterns": "journal_companion",
            "work_weekly_report": "career_mentor", "investment_review": "finance_coach",
        }.get(kind, "life_coach"),
        messages=[{"role": "user", "content": INSIGHT_PROMPTS[kind]}],
        focus=INSIGHT_FOCUS.get(kind),
    )
    if result is None:
        result = AIResult(offline.insight(ctx, kind), "offline", "rules", True)
    ins = AIInsight(
        owner_id=ctx.user_id, workspace_id=ctx.workspace_id, kind=kind, period_start=period,
        content=result.text, provider=result.provider, model=result.model, is_fallback=result.is_fallback,
    )
    ctx.db.add(ins)
    ctx.db.commit()
    return ins
