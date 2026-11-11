import os
import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, select

from .. import analytics as A
from .. import schemas as S
from ..access import get_owned, visible
from ..config import get_settings
from ..crud import crud_router
from ..deps import Ctx, get_ctx
from ..models import Attachment, JournalEntry

JournalOut = S.read(S.JournalIn, "JournalOut")
router = APIRouter(tags=["journal"])
ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/heic": ".heic"}


@router.get("/journal/tags", summary="All tags used in journal entries with counts")
def tags(ctx: Ctx = Depends(get_ctx)):
    rows = ctx.db.scalars(select(JournalEntry.tags).where(visible(JournalEntry, ctx))).all()
    counts: dict[str, int] = {}
    for tl in rows:
        for t in tl or []:
            counts[t] = counts.get(t, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


@router.get("/journal/mood", summary="Mood series and summary")
def mood(days: int = Query(default=90, ge=7, le=366), ctx: Ctx = Depends(get_ctx)):
    return A.journal_summary(ctx, A.today(ctx), days=days, include_hidden=True)


@router.get("/journal/by-tag/{tag}", response_model=list[JournalOut])
def by_tag(tag: str, ctx: Ctx = Depends(get_ctx)):
    entries = ctx.db.scalars(select(JournalEntry).where(visible(JournalEntry, ctx)).order_by(JournalEntry.entry_date.desc())).all()
    return [e for e in entries if tag in (e.tags or [])]


# ---------------------------------------------------------------- attachments (photos)
@router.post("/attachments", response_model=S.AttachmentOut, status_code=201)
async def upload(entity_type: str = Query(pattern="^(journal)$"), entity_id: uuid.UUID = Query(), file: UploadFile = File(...), ctx: Ctx = Depends(get_ctx)):
    get_owned(JournalEntry, entity_id, ctx, write=True)
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, "Only JPEG, PNG, WEBP or HEIC images are allowed")
    data = await file.read(get_settings().max_upload_mb * 1024 * 1024 + 1)
    if len(data) > get_settings().max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File larger than {get_settings().max_upload_mb} MB")
    att_id = uuid.uuid4()
    in_db = get_settings().upload_storage == "database"
    if in_db:
        path = f"db:{att_id}"
    else:
        folder = os.path.join(get_settings().upload_dir, str(ctx.user_id))
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"{att_id}{ALLOWED_TYPES[file.content_type]}")
        with open(path, "wb") as fh:
            fh.write(data)
    att = Attachment(data=data if in_db else None, 
        id=att_id, owner_id=ctx.user_id, workspace_id=ctx.workspace_id, entity_type=entity_type, entity_id=entity_id,
        filename=os.path.basename(file.filename or "photo")[:255], content_type=file.content_type, size_bytes=len(data), storage_path=path,
    )
    ctx.db.add(att)
    ctx.db.commit()
    return att


@router.get("/attachments", response_model=list[S.AttachmentOut])
def list_attachments(entity_id: uuid.UUID, ctx: Ctx = Depends(get_ctx)):
    return ctx.db.scalars(select(Attachment).where(visible(Attachment, ctx), Attachment.entity_id == entity_id)).all()


@router.get("/attachments/{att_id}/file")
def download(att_id: uuid.UUID, ctx: Ctx = Depends(get_ctx)):
    att = get_owned(Attachment, att_id, ctx)
    if att.storage_path.startswith("db:"):
        if att.data is None:
            raise HTTPException(404, "File missing")
        headers = {"Content-Disposition": f'inline; filename="{att.filename.replace(chr(34), "")}"'}
        return Response(att.data, media_type=att.content_type, headers=headers)
    if not os.path.exists(att.storage_path):
        raise HTTPException(404, "File missing")
    return FileResponse(att.storage_path, media_type=att.content_type, filename=att.filename)


@router.delete("/attachments/{att_id}", status_code=204)
def delete_attachment(att_id: uuid.UUID, ctx: Ctx = Depends(get_ctx)):
    att = get_owned(Attachment, att_id, ctx, write=True)
    try:
        if not att.storage_path.startswith("db:"):
            os.remove(att.storage_path)
    except FileNotFoundError:
        pass
    ctx.db.delete(att)
    ctx.db.commit()


routers = [
    router,
    crud_router(JournalEntry, S.JournalIn, S.partial(S.JournalIn, "JournalPatch"), JournalOut, prefix="/journal", tag="journal",
                filters=("kind", "mood"), date_field="entry_date", search_fields=("title", "body", "location", "decision_outcome"),
                order_by=(JournalEntry.entry_date.desc(), JournalEntry.created_at.desc())),
]

_ = (date, func)
