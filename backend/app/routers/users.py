import base64
import os
import shutil
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import delete, select

from .. import models as M
from ..ai.providers import resolve_config
from ..config import get_settings
from ..defaults import DEFAULT_AI_PERMISSIONS, DEFAULT_PREFERENCES
from ..deps import Ctx, get_ctx
from ..schemas import (
    AI_MODULES,
    DeleteAccountIn,
    PasswordChange,
    ProfileUpdate,
    SettingsOut,
    SettingsUpdate,
    UserOut,
)
from ..security import encrypt_secret, hash_password, verify_password

router = APIRouter(prefix="/users/me", tags=["account"])

EXPORT_MODELS = [
    M.Goal, M.Milestone, M.Task, M.Habit, M.HabitLog, M.Transaction, M.Budget, M.Subscription, M.Investment, M.Liability, M.NetWorthSnapshot, M.FinancialGoal,
    M.JournalEntry, M.Attachment, M.Skill, M.RoadmapItem, M.LearningLog, M.KnowledgeNote, M.Resource,
    M.LearningItem, M.InterviewItem, M.BodyMetric, M.Workout, M.DailyActivity, M.FoodLog, M.WorkLog,
    M.Opportunity, M.AIConversation, M.AIInsight,
]


@router.get("", response_model=UserOut)
def get_me(ctx: Ctx = Depends(get_ctx)):
    return ctx.user


@router.patch("", response_model=UserOut)
def update_me(payload: ProfileUpdate, ctx: Ctx = Depends(get_ctx)):
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(ctx.user, k, v)
    ctx.db.commit()
    return ctx.user


@router.post("/password", status_code=204)
def change_password(payload: PasswordChange, ctx: Ctx = Depends(get_ctx)):
    if not verify_password(payload.current_password, ctx.user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    ctx.user.password_hash = hash_password(payload.new_password)
    # Sign out every other session.
    for rt in ctx.db.scalars(select(M.RefreshToken).where(M.RefreshToken.user_id == ctx.user_id, M.RefreshToken.revoked_at.is_(None))):
        rt.revoked_at = datetime.now(timezone.utc)
    ctx.db.commit()


def _settings_out(ctx: Ctx) -> SettingsOut:
    us = ctx.user.settings
    cfg = resolve_config(us)
    return SettingsOut(
        preferences={**DEFAULT_PREFERENCES, **(us.preferences or {})},
        ai_permissions={**DEFAULT_AI_PERMISSIONS, **(us.ai_permissions or {})},
        ai_provider=us.ai_provider or "default",
        ai_model=us.ai_model,
        ai_base_url=us.ai_base_url,
        ai_key_set=bool(us.ai_api_key_encrypted),
        ai_effective={
            "mode": "ai" if cfg else "offline",
            "provider": cfg.provider if cfg else None,
            "model": cfg.model if cfg else None,
            "source": cfg.source if cfg else None,
        },
    )


@router.get("/settings", response_model=SettingsOut)
def get_settings_(ctx: Ctx = Depends(get_ctx)):
    return _settings_out(ctx)


@router.patch("/settings", response_model=SettingsOut)
def update_settings(payload: SettingsUpdate, ctx: Ctx = Depends(get_ctx)):
    us = ctx.user.settings
    data = payload.model_dump(exclude_unset=True)
    if "preferences" in data:
        unknown = set(data["preferences"]) - set(DEFAULT_PREFERENCES)
        if unknown:
            raise HTTPException(422, f"Unknown preferences: {', '.join(sorted(unknown))}")
        us.preferences = {**(us.preferences or {}), **data["preferences"]}
    if "ai_permissions" in data:
        unknown = set(data["ai_permissions"]) - set(AI_MODULES)
        if unknown:
            raise HTTPException(422, f"Unknown modules: {', '.join(sorted(unknown))}")
        us.ai_permissions = {**(us.ai_permissions or {}), **data["ai_permissions"]}
    for k in ("ai_provider", "ai_model", "ai_base_url"):
        if k in data:
            setattr(us, k, data[k] or None)
    if "ai_api_key" in data:
        us.ai_api_key_encrypted = encrypt_secret(data["ai_api_key"]) if data["ai_api_key"] else None
    ctx.db.commit()
    ctx.db.refresh(us)
    return _settings_out(ctx)


def _row(obj) -> dict:
    out = {}
    for col in obj.__table__.columns:
        v = getattr(obj, col.name)
        if isinstance(v, bytes):  # photos stored in the database
            out[col.name] = base64.b64encode(v).decode()
            continue
        out[col.name] = v.isoformat() if hasattr(v, "isoformat") else (str(v) if v is not None and not isinstance(v, (int, float, bool, str, list, dict)) else v)
    return out


@router.get("/export", summary="Download all of your data as JSON")
def export_data(ctx: Ctx = Depends(get_ctx)):
    data: dict = {"exported_at": datetime.now(timezone.utc).isoformat(), "user": _row(ctx.user)}
    data["user"].pop("password_hash", None)
    data["settings"] = {"preferences": ctx.user.settings.preferences, "ai_permissions": ctx.user.settings.ai_permissions}
    for model in EXPORT_MODELS:
        rows = ctx.db.scalars(select(model).where(model.owner_id == ctx.user_id)).all()
        items = []
        for r in rows:
            d = _row(r)
            if isinstance(r, M.Workout):
                d["sets"] = [_row(s) for s in r.sets]
            if isinstance(r, M.AIConversation):
                d["messages"] = [_row(m) for m in r.messages]
            items.append(d)
        data[model.__tablename__] = items
    return JSONResponse(data, headers={"Content-Disposition": 'attachment; filename="aaroh-export.json"'})


@router.delete("", status_code=204, summary="Permanently delete your account and all data")
def delete_account(payload: DeleteAccountIn, ctx: Ctx = Depends(get_ctx)):
    if not verify_password(payload.password, ctx.user.password_hash):
        raise HTTPException(400, "Password is incorrect")
    db, uid = ctx.db, ctx.user_id
    personal = db.scalars(select(M.Workspace).where(M.Workspace.created_by == uid, M.Workspace.kind == "personal")).all()
    # Owned rows cascade from users; personal workspaces are removed explicitly.
    for model in EXPORT_MODELS:
        db.execute(delete(model).where(model.owner_id == uid))
    db.execute(delete(M.WorkspaceMember).where(M.WorkspaceMember.user_id == uid))
    for ws in personal:
        db.delete(ws)
    db.delete(ctx.user)
    db.commit()
    shutil.rmtree(os.path.join(get_settings().upload_dir, str(uid)), ignore_errors=True)
