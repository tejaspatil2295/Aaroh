import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from ..access import get_owned, visible
from ..ai import offline
from ..ai.context import build_context
from ..ai.prompts import PERSONAS
from ..ai.providers import resolve_config
from ..ai.service import complete, generate_insight
from ..deps import Ctx, get_ctx
from ..models import AIConversation, AIInsight, AIMessage
from ..schemas import AIMessageOut, ChatIn, ConversationOut, InsightOut, InsightRequest

router = APIRouter(prefix="/ai", tags=["ai"])
HISTORY_TURNS = 20


@router.get("/status")
def status(ctx: Ctx = Depends(get_ctx)):
    cfg = resolve_config(ctx.user.settings)
    _, modules = build_context(ctx)
    return {
        "mode": "ai" if cfg else "offline",
        "provider": cfg.provider if cfg else None,
        "model": cfg.model if cfg else None,
        "modules_shared": modules,
        "personas": [{"id": k, "title": v[0], "description": v[1]} for k, v in PERSONAS.items()],
    }


@router.get("/context-preview", summary="Exactly what the AI would see (for transparency)")
def context_preview(ctx: Ctx = Depends(get_ctx)):
    text, modules = build_context(ctx)
    return {"modules": modules, "context": text}


@router.post("/chat")
def chat(payload: ChatIn, ctx: Ctx = Depends(get_ctx)):
    if payload.conversation_id:
        conv = get_owned(AIConversation, payload.conversation_id, ctx, write=True)
        if conv.owner_id != ctx.user_id:
            conv = None
    else:
        conv = None
    if conv is None:
        conv = AIConversation(owner_id=ctx.user_id, workspace_id=ctx.workspace_id, persona=payload.persona, title=payload.message[:80])
        ctx.db.add(conv)
        ctx.db.flush()
    conv.persona = payload.persona
    history = [{"role": m.role, "content": m.content} for m in conv.messages[-HISTORY_TURNS:] if not m.is_fallback]
    user_msg = AIMessage(conversation_id=conv.id, role="user", content=payload.message)
    ctx.db.add(user_msg)
    ctx.db.flush()
    focus = PERSONAS[payload.persona][2]
    result = complete(ctx, payload.persona, history + [{"role": "user", "content": payload.message}], focus=focus)
    if result is None:
        reply = AIMessage(conversation_id=conv.id, role="assistant", content=offline.chat_reply(ctx, payload.persona), provider="offline", model="rules", is_fallback=True)
    else:
        reply = AIMessage(conversation_id=conv.id, role="assistant", content=result.text, provider=result.provider, model=result.model)
    ctx.db.add(reply)
    ctx.db.commit()
    return {"conversation": ConversationOut.model_validate(conv), "message": AIMessageOut.model_validate(reply), "user_message": AIMessageOut.model_validate(user_msg)}


@router.get("/conversations", response_model=list[ConversationOut])
def conversations(ctx: Ctx = Depends(get_ctx)):
    return ctx.db.scalars(
        select(AIConversation).where(visible(AIConversation, ctx), AIConversation.owner_id == ctx.user_id).order_by(AIConversation.updated_at.desc()).limit(100)
    ).all()


@router.get("/conversations/{cid}/messages", response_model=list[AIMessageOut])
def messages(cid: uuid.UUID, ctx: Ctx = Depends(get_ctx)):
    return get_owned(AIConversation, cid, ctx).messages


@router.delete("/conversations/{cid}", status_code=204)
def delete_conversation(cid: uuid.UUID, ctx: Ctx = Depends(get_ctx)):
    ctx.db.delete(get_owned(AIConversation, cid, ctx, write=True))
    ctx.db.commit()


@router.post("/insights", response_model=InsightOut, summary="Generate (or fetch cached) insight/review")
def insights(payload: InsightRequest, ctx: Ctx = Depends(get_ctx)):
    return generate_insight(ctx, payload.kind, payload.force)


@router.get("/insights", response_model=list[InsightOut])
def list_insights(kind: str | None = Query(default=None), limit: int = Query(default=30, le=200), ctx: Ctx = Depends(get_ctx)):
    stmt = select(AIInsight).where(visible(AIInsight, ctx), AIInsight.owner_id == ctx.user_id)
    if kind:
        stmt = stmt.where(AIInsight.kind == kind)
    return ctx.db.scalars(stmt.order_by(AIInsight.created_at.desc()).limit(limit)).all()
