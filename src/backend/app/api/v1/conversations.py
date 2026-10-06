"""Conversation endpoints: CRUD + message stream + deterministic choices."""

import logging
import uuid
from functools import partial

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.dependencies import get_graph
from app.agents.state import PlanItem, SINGLE_CHOICE_CATEGORIES, get_field, _norm_group
from app.api.v1.presenters import (
    conv_to_dict,
    option_to_dict,
    plan_payload,
    requirements_to_items,
    stored_to_chat,
)
from app.api.v1.schemas import (
    CreateConversationRequest,
    RenameConversationRequest,
    SaveChoicesRequest,
    SendMessageRequest,
)
from app.api.v1.streaming import stream_turn, trace_config
from app.api.v1.titles import DEFAULT_CONVERSATION_TITLE
from app.database.database import AsyncSessionLocal
from app.database import repositories as repo

router = APIRouter()

logger = logging.getLogger("uvicorn.error")


@router.post("/conversations/{conversation_id}/choices")
async def save_choices(conversation_id: str, body: SaveChoicesRequest, graph=Depends(get_graph)):
    """Save UI button selections deterministically (no LLM resolution).

    Resolves option_ids against available_options, snapshots label/price
    into the trip plan (replacement per single-choice (category, group)). Returns
    the saved labels; the frontend then sends the user message through
    the normal pipeline (like "Let's go with…"), where extract+router
    short-circuit on SAVED_CHOICES_PREFIX straight to main_llm.

    Args:
        conversation_id: the conversation id (LangGraph thread id).
        body: the selected category/option_id pairs.
        graph: the shared compiled graph (injected).

    Returns:
        Dict with the saved labels plus the refreshed plan payload.

    Raises:
        HTTPException: 503 when the graph is not initialized, 422 for an
            unknown option id.
    """
    if graph is None:
        raise HTTPException(status_code=503, detail="Graph not initialized")
    config = trace_config(conversation_id)
    state = await graph.aget_state(config)
    values = state.values or {}
    avail = values.get("available_options") or {}
    plan = list(values.get("trip_plan") or [])

    def find(category: str, option_id: str):
        for opt in avail.get(category, []) or []:
            get = partial(get_field, opt)
            if str(get("id")) == str(option_id):
                return get
        return None

    saved: list[str] = []
    for ch in body.choices:
        get = find(ch.category, ch.option_id)
        if get is None:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown option '{ch.option_id}' for category '{ch.category}'",
            )
        group = _norm_group(get("group", ""))
        item = PlanItem(
            category=ch.category,
            option_id=str(ch.option_id),
            label=get("label", "") or str(ch.option_id),
            price=get("price"),
            currency=get("currency"),
            per_person=bool(get("per_person", False)),
            details=get("details", "") or "",
            group=group,
        )
        key = lambda it: (
            it["category"] if isinstance(it, dict) else it.category,
            _norm_group(it["group"] if isinstance(it, dict) else it.group),
            str(it["option_id"] if isinstance(it, dict) else it.option_id),
        )
        if ch.category in SINGLE_CHOICE_CATEGORIES:
            plan = [it for it in plan if key(it)[:2] != (ch.category, group)]
            plan.append(item)
        elif not any(key(it) == (ch.category, group, str(ch.option_id)) for it in plan):
            plan.append(item)
        saved.append(item.label)
    await graph.aupdate_state(config, {"trip_plan": plan})
    fresh = await graph.aget_state(config)
    return {"saved": saved, "plan": plan_payload(fresh.values or {})}


@router.post("/conversations/{conversation_id}/messages")
async def send_message(conversation_id: str, body: SendMessageRequest, graph=Depends(get_graph)):
    """Stream one graph turn as SSE (`stream_turn`).

    Args:
        conversation_id: the conversation id (LangGraph thread id).
        body: the user's message text.
        graph: the shared compiled graph (injected).

    Returns:
        A `StreamingResponse` with `text/event-stream` frames.

    Raises:
        HTTPException: 503 when the graph is not initialized.
    """
    if graph is None:
        raise HTTPException(status_code=503, detail="Graph not initialized")
    return StreamingResponse(
        stream_turn(graph, conversation_id, body.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/conversations")
async def list_conversations():
    """List all conversations for the sidebar, newest first.

    Returns:
        Dict with the conversation list payloads.
    """
    async with AsyncSessionLocal() as session:
        convs = await repo.list_conversations(session)
        return {"conversations": [conv_to_dict(c) for c in convs]}


@router.post("/conversations")
async def create_conversation(body: CreateConversationRequest):
    """Create (or ensure) a conversation with an optional client-side id.

    Args:
        body: optional client id plus title (defaults applied).

    Returns:
        The new (or existing) conversation payload.
    """
    conversation_id = body.id.strip() if body.id and body.id.strip() else f"trip-{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as session:
        conv = await repo.ensure_conversation(session, conversation_id, body.title or DEFAULT_CONVERSATION_TITLE)
        await session.commit()
        return conv_to_dict(conv)


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    """Return the persisted message history (for reload rehydrate).

    Args:
        conversation_id: the conversation id.

    Returns:
        Dict with the chat message payloads in order.
    """
    async with AsyncSessionLocal() as session:
        msgs = await repo.get_messages(session, conversation_id)
        return {"messages": [stored_to_chat(m) for m in msgs]}


@router.get("/conversations/{conversation_id}/state")
async def get_conversation_state(conversation_id: str, graph=Depends(get_graph)):
    """Rehydrate side panels (requirements/options/plan) after a reload.

    Args:
        conversation_id: the conversation id (LangGraph thread id).
        graph: the shared compiled graph (injected).

    Returns:
        Dict with requirements, options by category and the plan payload
        (None when the plan is still empty).

    Raises:
        HTTPException: 503 when the graph is not initialized.
    """
    if graph is None:
        raise HTTPException(status_code=503, detail="Graph not initialized")
    state = await graph.aget_state({"configurable": {"thread_id": conversation_id}})
    values = state.values or {}
    options = {}
    for category, opts in (values.get("available_options") or {}).items():
        options[category] = [option_to_dict(o) for o in (opts or [])]
    return {
        "requirements": requirements_to_items(values.get("requirements")),
        "options": options,
        "plan": plan_payload(values) if values.get("trip_plan") else None,
    }


@router.patch("/conversations/{conversation_id}")
async def rename_conversation(conversation_id: str, body: RenameConversationRequest):
    """Rename a conversation (manual renames are never auto-overwritten).

    Args:
        conversation_id: the conversation id.
        body: the new title (blank falls back to the default title).

    Returns:
        The renamed conversation payload.

    Raises:
        HTTPException: 404 when the conversation does not exist.
    """
    async with AsyncSessionLocal() as session:
        conv = await repo.rename_conversation(session, conversation_id, body.title.strip() or DEFAULT_CONVERSATION_TITLE)
        if conv is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        await session.commit()
        return conv_to_dict(conv)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, graph=Depends(get_graph)):
    """Delete a conversation plus its graph checkpoint thread.

    The checkpoint delete is best-effort: a failure only logs, the
    conversation is already gone.

    Args:
        conversation_id: the conversation id.
        graph: the shared compiled graph (injected, optional for this op).

    Returns:
        Dict with the deleted conversation id.

    Raises:
        HTTPException: 404 when the conversation does not exist.
    """
    async with AsyncSessionLocal() as session:
        ok = await repo.delete_conversation(session, conversation_id)
        await session.commit()
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if graph is not None:
        try:
            checkpointer = getattr(graph, "checkpointer", None)
            if checkpointer is not None and hasattr(checkpointer, "adelete_thread"):
                await checkpointer.adelete_thread(conversation_id)
        except Exception:
            logger.warning("Checkpoint delete failed for %s", conversation_id, exc_info=True)
    return {"deleted": conversation_id}
