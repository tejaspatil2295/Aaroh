"""Professional work journal and the UPSC knowledge / side-income hub."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from .. import analytics as A
from .. import schemas as S
from ..access import get_owned, visible
from ..ai.service import complete
from ..crud import crud_router
from ..deps import Ctx, get_ctx
from ..models import Opportunity, WorkLog

WorkLogOut = S.read(S.WorkLogIn, "WorkLogOut")
OpportunityOut = S.read(S.OpportunityIn, "OpportunityOut", ai_evaluation=(str, ""))

work = APIRouter(prefix="/work", tags=["work"])
side = APIRouter(prefix="/side-income", tags=["side-income"])


@work.get("/weekly", summary="Deterministic weekly work summary (use AI insights for the narrative report)")
def weekly(ctx: Ctx = Depends(get_ctx)):
    return A.work_week(ctx, A.today(ctx))


@work.get("/projects")
def projects(ctx: Ctx = Depends(get_ctx)):
    rows = ctx.db.scalars(select(WorkLog).where(visible(WorkLog, ctx))).all()
    out: dict[str, dict] = {}
    for r in rows:
        p = out.setdefault(r.project or "General", {"project": r.project or "General", "entries": 0, "hours": 0.0, "last": None})
        p["entries"] += 1
        p["hours"] += float(r.hours or 0)
        p["last"] = max(p["last"] or r.date, r.date)
    return sorted(out.values(), key=lambda p: p["last"], reverse=True)


# Curated starting points. These are templates the user can add and then edit; numbers are left blank on purpose.
IDEA_TEMPLATES = [
    {"title": "1:1 UPSC mentorship (answer-writing & strategy)", "category": "upsc_mentorship", "skills_required": ["UPSC GS knowledge", "mentoring", "communication"],
     "description": "Paid 1:1 sessions for aspirants on strategy, answer writing review and interview prep, drawing on 5 years of preparation experience."},
    {"title": "Current affairs explainers (newsletter / YouTube)", "category": "current_affairs", "skills_required": ["current affairs", "writing", "video editing"],
     "description": "Weekly current-affairs analysis for aspirants. Builds an audience that later supports courses or mentorship."},
    {"title": "GS answer-writing evaluation service", "category": "teaching", "skills_required": ["UPSC Mains", "evaluation", "feedback writing"],
     "description": "Evaluate mains answers with structured feedback, sold as packs."},
    {"title": "Freelance full-stack projects", "category": "freelancing", "skills_required": ["React", "Angular", "Node.js", "Django", "Spring Boot", "SQL"],
     "description": "Small fixed-scope web apps or dashboards for clients via referrals, LinkedIn or freelance platforms."},
    {"title": "DevOps / deployment consulting for small teams", "category": "consulting", "skills_required": ["Docker", "CI/CD", "cloud", "Linux"],
     "description": "Help startups set up CI/CD, containerisation and reliable deployments on hourly or fixed packages."},
    {"title": "Technical blog: career switch to software engineering", "category": "blogging", "skills_required": ["writing", "software engineering"],
     "description": "Write about moving from UPSC preparation into IT, plus practical engineering tutorials."},
    {"title": "Digital product: UPSC study planner / notes templates", "category": "digital_product", "skills_required": ["UPSC syllabus", "design", "Notion/Sheets"],
     "description": "Sell structured planners and revision templates. Low cost to create, needs distribution."},
    {"title": "Online course: web development for UPSC-to-IT switchers", "category": "online_course", "skills_required": ["teaching", "full-stack development"],
     "description": "Cohort or recorded course for non-CS career switchers. Longer to build; validate demand first."},
]


@side.get("/templates", summary="Starter opportunity templates based on the user's background")
def templates():
    return IDEA_TEMPLATES


@side.get("/summary")
def side_summary(ctx: Ctx = Depends(get_ctx)):
    return A.side_income_summary(ctx)


@side.post("/opportunities/{opp_id}/evaluate", response_model=OpportunityOut, summary="AI: realistic evaluation of an opportunity")
def evaluate(opp_id: uuid.UUID, ctx: Ctx = Depends(get_ctx)):
    o = get_owned(Opportunity, opp_id, ctx, write=True)
    prompt = (
        f"Evaluate this side-income opportunity realistically for me.\nTitle: {o.title}\nCategory: {o.category}\n"
        f"Description: {o.description}\nHours/week I can give: {o.hours_per_week or 'not set'}\n"
        f"My estimates: investment ₹{o.estimated_investment or '?'}, monthly ₹{o.est_monthly_low or '?'}–₹{o.est_monthly_high or '?'}\n"
        f"Validation notes so far: {o.validation_notes or 'none'}\n\n"
        "Cover: fit with my skills and time, competition, realistic earning range in the first 6 months with stated assumptions "
        "(no promises), upfront investment, time to first revenue, key risks, a cheap 2-week validation experiment, and a "
        "go / test-first / skip recommendation. Use headings and bullets, under 350 words."
    )
    res = complete(ctx, "side_hustle_advisor", [{"role": "user", "content": prompt}], focus={"profile", "side_income", "finance", "learning"})
    if res is None:
        raise HTTPException(503, "Opportunity evaluation needs an AI provider. Add one in Settings > AI.")
    o.ai_evaluation = res.text
    ctx.db.commit()
    return o


routers = [
    work,
    side,
    crud_router(WorkLog, S.WorkLogIn, S.partial(S.WorkLogIn, "WorkLogPatch"), WorkLogOut, prefix="/work/logs", tag="work",
                filters=("project",), date_field="date",
                search_fields=("summary", "tasks_completed", "problems", "solutions", "learnings", "pending", "project"),
                order_by=(WorkLog.date.desc(), WorkLog.created_at.desc())),
    crud_router(Opportunity, S.OpportunityIn, S.partial(S.OpportunityIn, "OpportunityPatch"), OpportunityOut,
                prefix="/side-income/opportunities", tag="side-income", filters=("status", "category"),
                search_fields=("title", "description"), order_by=(Opportunity.created_at.desc(),)),
]
