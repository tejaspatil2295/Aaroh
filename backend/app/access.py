"""Row-level access rules. Every query for user data must go through `visible()`."""
from sqlalchemy import and_, or_

from .deps import Ctx


def visible(model, ctx: Ctx):
    """Owner sees all their rows in the workspace; others see only rows marked shared."""
    return and_(
        model.workspace_id == ctx.workspace_id,
        or_(model.owner_id == ctx.user_id, model.visibility == "shared"),
    )


def can_write(obj, ctx: Ctx) -> bool:
    if obj.owner_id == ctx.user_id:
        return True
    return obj.visibility == "shared" and ctx.role in ("owner", "admin", "member")


def get_owned(model, obj_id, ctx: Ctx, write: bool = False):
    from fastapi import HTTPException

    obj = ctx.db.get(model, obj_id)
    if obj is None or obj.workspace_id != ctx.workspace_id or (obj.owner_id != ctx.user_id and obj.visibility != "shared"):
        raise HTTPException(404, "Not found")
    if write and not can_write(obj, ctx):
        raise HTTPException(403, "Read-only access")
    return obj
