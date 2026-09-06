import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from pydantic import BaseModel

from app.core.dependencies import get_graph

router = APIRouter()


class SendMessageRequest(BaseModel):
    message: str


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
    try:
        state = await graph.aget_state(config)
        if state.interrupts:
            stream_input = Command(resume=message)
        else:
            yield _frame("status", {"text": "Understanding your request…"})
            stream_input = {"messages": [HumanMessage(content=message)]}
        async for mode, payload in graph.astream(
            stream_input, config=config, stream_mode=["updates", "messages"]
        ):
            if mode == "messages":
                chunk, metadata = payload
                if metadata.get("langgraph_node") != "main_llm":
                    continue
                content = getattr(chunk, "content", "")
                if isinstance(content, str) and content:
                    yield _frame("token", {"text": content})
            elif mode == "updates":
                if not isinstance(payload, dict):
                    continue
                for node, output in payload.items():
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
                    elif node == "orchestrator":
                        agents = [a for a in (_task_agent(t) for t in output.get("orchestration_plan", [])) if a]
                        if agents:
                            yield _frame("status", {"text": "Executing specialized subagents…"})
                            yield _frame("agents.start", {"agents": agents})
                    elif node in RESEARCH_KEY_BY_AGENT:
                        yield _frame("agent.done", {"id": node})
                        yield _frame(
                            "research.update",
                            {"key": RESEARCH_KEY_BY_AGENT[node], "state": "done"},
                        )
        final = await graph.aget_state(config)
        req = (final.values or {}).get("requirements")
        if req is not None:
            yield _frame("requirements.updated", {"requirements": _requirements_to_items(req)})
        for interrupt in final.interrupts or []:
            if isinstance(interrupt.value, str) and interrupt.value:
                yield _frame(
                    "message",
                    {
                        "message": {
                            "id": f"m{uuid.uuid4().hex[:8]}",
                            "role": "assistant",
                            "kind": "text",
                            "text": interrupt.value,
                            "createdAt": "now",
                        }
                    },
                )
        yield "event: done\ndata: {}\n\n"
    except Exception as exc:
        yield _frame("error", {"message": str(exc)})


@router.post("/conversations/{conversation_id}/messages")
async def send_message(conversation_id: str, body: SendMessageRequest, graph=Depends(get_graph)):
    if graph is None:
        raise HTTPException(status_code=503, detail="Graph not initialized")
    return StreamingResponse(
        _stream(graph, conversation_id, body.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
