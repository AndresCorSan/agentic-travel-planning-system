import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Command
from pydantic import BaseModel

from app.core.dependencies import get_graph
from app.agents.llm import light_llm
from app.agents.state import PlanItem, SINGLE_CHOICE_CATEGORIES
from app.agents.tools.plan import plan_total
from app.database.database import AsyncSessionLocal
from app.database import repositories as repo

router = APIRouter()


class CreateConversationRequest(BaseModel):
    title: str = "New trip"
    id: str | None = None


class RenameConversationRequest(BaseModel):
    title: str


class SendMessageRequest(BaseModel):
    message: str


class ChoiceItem(BaseModel):
    category: str
    option_id: str


class SaveChoicesRequest(BaseModel):
    choices: list[ChoiceItem]


class SavePlanRequest(BaseModel):
    title: str | None = None


STATUS_BY_ROUTE = {
    "destination_research": "Researching destinations…",
    "orchestrator": "Planning research…",
    "main_llm": "Writing answer…",
}

RESEARCH_KEY_BY_AGENT = {
    "weather_agent": "weather",
    "accommodation_agent": "accommodation",
    "transportation_agent": "transportation",
    "activities_agent": "activities",
    "rental_cars_agent": "rentalCar",
}


def _frame(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _task_agent(task) -> str | None:
    if hasattr(task, "agent"):
        return task.agent
    if isinstance(task, dict):
        return task.get("agent")
    return None


AGENT_RESULT_MAX_CHARS = 8000

def _subagent_result_text(output: dict) -> str | None:
    """Latest text from a subagent node update.

    Result keys are irregular (weather_results, activity_results,
    rental_car_results, ...), so scan for the `*_results` suffix instead
    of hardcoding them. Also tolerates Anthropic-style content blocks.
    """
    for key, value in output.items():
        if key.endswith("_results") and isinstance(value, list) and value:
            last = value[-1]
            if isinstance(last, list):
                last = "\n".join(
                    b.get("text", "") for b in last
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            if isinstance(last, str) and last.strip():
                text = last.strip()
                if len(text) > AGENT_RESULT_MAX_CHARS:
                    return text[:AGENT_RESULT_MAX_CHARS] + "\n\n…(truncated)"
                return text
    return None


CURRENCY_SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥"}


def _format_budget(budget, currency) -> str | None:
    """User-friendly budget label: symbol + thousands separator (€1,000).

    Unknown currency codes fall back to "CODE 1,000" (never glued).
    Returns None when there is no budget so the panel shows Not specified.
    """
    if not budget:
        return None
    code = (currency or "").strip().upper()
    symbol = CURRENCY_SYMBOLS.get(code)
    prefix = symbol if symbol is not None else (f"{code} " if code else "")
    amount = f"{budget:,.0f}" if float(budget).is_integer() else f"{budget:,.2f}"
    return f"{prefix}{amount}"


def _option_to_dict(opt) -> dict:
    """PlanOption (pydantic or dict) -> frontend payload."""
    get = lambda name, default=None: (
        getattr(opt, name, default)
        if not isinstance(opt, dict) else opt.get(name, default)
    )
    return {
        "id": str(get("id", "")),
        "label": get("label", "") or "",
        "price": get("price"),
        "currency": get("currency"),
        "per_person": bool(get("per_person", False)),
        "details": get("details", "") or "",
    }


def _plan_payload(values: dict) -> dict:
    """Trip plan + deterministic total for the Plan panel / Budget."""
    raw_plan = (values or {}).get("trip_plan") or []
    req = (values or {}).get("requirements")
    get = lambda name: getattr(req, name, None) if not isinstance(req, dict) else (req or {}).get(name)
    travelers = get("travelers")
    budget = get("budget")
    items = []
    for it in raw_plan:
        get_it = lambda name, default=None: (
            getattr(it, name, default)
            if not isinstance(it, dict) else it.get(name, default)
        )
        items.append({
            "category": get_it("category"),
            "option_id": str(get_it("option_id", "")),
            "label": get_it("label", "") or "",
            "price": get_it("price"),
            "currency": get_it("currency"),
            "per_person": bool(get_it("per_person", False)),
            "details": get_it("details", "") or "",
        })
    total, currency = plan_total(raw_plan, travelers)
    return {
        "plan": items,
        "total": total,
        "currency": currency,
        "budget": budget,
        "overBudget": bool(budget and total > float(budget)),
    }


def _candidate_to_card(candidate, index: int) -> dict:
    """DestinationCandidate (pydantic or dict) -> frontend Destination card."""
    get = lambda name, default=None: (
        getattr(candidate, name, default)
        if not isinstance(candidate, dict) else candidate.get(name, default)
    )
    score = get("score", 0) or 0
    code = (get("country_code", "") or "").strip().lower()
    if len(code) != 2 or not code.isalpha():
        code = ""
    return {
        "id": f"dest-{index}",
        "name": get("destination", "Unknown"),
        "country": get("country", "") or "",
        "country_code": code,
        "tagline": get("reason", "") or "",
        "highlights": get("highlights", []) or [],
        "suitability": int(round(float(score) * 10)),
        "drawback": get("drawback", "") or "",
    }


def _requirements_to_items(req) -> list[dict]:
    """TravelRequirements -> RequirementItem[] for the Travel State panel."""
    if req is None:
        return []
    get = lambda name: getattr(req, name, None) if not isinstance(req, dict) else req.get(name)
    destination = get("destination")
    origin = get("origin")
    travel_dates = get("travel_dates")
    duration_days = get("duration_days")
    travelers = get("travelers")
    budget = get("budget")
    currency = get("currency")
    transport_mode = get("transport_mode")
    accommodation_type = get("accommodation_type")
    interests = get("interests") or []
    constraints = get("constraints") or []
    return [
        {"key": "destination", "label": "Destination", "value": destination, "confirmed": bool(destination)},
        {"key": "origin", "label": "Origin", "value": origin, "confirmed": bool(origin)},
        {"key": "dates", "label": "Dates", "value": travel_dates, "confirmed": bool(travel_dates)},
        {
            "key": "duration",
            "label": "Duration",
            "value": f"{duration_days} days" if duration_days else None,
            "confirmed": bool(duration_days),
        },
        {
            "key": "travelers",
            "label": "Travelers",
            "value": str(travelers) if travelers else None,
            "confirmed": bool(travelers),
        },
        {
            "key": "budget",
            "label": "Budget",
            "value": _format_budget(budget, currency),
            "confirmed": bool(budget),
        },
        {
            "key": "interests",
            "label": "Interests",
            "value": ", ".join(interests) if interests else None,
            "confirmed": bool(interests),
        },
        {
            "key": "transport",
            "label": "Transport",
            "value": transport_mode,
            "confirmed": bool(transport_mode),
        },
        {
            "key": "accommodation",
            "label": "Accommodation",
            "value": accommodation_type,
            "confirmed": bool(accommodation_type),
        },
        {
            "key": "constraints",
            "label": "Constraints",
            "value": ", ".join(constraints) if constraints else None,
            "confirmed": bool(constraints),
        },
    ]


async def _stream(graph, conversation_id: str, message: str):
    config = {"configurable": {"thread_id": conversation_id}}
    # Persist the user turn up-front so history survives mid-stream crashes.
    try:
        async with AsyncSessionLocal() as session:
            conv = await repo.ensure_conversation(session, conversation_id)
            if conv.title in ("New trip", "Untitled trip") and message.strip():
                conv.title = message.strip()[:60]
            await repo.add_message(session, conversation_id, "user", "text", message)
            await session.commit()
    except Exception:
        pass
    assistant_texts: list[str] = []
    assistant_cards: list[dict] = []
    agent_results: dict[str, str] = {}
    try:
        state = await graph.aget_state(config)
        if state.interrupts:
            stream_input = Command(resume=message)
        else:
            yield _frame("status", {"text": "Understanding your request…"})
            stream_input = {"messages": [HumanMessage(content=message)]}
        # Set after a main_tools update: the next main_llm tokens start a
        # new reply but stream into the same bubble, so separate them
        # with a blank line (markdown collapses extras, harmless).
        tools_ran = False
        async for mode, payload in graph.astream(
            stream_input, config=config, stream_mode=["updates", "messages"]
        ):
            if mode == "messages":
                chunk, metadata = payload
                if metadata.get("langgraph_node") != "main_llm":
                    continue
                content = getattr(chunk, "content", "")
                if isinstance(content, str) and content:
                    if tools_ran:
                        content = "\n\n" + content.lstrip("\n")
                        tools_ran = False
                    assistant_texts.append(content)
                    yield _frame("token", {"text": content})
            elif mode == "updates":
                if not isinstance(payload, dict):
                    continue
                for node, output in payload.items():
                    if isinstance(output, list):
                        # Parallel tool calls (e.g. one present_options per
                        # category) stream as one update dict per call, not
                        # a single dict: merge them so every category still
                        # emits its event below.
                        merged: dict = {}
                        for item in output:
                            if not isinstance(item, dict):
                                continue
                            for k, v in item.items():
                                if (
                                    k == "available_options"
                                    and isinstance(v, dict)
                                    and isinstance(merged.get(k), dict)
                                ):
                                    merged[k] = {**merged[k], **v}
                                elif k not in merged:
                                    merged[k] = v
                        output = merged
                    if not isinstance(output, dict):
                        continue
                    if node == "extract_requirements" and output.get("requirements") is not None:
                        yield _frame(
                            "requirements.updated",
                            {"requirements": _requirements_to_items(output["requirements"])},
                        )
                    elif node == "router" and output.get("next_step"):
                        status = STATUS_BY_ROUTE.get(output["next_step"])
                        if status:
                            yield _frame("status", {"text": status})
                    elif node == "destination_research" and output.get("destination_candidates"):
                        candidates = output["destination_candidates"]
                        cards = [_candidate_to_card(c, i) for i, c in enumerate(candidates)]
                        assistant_cards.append({"destinations": cards})
                        yield _frame(
                            "message",
                            {
                                "message": {
                                    "id": f"m{uuid.uuid4().hex[:8]}",
                                    "role": "assistant",
                                    "kind": "destinations",
                                    "text": "Here are my top picks — choose one or tell me what to adjust.",
                                    "destinations": cards,
                                    "createdAt": datetime.now(timezone.utc).isoformat(),
                                }
                            },
                        )
                    elif node == "orchestrator":
                        agents = [a for a in (_task_agent(t) for t in output.get("orchestration_plan", [])) if a]
                        if agents:
                            yield _frame("status", {"text": "Executing specialized subagents…"})
                            yield _frame("agents.start", {"agents": agents})
                    elif node == "main_tools" and output.get("requirements") is not None:
                        # update_requirements returns a Command carrying the new
                        # requirements: push them live instead of waiting for
                        # the turn to finish.
                        tools_ran = True
                        yield _frame(
                            "requirements.updated",
                            {"requirements": _requirements_to_items(output["requirements"])},
                        )
                    if node == "main_tools" and output.get("available_options") is not None:
                        # present_options published selectable options: push
                        # each category so the UI can render choice controls.
                        tools_ran = True
                        for category, opts in (output["available_options"] or {}).items():
                            yield _frame(
                                "options",
                                {
                                    "category": category,
                                    "options": [_option_to_dict(o) for o in (opts or [])],
                                },
                            )
                    if node == "main_tools" and output.get("trip_plan") is not None:
                        # add/remove_plan_item changed the plan: push items +
                        # deterministic total live.
                        tools_ran = True
                        state_now = await graph.aget_state(config)
                        yield _frame("plan.updated", _plan_payload(state_now.values or {}))
                    elif node in RESEARCH_KEY_BY_AGENT:
                        yield _frame("agent.done", {"id": node})
                        yield _frame(
                            "research.update",
                            {"key": RESEARCH_KEY_BY_AGENT[node], "state": "done"},
                        )
                        result_text = _subagent_result_text(output)
                        if result_text:
                            agent_results[node] = result_text
                            yield _frame("agent.result", {"id": node, "text": result_text})
        final = await graph.aget_state(config)
        req = (final.values or {}).get("requirements")
        if req is not None:
            yield _frame("requirements.updated", {"requirements": _requirements_to_items(req)})
        if (final.values or {}).get("trip_plan"):
            yield _frame("plan.updated", _plan_payload(final.values or {}))
        interrupt_texts: list[str] = []
        for interrupt in final.interrupts or []:
            if isinstance(interrupt.value, str) and interrupt.value:
                interrupt_texts.append(interrupt.value)
                yield _frame(
                    "message",
                    {
                        "message": {
                            "id": f"m{uuid.uuid4().hex[:8]}",
                            "role": "assistant",
                            "kind": "text",
                            "text": interrupt.value,
                            "createdAt": datetime.now(timezone.utc).isoformat(),
                        }
                    },
                )
        # Persist the assistant turn (text + destination cards + interrupts).
        # Subagent outputs ride along as the message payload so the
        # accordions rehydrate exactly as they streamed.
        try:
            async with AsyncSessionLocal() as session:
                await repo.ensure_conversation(session, conversation_id)
                results = [{"id": nid, "text": text} for nid, text in agent_results.items()]
                full_text = "".join(assistant_texts).strip()
                if full_text:
                    await repo.add_message(
                        session, conversation_id, "assistant", "text", full_text,
                        {"subagentResults": results} if results else None,
                    )
                elif results:
                    await repo.add_message(
                        session, conversation_id, "assistant", "text", "",
                        {"subagentResults": results},
                    )
                for card in assistant_cards:
                    await repo.add_message(
                        session, conversation_id, "assistant", "destinations",
                        "Here are my top picks — choose one or tell me what to adjust.",
                        card,
                    )
                for text in interrupt_texts:
                    await repo.add_message(session, conversation_id, "assistant", "text", text)
                await session.commit()
        except Exception:
            pass
        yield "event: done\ndata: {}\n\n"
    except Exception as exc:
        if getattr(exc, "status_code", None) == 429 or "429" in str(exc):
            yield _frame(
                "error",
                {"message": "All models are busy right now, please retry in a minute."},
            )
        else:
            yield _frame("error", {"message": str(exc)})


@router.post("/conversations/{conversation_id}/choices")
async def save_choices(conversation_id: str, body: SaveChoicesRequest, graph=Depends(get_graph)):
    """Save UI button selections deterministically (no LLM resolution).

    Resolves option_ids against available_options, snapshots label/price
    into the trip plan (replacement per single-choice category). Returns
    the saved labels; the frontend then sends the user message through
    the normal pipeline (like "Let's go with…"), where extract+router
    short-circuit on SAVED_CHOICES_PREFIX straight to main_llm.
    """
    if graph is None:
        raise HTTPException(status_code=503, detail="Graph not initialized")
    config = {"configurable": {"thread_id": conversation_id}}
    state = await graph.aget_state(config)
    values = state.values or {}
    avail = values.get("available_options") or {}
    plan = list(values.get("trip_plan") or [])

    def find(category: str, option_id: str):
        for opt in avail.get(category, []) or []:
            get = lambda name, default=None: (
                getattr(opt, name, default)
                if not isinstance(opt, dict) else opt.get(name, default)
            )
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
        item = PlanItem(
            category=ch.category,
            option_id=str(ch.option_id),
            label=get("label", "") or str(ch.option_id),
            price=get("price"),
            currency=get("currency"),
            per_person=bool(get("per_person", False)),
            details=get("details", "") or "",
        )
        key = lambda it: (
            it["category"] if isinstance(it, dict) else it.category,
            str(it["option_id"] if isinstance(it, dict) else it.option_id),
        )
        if ch.category in SINGLE_CHOICE_CATEGORIES:
            plan = [it for it in plan if key(it)[0] != ch.category]
            plan.append(item)
        elif not any(key(it) == (ch.category, str(ch.option_id)) for it in plan):
            plan.append(item)
        saved.append(item.label)
    await graph.aupdate_state(config, {"trip_plan": plan})
    fresh = await graph.aget_state(config)
    return {"saved": saved, "plan": _plan_payload(fresh.values or {})}


@router.post("/conversations/{conversation_id}/messages")
async def send_message(conversation_id: str, body: SendMessageRequest, graph=Depends(get_graph)):
    if graph is None:
        raise HTTPException(status_code=503, detail="Graph not initialized")
    return StreamingResponse(
        _stream(graph, conversation_id, body.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


def _conv_to_dict(conv) -> dict:
    updated = conv.updated_at
    if updated is not None and updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    return {
        "id": conv.id,
        "title": conv.title,
        "updatedAt": updated.isoformat() if updated else None,
        "messageIds": [],
    }


def _stored_to_chat(msg) -> dict:
    created = msg.created_at
    if created is not None and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    out = {
        "id": f"srv-{msg.id}",
        "role": msg.role,
        "kind": msg.kind or "text",
        "text": msg.text or "",
        "createdAt": created.isoformat() if created else None,
    }
    if isinstance(msg.payload, dict) and "destinations" in msg.payload:
        out["destinations"] = msg.payload["destinations"]
    if isinstance(msg.payload, dict) and msg.payload.get("subagentResults"):
        out["subagentResults"] = [
            {"id": r.get("id", ""), "label": "", "text": r.get("text", "")}
            for r in msg.payload["subagentResults"]
            if isinstance(r, dict)
        ]
    return out


@router.get("/conversations")
async def list_conversations():
    async with AsyncSessionLocal() as session:
        convs = await repo.list_conversations(session)
        return {"conversations": [_conv_to_dict(c) for c in convs]}


@router.post("/conversations")
async def create_conversation(body: CreateConversationRequest):
    conversation_id = body.id.strip() if body.id and body.id.strip() else f"trip-{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as session:
        conv = await repo.ensure_conversation(session, conversation_id, body.title or "New trip")
        await session.commit()
        return _conv_to_dict(conv)


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    async with AsyncSessionLocal() as session:
        msgs = await repo.get_messages(session, conversation_id)
        return {"messages": [_stored_to_chat(m) for m in msgs]}


@router.get("/conversations/{conversation_id}/state")
async def get_conversation_state(conversation_id: str, graph=Depends(get_graph)):
    """Rehydrate side panels (requirements/options/plan) after a reload."""
    if graph is None:
        raise HTTPException(status_code=503, detail="Graph not initialized")
    state = await graph.aget_state({"configurable": {"thread_id": conversation_id}})
    values = state.values or {}
    options = {}
    for category, opts in (values.get("available_options") or {}).items():
        options[category] = [_option_to_dict(o) for o in (opts or [])]
    return {
        "requirements": _requirements_to_items(values.get("requirements")),
        "options": options,
        "plan": _plan_payload(values) if values.get("trip_plan") else None,
    }


@router.patch("/conversations/{conversation_id}")
async def rename_conversation(conversation_id: str, body: RenameConversationRequest):
    async with AsyncSessionLocal() as session:
        conv = await repo.rename_conversation(session, conversation_id, body.title.strip() or "Untitled trip")
        if conv is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        await session.commit()
        return _conv_to_dict(conv)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, graph=Depends(get_graph)):
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
            pass
    return {"deleted": conversation_id}


PLAN_DESCRIPTION_PROMPT = """
You write the opening paragraph of a saved trip plan, shown above the requirements and trip plan details.
Write one short paragraph of 3-5 sentences with an evocative travel-guide tone: the feel of the destination
at that time of year and the thread of this particular trip (what kind of experience it will be, drawn from
the interests and the saved picks).

Rules: do NOT repeat the requirements or list the plan items one by one — that information is already
visible below. Never mention prices, totals or budget. Never invent places, dates or activities beyond
the input; stay general when unsure ("riverside evenings", "day trips nearby") rather than naming
specifics not given. Plain prose only: no markdown, no bullets, no headings.
Reply in the same language as the requirements and plan labels.""".strip()


def _fallback_description(requirements: list[dict], payload: dict) -> str:
    by_key = {r.get("key"): r.get("value") for r in requirements if isinstance(r, dict)}
    dest = by_key.get("destination") or "your destination"
    dates = by_key.get("dates")
    travelers = by_key.get("travelers")
    n = len(payload.get("plan") or [])
    bits = f"Trip to {dest}"
    if dates:
        bits += f" ({dates})"
    if travelers:
        bits += f" for {travelers}"
    return f"{bits} with {n} saved choice(s). Details, totals and budget are listed below."


async def _describe_plan(requirements: list[dict], payload: dict) -> str:
    """Standalone light_llm call (not the graph): the input is just the snapshot."""
    confirmed = [f"{r.get('label')}: {r.get('value')}" for r in requirements if isinstance(r, dict) and r.get("value")]
    picks = [f"{i.get('category')}: {i.get('label')}" for i in (payload.get("plan") or []) if isinstance(i, dict)]
    summary = "Requirements:\n" + ("\n".join(f"- {c}" for c in confirmed) or "- (none)") + "\n"
    summary += "Plan:\n" + ("\n".join(f"- {p}" for p in picks) or "- (empty)")
    try:
        msg = await light_llm.ainvoke([
            SystemMessage(content=PLAN_DESCRIPTION_PROMPT),
            HumanMessage(content=summary),
        ])
        text = (getattr(msg, "content", "") or "").strip()
        return text or _fallback_description(requirements, payload)
    except Exception:
        return _fallback_description(requirements, payload)


def _saved_plan_to_dict(row) -> dict:
    created = row.created_at
    if created is not None and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    payload = dict(row.plan or {})
    return {
        "id": str(row.id),
        "title": row.title,
        "description": row.description or "",
        "conversationId": row.conversation_id,
        "requirements": row.requirements or [],
        "plan": payload.get("plan") or [],
        "total": payload.get("total", 0),
        "currency": payload.get("currency"),
        "budget": payload.get("budget"),
        "overBudget": bool(payload.get("overBudget", False)),
        "createdAt": created.isoformat() if created else None,
        # Card subtitle: prefer the saved Dates requirement, else creation date.
        "destination": next(
            (r.get("value") for r in (row.requirements or []) if isinstance(r, dict) and r.get("key") == "destination" and r.get("value")),
            "",
        ),
        "dates": next(
            (r.get("value") for r in (row.requirements or []) if isinstance(r, dict) and r.get("key") == "dates" and r.get("value")),
            "",
        ),
    }


@router.post("/conversations/{conversation_id}/plans")
async def save_plan(conversation_id: str, body: SavePlanRequest, graph=Depends(get_graph)):
    """Snapshot destination + requirements + trip plan + budget as a new saved plan."""
    if graph is None:
        raise HTTPException(status_code=503, detail="Graph not initialized")
    state = await graph.aget_state({"configurable": {"thread_id": conversation_id}})
    values = state.values or {}
    requirements = _requirements_to_items(values.get("requirements"))
    payload = _plan_payload(values)
    destination = next((r["value"] for r in requirements if r["key"] == "destination" and r["value"]), None)
    if not destination:
        raise HTTPException(status_code=422, detail="Set a destination before saving a plan")
    if not payload["plan"]:
        raise HTTPException(status_code=422, detail="Pick at least one option before saving a plan")
    title = (body.title or "").strip() or f"{destination} trip"
    description = await _describe_plan(requirements, payload)
    async with AsyncSessionLocal() as session:
        await repo.ensure_conversation(session, conversation_id)
        row = await repo.create_saved_plan(session, conversation_id, title, description, requirements, payload)
        await session.commit()
        return _saved_plan_to_dict(row)


@router.get("/plans")
async def list_plans():
    async with AsyncSessionLocal() as session:
        rows = await repo.list_saved_plans(session)
        return {"plans": [_saved_plan_to_dict(r) for r in rows]}


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: int):
    async with AsyncSessionLocal() as session:
        row = await repo.get_saved_plan(session, plan_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Plan not found")
        return _saved_plan_to_dict(row)


class RenamePlanRequest(BaseModel):
    title: str


@router.patch("/plans/{plan_id}")
async def rename_plan(plan_id: int, body: RenamePlanRequest):
    async with AsyncSessionLocal() as session:
        row = await repo.rename_saved_plan(session, plan_id, body.title.strip() or "Saved trip")
        if row is None:
            raise HTTPException(status_code=404, detail="Plan not found")
        await session.commit()
        return _saved_plan_to_dict(row)


@router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: int):
    async with AsyncSessionLocal() as session:
        ok = await repo.delete_saved_plan(session, plan_id)
        await session.commit()
    if not ok:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"deleted": plan_id}
