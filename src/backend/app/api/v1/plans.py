"""Saved trip-plan endpoints: snapshot CRUD + LLM-written description."""

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.dependencies import get_graph
from app.agents.ai_models import light_llm
from app.api.v1.presenters import plan_payload, requirements_to_items, saved_plan_to_dict
from app.api.v1.schemas import RenamePlanRequest, SavePlanRequest
from app.api.v1.streaming import trace_config
from app.database.database import AsyncSessionLocal
from app.database import repositories as repo

router = APIRouter()

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


async def _describe_plan(requirements: list[dict], payload: dict, conversation_id: str) -> str:
    """Standalone light_llm call (not the graph): the input is just the snapshot."""
    confirmed = [f"{r.get('label')}: {r.get('value')}" for r in requirements if isinstance(r, dict) and r.get("value")]
    picks = [f"{i.get('category')}: {i.get('label')}" for i in (payload.get("plan") or []) if isinstance(i, dict)]
    summary = "Requirements:\n" + ("\n".join(f"- {c}" for c in confirmed) or "- (none)") + "\n"
    summary += "Plan:\n" + ("\n".join(f"- {p}" for p in picks) or "- (empty)")
    try:
        msg = await light_llm.ainvoke([
            SystemMessage(content=PLAN_DESCRIPTION_PROMPT),
            HumanMessage(content=summary),
        ], config=trace_config(conversation_id))
        text = (getattr(msg, "content", "") or "").strip()
        return text or _fallback_description(requirements, payload)
    except Exception:
        return _fallback_description(requirements, payload)


@router.post("/conversations/{conversation_id}/plans")
async def save_plan(conversation_id: str, body: SavePlanRequest, graph=Depends(get_graph)):
    """Snapshot destination + requirements + trip plan + budget as a new saved plan."""
    if graph is None:
        raise HTTPException(status_code=503, detail="Graph not initialized")
    state = await graph.aget_state({"configurable": {"thread_id": conversation_id}})
    values = state.values or {}
    requirements = requirements_to_items(values.get("requirements"))
    payload = plan_payload(values)
    destination = next((r["value"] for r in requirements if r["key"] == "destination" and r["value"]), None)
    if not destination:
        raise HTTPException(status_code=422, detail="Set a destination before saving a plan")
    if not payload["plan"]:
        raise HTTPException(status_code=422, detail="Pick at least one option before saving a plan")
    title = (body.title or "").strip() or f"{destination} trip"
    description = await _describe_plan(requirements, payload, conversation_id)
    async with AsyncSessionLocal() as session:
        await repo.ensure_conversation(session, conversation_id)
        row = await repo.create_saved_plan(session, conversation_id, title, description, requirements, payload)
        await session.commit()
        return saved_plan_to_dict(row)


@router.get("/plans")
async def list_plans():
    async with AsyncSessionLocal() as session:
        rows = await repo.list_saved_plans(session)
        return {"plans": [saved_plan_to_dict(r) for r in rows]}


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: int):
    async with AsyncSessionLocal() as session:
        row = await repo.get_saved_plan(session, plan_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Plan not found")
        return saved_plan_to_dict(row)


@router.patch("/plans/{plan_id}")
async def rename_plan(plan_id: int, body: RenamePlanRequest):
    async with AsyncSessionLocal() as session:
        row = await repo.rename_saved_plan(session, plan_id, body.title.strip() or "Saved trip")
        if row is None:
            raise HTTPException(status_code=404, detail="Plan not found")
        await session.commit()
        return saved_plan_to_dict(row)


@router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: int):
    async with AsyncSessionLocal() as session:
        ok = await repo.delete_saved_plan(session, plan_id)
        await session.commit()
    if not ok:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"deleted": plan_id}
