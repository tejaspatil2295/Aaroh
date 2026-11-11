from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from .. import analytics as A
from .. import schemas as S
from ..access import visible
from ..crud import assert_ref, crud_router
from ..deps import Ctx, get_ctx
from ..models import InterviewItem, KnowledgeNote, LearningItem, LearningLog, Resource, RoadmapItem, Skill

SkillOut = S.read(S.SkillIn, "SkillOut")
RoadmapOut = S.read(S.RoadmapItemIn, "RoadmapItemOut", completed_at=(datetime | None, None))
LogOut = S.read(S.LearningLogIn, "LearningLogOut")
NoteOut = S.read(S.NoteIn, "NoteOut")
ResourceOut = S.read(S.ResourceIn, "ResourceOut")
ItemOut = S.read(S.LearningItemIn, "LearningItemOut")
InterviewOut = S.read(S.InterviewItemIn, "InterviewItemOut")

router = APIRouter(prefix="/learning", tags=["learning"])


@router.get("/summary")
def summary(ctx: Ctx = Depends(get_ctx)):
    data = A.learning_summary(ctx, A.today(ctx))
    skills = ctx.db.scalars(select(Skill).where(visible(Skill, ctx))).all()
    road = ctx.db.scalars(select(RoadmapItem).where(visible(RoadmapItem, ctx))).all()
    data["roadmap_progress"] = {
        str(s.id): {"done": sum(1 for r in road if r.skill_id == s.id and r.done), "total": sum(1 for r in road if r.skill_id == s.id)}
        for s in skills
    }
    return data


@router.get("/daily", summary="Learning minutes per day")
def daily(days: int = Query(default=28, ge=7, le=180), ctx: Ctx = Depends(get_ctx)):
    end = A.today(ctx)
    start = end - timedelta(days=days - 1)
    logs = ctx.db.scalars(select(LearningLog).where(visible(LearningLog, ctx), LearningLog.date >= start)).all()
    series = {(start + timedelta(days=i)).isoformat(): 0 for i in range(days)}
    for log in logs:
        series[log.date.isoformat()] = series.get(log.date.isoformat(), 0) + log.minutes
    return [{"date": d, "minutes": m} for d, m in series.items()]


def _skill_ref(obj, ctx: Ctx, data: dict) -> None:
    assert_ref(Skill, data.get("skill_id"), ctx)


def _roadmap_hook(obj, ctx: Ctx, data: dict) -> None:
    _skill_ref(obj, ctx, data)
    if "done" in data:
        obj.completed_at = datetime.now(timezone.utc) if data["done"] else None


routers = [
    router,
    crud_router(Skill, S.SkillIn, S.partial(S.SkillIn, "SkillPatch"), SkillOut, prefix="/learning/skills", tag="learning",
                filters=("status", "category", "priority"), search_fields=("name", "notes"), order_by=(Skill.created_at,)),
    crud_router(RoadmapItem, S.RoadmapItemIn, S.partial(S.RoadmapItemIn, "RoadmapItemPatch"), RoadmapOut, prefix="/learning/roadmap",
                tag="learning", filters=("skill_id", "done"), order_by=(RoadmapItem.order_index, RoadmapItem.created_at), before_save=_roadmap_hook),
    crud_router(LearningLog, S.LearningLogIn, S.partial(S.LearningLogIn, "LearningLogPatch"), LogOut, prefix="/learning/logs",
                tag="learning", filters=("skill_id",), date_field="date", search_fields=("topic", "notes"),
                order_by=(LearningLog.date.desc(), LearningLog.created_at.desc()), before_save=_skill_ref),
    crud_router(KnowledgeNote, S.NoteIn, S.partial(S.NoteIn, "NotePatch"), NoteOut, prefix="/learning/notes", tag="learning",
                filters=("kind", "skill_id", "language"), search_fields=("title", "content"), order_by=(KnowledgeNote.updated_at.desc(),),
                before_save=_skill_ref),
    crud_router(Resource, S.ResourceIn, S.partial(S.ResourceIn, "ResourcePatch"), ResourceOut, prefix="/learning/resources",
                tag="learning", filters=("status", "kind", "skill_id"), search_fields=("title", "url", "notes"), before_save=_skill_ref),
    crud_router(LearningItem, S.LearningItemIn, S.partial(S.LearningItemIn, "LearningItemPatch"), ItemOut, prefix="/learning/items",
                tag="learning", filters=("kind", "status"), search_fields=("title", "provider")),
    crud_router(InterviewItem, S.InterviewItemIn, S.partial(S.InterviewItemIn, "InterviewItemPatch"), InterviewOut,
                prefix="/learning/interview", tag="learning", filters=("category", "status"), search_fields=("topic", "question"),
                order_by=(InterviewItem.confidence, InterviewItem.created_at)),
]
