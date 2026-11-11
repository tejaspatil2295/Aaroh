import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from .. import analytics as A
from .. import schemas as S
from ..access import get_owned, visible
from ..crud import crud_router
from ..deps import Ctx, get_ctx
from ..models import BodyMetric, DailyActivity, FoodLog, Workout, WorkoutSet

BodyMetricOut = S.read(S.BodyMetricIn, "BodyMetricOut")
ActivityOut = S.read(S.DailyActivityIn, "DailyActivityOut", source=(str, "manual"))
FoodOut = S.read(S.FoodLogIn, "FoodLogOut")


class WorkoutOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    date: date
    title: str
    workout_type: str
    duration_minutes: int | None
    attended_gym: bool
    status: str
    notes: str
    source: str
    sets: list[S.WorkoutSetOut]
    created_at: datetime


router = APIRouter(prefix="/fitness", tags=["fitness"])


@router.get("/summary")
def summary(ctx: Ctx = Depends(get_ctx)):
    day = A.today(ctx)
    return {"today": A.fitness_day(ctx, day), "week": A.fitness_week(ctx, day)}


@router.get("/series", summary="Chart series: weight, protein, calories, steps, water")
def series(days: int = Query(default=30, ge=7, le=365), ctx: Ctx = Depends(get_ctx)):
    end = A.today(ctx)
    start = end - timedelta(days=days - 1)
    base = {(start + timedelta(days=i)): {"date": (start + timedelta(days=i)).isoformat(), "protein": 0.0, "calories": 0, "steps": None, "water": None, "weight": None, "workout": 0} for i in range(days)}
    for f in ctx.db.scalars(select(FoodLog).where(visible(FoodLog, ctx), FoodLog.date >= start)).all():
        if f.date in base:
            base[f.date]["protein"] += float(f.protein_g)
            base[f.date]["calories"] += f.calories
    for a in ctx.db.scalars(select(DailyActivity).where(visible(DailyActivity, ctx), DailyActivity.date >= start)).all():
        if a.date in base:
            base[a.date]["steps"], base[a.date]["water"] = a.steps, a.water_ml
    for m in ctx.db.scalars(select(BodyMetric).where(visible(BodyMetric, ctx), BodyMetric.date >= start)).all():
        if m.date in base and m.weight_kg is not None:
            base[m.date]["weight"] = float(m.weight_kg)
    for w in ctx.db.scalars(select(Workout).where(visible(Workout, ctx), Workout.date >= start, Workout.status == "done")).all():
        if w.date in base:
            base[w.date]["workout"] += 1
    return list(base.values())


@router.get("/exercises", summary="Distinct exercises with best set, for progress tracking")
def exercises(ctx: Ctx = Depends(get_ctx)):
    rows = ctx.db.execute(
        select(WorkoutSet, Workout.date).join(Workout).where(visible(Workout, ctx)).order_by(Workout.date)
    ).all()
    out: dict[str, dict] = {}
    for s, d in rows:
        e = out.setdefault(s.exercise, {"exercise": s.exercise, "sets": 0, "best_weight": 0.0, "history": {}})
        e["sets"] += 1
        w = float(s.weight_kg or 0)
        e["best_weight"] = max(e["best_weight"], w)
        e["history"][d.isoformat()] = max(e["history"].get(d.isoformat(), 0), w)
    return [{**v, "history": [{"date": k, "weight": w} for k, w in v["history"].items()]} for v in out.values()]


# ---------------------------------------------------------------- workouts (nested sets)
@router.get("/workouts", response_model=list[WorkoutOut])
def list_workouts(date_from: date | None = Query(default=None, alias="from"), date_to: date | None = Query(default=None, alias="to"),
                  limit: int = Query(default=100, le=500), ctx: Ctx = Depends(get_ctx)):
    stmt = select(Workout).where(visible(Workout, ctx))
    if date_from:
        stmt = stmt.where(Workout.date >= date_from)
    if date_to:
        stmt = stmt.where(Workout.date <= date_to)
    return ctx.db.scalars(stmt.order_by(Workout.date.desc()).limit(limit)).all()


def _apply_workout(w: Workout, payload: S.WorkoutIn) -> None:
    data = payload.model_dump(exclude={"sets"})
    for k, v in data.items():
        setattr(w, k, v)
    w.sets = [WorkoutSet(**s.model_dump()) for s in payload.sets]


@router.post("/workouts", response_model=WorkoutOut, status_code=201)
def create_workout(payload: S.WorkoutIn, ctx: Ctx = Depends(get_ctx)):
    w = Workout(owner_id=ctx.user_id, workspace_id=ctx.workspace_id)
    _apply_workout(w, payload)
    ctx.db.add(w)
    ctx.db.commit()
    return w


@router.get("/workouts/{wid}", response_model=WorkoutOut)
def get_workout(wid: uuid.UUID, ctx: Ctx = Depends(get_ctx)):
    return get_owned(Workout, wid, ctx)


@router.put("/workouts/{wid}", response_model=WorkoutOut)
def replace_workout(wid: uuid.UUID, payload: S.WorkoutIn, ctx: Ctx = Depends(get_ctx)):
    w = get_owned(Workout, wid, ctx, write=True)
    _apply_workout(w, payload)
    ctx.db.commit()
    return w


@router.delete("/workouts/{wid}", status_code=204)
def delete_workout(wid: uuid.UUID, ctx: Ctx = Depends(get_ctx)):
    ctx.db.delete(get_owned(Workout, wid, ctx, write=True))
    ctx.db.commit()


# ---------------------------------------------------------------- daily activity (upsert by date)
class ActivityPatch(BaseModel):
    steps: int | None = Field(default=None, ge=0, le=200000)
    water_ml: int | None = Field(default=None, ge=0, le=20000)
    add_water_ml: int | None = Field(default=None, ge=-5000, le=5000)
    sleep_hours: Decimal | None = Field(default=None, ge=0, le=24)
    active_minutes: int | None = Field(default=None, ge=0, le=1440)


@router.put("/activity/{day}", response_model=ActivityOut, summary="Create or update the activity log for a day")
def upsert_activity(day: date, payload: ActivityPatch, ctx: Ctx = Depends(get_ctx)):
    a = ctx.db.scalar(select(DailyActivity).where(visible(DailyActivity, ctx), DailyActivity.owner_id == ctx.user_id, DailyActivity.date == day))
    if not a:
        a = DailyActivity(owner_id=ctx.user_id, workspace_id=ctx.workspace_id, date=day, steps=0, water_ml=0, active_minutes=0)
        ctx.db.add(a)
    data = payload.model_dump(exclude_unset=True)
    add = data.pop("add_water_ml", None)
    for k, v in data.items():
        if v is not None:
            setattr(a, k, v)
    if add:
        a.water_ml = max(0, (a.water_ml or 0) + add)
    ctx.db.commit()
    return a


@router.get("/activity", response_model=list[ActivityOut])
def list_activity(date_from: date | None = Query(default=None, alias="from"), ctx: Ctx = Depends(get_ctx)):
    stmt = select(DailyActivity).where(visible(DailyActivity, ctx))
    if date_from:
        stmt = stmt.where(DailyActivity.date >= date_from)
    return ctx.db.scalars(stmt.order_by(DailyActivity.date.desc()).limit(366)).all()


# ---------------------------------------------------------------- integration import (Health Connect / Google Fit)
class ImportRecord(BaseModel):
    type: Literal["steps", "workout", "weight"]
    date: date
    value: float | None = None
    title: str | None = None
    duration_minutes: int | None = None
    external_id: str = Field(max_length=120)


class ImportIn(BaseModel):
    source: Literal["health_connect", "google_fit"]
    records: list[ImportRecord] = Field(max_length=2000)


@router.post("/import", summary="Bulk import from a device health platform (idempotent by external_id)")
def import_records(payload: ImportIn, ctx: Ctx = Depends(get_ctx)):
    created = updated = 0
    for r in payload.records:
        if r.type == "steps":
            a = ctx.db.scalar(select(DailyActivity).where(DailyActivity.owner_id == ctx.user_id, DailyActivity.date == r.date))
            if not a:
                a = DailyActivity(owner_id=ctx.user_id, workspace_id=ctx.workspace_id, date=r.date, water_ml=0, active_minutes=0)
                ctx.db.add(a)
                created += 1
            else:
                updated += 1
            a.steps, a.source = int(r.value or 0), payload.source
        elif r.type == "workout":
            w = ctx.db.scalar(select(Workout).where(Workout.owner_id == ctx.user_id, Workout.external_id == r.external_id))
            if not w:
                ctx.db.add(Workout(owner_id=ctx.user_id, workspace_id=ctx.workspace_id, date=r.date, title=r.title or "Workout",
                                   duration_minutes=r.duration_minutes, source=payload.source, external_id=r.external_id, attended_gym=False))
                created += 1
        elif r.type == "weight" and r.value:
            ctx.db.add(BodyMetric(owner_id=ctx.user_id, workspace_id=ctx.workspace_id, date=r.date, weight_kg=r.value, notes=f"Imported from {payload.source}"))
            created += 1
        ctx.db.flush()
    ctx.db.commit()
    return {"created": created, "updated": updated}


routers = [
    router,
    crud_router(BodyMetric, S.BodyMetricIn, S.partial(S.BodyMetricIn, "BodyMetricPatch"), BodyMetricOut, prefix="/fitness/body",
                tag="fitness", date_field="date", order_by=(BodyMetric.date.desc(),)),
    crud_router(FoodLog, S.FoodLogIn, S.partial(S.FoodLogIn, "FoodLogPatch"), FoodOut, prefix="/fitness/food", tag="fitness",
                filters=("meal",), date_field="date", search_fields=("food",), order_by=(FoodLog.date.desc(), FoodLog.created_at)),
]
