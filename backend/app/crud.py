"""Generic, workspace-scoped CRUD router factory used by most modules."""
import uuid
from datetime import date
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from .access import get_owned, visible
from .deps import Ctx, get_ctx


def _coerce(value: str, column) -> Any:
    py = column.type.python_type
    if py is bool:
        return value.lower() in ("1", "true", "yes")
    if py is date:
        return date.fromisoformat(value)
    if py is uuid.UUID:
        return uuid.UUID(value)
    return py(value)


def crud_router(
    model,
    create_schema,
    update_schema,
    read_schema,
    *,
    prefix: str,
    tag: str,
    filters: tuple[str, ...] = (),
    date_field: str | None = None,
    search_fields: tuple[str, ...] = (),
    order_by: tuple = (),
    before_save: Callable[[Any, Ctx, dict], None] | None = None,
    after_save: Callable[[Any, Ctx, dict], None] | None = None,
    max_limit: int = 1000,
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    @router.get("", response_model=list[read_schema], summary=f"List {tag}")
    def list_items(
        request: Request,
        ctx: Ctx = Depends(get_ctx),
        q: str | None = Query(default=None, max_length=200, description="Full-text search"),
        date_from: date | None = Query(default=None, alias="from"),
        date_to: date | None = Query(default=None, alias="to"),
        limit: int = Query(default=200, ge=1, le=max_limit),
        offset: int = Query(default=0, ge=0),
    ):
        stmt = select(model).where(visible(model, ctx))
        for name in filters:
            if (raw := request.query_params.get(name)) is not None:
                col = getattr(model, name)
                try:
                    stmt = stmt.where(col == _coerce(raw, col.property.columns[0]))
                except ValueError:
                    raise HTTPException(422, f"Invalid value for {name}")
        if date_field:
            col = getattr(model, date_field)
            if date_from:
                stmt = stmt.where(col >= date_from)
            if date_to:
                stmt = stmt.where(col <= date_to)
        if q and search_fields:
            like = f"%{q}%"
            stmt = stmt.where(or_(*[getattr(model, f).ilike(like) for f in search_fields]))
        stmt = stmt.order_by(*(order_by or (model.created_at.desc(),))).limit(limit).offset(offset)
        return ctx.db.scalars(stmt).all()

    @router.post("", response_model=read_schema, status_code=201, summary=f"Create {tag}")
    def create_item(payload: create_schema, ctx: Ctx = Depends(get_ctx)):  # type: ignore[valid-type]
        data = payload.model_dump()
        obj = model(owner_id=ctx.user_id, workspace_id=ctx.workspace_id)
        if before_save:
            before_save(obj, ctx, data)
        for k, v in data.items():
            setattr(obj, k, v)
        ctx.db.add(obj)
        _commit(ctx)
        if after_save:
            after_save(obj, ctx, data)
        return obj

    @router.get("/{item_id}", response_model=read_schema)
    def get_item(item_id: uuid.UUID, ctx: Ctx = Depends(get_ctx)):
        return get_owned(model, item_id, ctx)

    @router.patch("/{item_id}", response_model=read_schema)
    def update_item(item_id: uuid.UUID, payload: update_schema, ctx: Ctx = Depends(get_ctx)):  # type: ignore[valid-type]
        obj = get_owned(model, item_id, ctx, write=True)
        data = payload.model_dump(exclude_unset=True)
        cols = model.__table__.columns
        # A null for a NOT NULL column means "leave unchanged" (forms send empty selects as null).
        data = {k: v for k, v in data.items() if v is not None or k not in cols or cols[k].nullable}
        if before_save:
            before_save(obj, ctx, data)
        for k, v in data.items():
            setattr(obj, k, v)
        _commit(ctx)
        if after_save:
            after_save(obj, ctx, data)
        return obj

    @router.delete("/{item_id}", status_code=204)
    def delete_item(item_id: uuid.UUID, ctx: Ctx = Depends(get_ctx)):
        obj = get_owned(model, item_id, ctx, write=True)
        ctx.db.delete(obj)
        ctx.db.commit()

    return router


def _commit(ctx: Ctx) -> None:
    try:
        ctx.db.commit()
    except IntegrityError as e:
        ctx.db.rollback()
        raise HTTPException(409, "Conflicts with an existing record") from e


def assert_ref(model, ref_id, ctx: Ctx) -> None:
    """Validate that a referenced id (e.g. goal_id) belongs to the caller's workspace."""
    if ref_id is not None:
        get_owned(model, ref_id, ctx)
