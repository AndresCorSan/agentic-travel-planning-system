"""Routing node: Jev decision first, chat-LLM fallback, main_llm default.

Decides between destination research, subagent orchestration, or a
direct main-LLM reply. Never raises: any failure degrades to main_llm.
"""
from typing import Literal
import logging
from langchain_core.messages import SystemMessage
from pydantic import BaseModel
from app.agents.ai_models import JEV_CONFIDENCE_THRESHOLD, decide_route_via_jev, light_llm
from app.agents.state import TravelState
from app.agents.tools.plan import is_ui_choices_confirmation
from app.agents.usage import collect_usage
from app.agents.utils import sanitize_messages_for_llm

logger = logging.getLogger("uvicorn.error")

RESEARCH_ROUTER_PROMPT = """
You are a travel-planning router.

Decide what should happen next based on the user's latest message.
Check the routes in this order and take the first one that fits.

1. Set route="main_llm" when no specialist research is needed:
   - greetings, small talk, thanks, goodbyes
   - messages outside what the app covers (anything not about travel
     planning: e.g. coding, homework, general chit-chat topics) — the
     assistant should briefly decline and steer back to travel, never
     launch searches for these
   - stating a travel intent or naming a destination without requesting
     anything concrete yet — the assistant should acknowledge and ask what 
     to research next, not launch searches on its own
   - general information questions answerable from general knowledge
   - questions answerable from the current conversation state
   These need no research tools at all.

2. Set route="destination_research" when the user has not committed to a
   single destination and would benefit from discovering, comparing, or
   selecting destinations. This includes requests that provide multiple
   destinations and ask to compare or choose between them.

3. Set route="orchestrator" ONLY when the user explicitly asks for concrete,
   bookable options that require specialist research: specific hotels, flights,
   activities, transport, rental cars, or weather for a planned trip.
   A general question about a place is NOT enough — that is route 1.
   Merely naming a destination or expressing intent to travel, without
   asking for options, is NOT enough either — that is also route 1.

Base the decision only on the user's request. Do not invent requirements.
"""

class ResearchDecision(BaseModel):
    route: Literal["destination_research", "orchestrator", "main_llm"]


JEV_ROUTE_INSTRUCTIONS = (
    "Which route should handle the user's latest message? "
    "Check main_llm first, then destination_research, then orchestrator."
)

JEV_ROUTE_CRITERIA = {
    "main_llm": (
        "greetings, small talk, thanks, goodbyes; messages outside travel "
        "planning (coding, homework, or any non-travel topic) which the "
        "assistant must briefly decline; merely mentioning a trip "
        "or destination in passing without asking for anything (no ideas, "
        "recommendations, or options requested); general information "
        "questions answerable from general knowledge or the current "
        "conversation state. No research tools needed."
    ),
    "destination_research": (
        "user has not committed to a single destination and asks for "
        "destination ideas, suggestions, recommendations, or inspiration "
        "(e.g. 'where should I go', 'which city do you recommend'), "
        "or wants to discover, compare, or choose between destinations."
    ),
    "orchestrator": (
        "user explicitly asks for concrete, bookable options requiring "
        "specialist research: specific hotels, flights, activities, "
        "transport, rental cars, or weather for a planned trip."
    ),
}

structured_router_llm = light_llm.with_structured_output(
    ResearchDecision,
    # Raw response kept for turn usage stats; parse errors stay raising.
    include_raw=True,
)

async def research_router(state: TravelState, config: dict | None = None):
    """Decide which route should handle the latest message.

    Tries the Jev decision model first with a chat-LLM fallback, degrading
    to main_llm when the decision is unparseable.

    Args:
        state: Current graph state holding messages and requirements.
        config: Optional LangGraph invoke config carrying the thread id.

    Returns:
        Partial state update with the next step and turn usage.
    """
    tid = (config or {}).get("configurable", {}).get("thread_id", "?")
    messages = state.get("messages") or []
    # 1. Short-circuit: saved-choices confirmations only need the main LLM
    # to acknowledge, so skip the routing call and go straight there.
    if is_ui_choices_confirmation(messages):
        logger.info("[%s] router: route=main_llm (choices confirmation)", tid)
        return {"next_step": "main_llm"}

    # 2. Fast path: Jev decision model via OpenRouter (no text generation).
    # Falls back to the chat LLM on error, unknown choice, or low confidence.
    sanitized = sanitize_messages_for_llm(state["messages"])
    conversation = "\n".join(
        f"{getattr(m, 'type', 'message')}: {m.content}" for m in sanitized[-10:]
    )
    requirements = state.get("requirements")
    jev_state = {
        "requirements": str(requirements) if requirements else "none yet",
        "conversation": conversation,
    }
    jev_result = await decide_route_via_jev(
        state=jev_state,
        instructions=JEV_ROUTE_INSTRUCTIONS,
        criteria=JEV_ROUTE_CRITERIA,
    )
    if jev_result is not None:
        choice, confidence = jev_result
        if confidence >= JEV_CONFIDENCE_THRESHOLD:
            logger.info("[%s] router: route=%s (via jev, conf=%.2f)", tid, choice, confidence)
            return {"next_step": choice}

    # 3. Fallback: structured output from the chat LLM.
    result = await structured_router_llm.ainvoke([
        SystemMessage(content=RESEARCH_ROUTER_PROMPT),
        *sanitized,
    ])
    if result.get("parsing_error") is not None:
        logger.warning("Router decision unparseable; falling back to main_llm")
        # No next_step here: route_next defaults to main_llm when it is unset.
        return {"turn_usage": collect_usage([result["raw"]], "router")}

    logger.info("[%s] router: route=%s (via chat llm)", tid, result["parsed"].route)
    return {
        "next_step": result["parsed"].route,
        "turn_usage": collect_usage([result["raw"]], "router"),
    }


def route_next(state: TravelState):
    """Router for the router node: research, orchestration, or direct reply.

    Args:
        state: Current graph state holding the next step routing decision.

    Returns:
        Next node name, defaulting to main_llm when unset.
    """
    return state.get("next_step") or "main_llm"
