from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
from app.agents.llm import light_llm
from app.agents.state import TravelState
from app.agents.tools.plan import SAVED_CHOICES_PREFIX
from app.agents.utils import sanitize_messages_for_llm

RESEARCH_ROUTER_PROMPT = """
You are a travel-planning router.

Decide what should happen next based on the user's latest message.
Check the routes in this order and take the first one that fits.

1. Set route="main_llm" when no specialist research is needed:
   - greetings, small talk, thanks, goodbyes
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

structured_router_llm = light_llm.with_structured_output(ResearchDecision)

async def research_router(state: TravelState):
    messages = state.get("messages") or []
    # Saved-choices confirmations only need the main LLM to acknowledge:
    # skip the routing call and go straight there.
    if messages and isinstance(messages[-1], HumanMessage) and str(messages[-1].content or "").startswith(SAVED_CHOICES_PREFIX):
        return {"next_step": "main_llm"}
    response = await structured_router_llm.ainvoke([
        SystemMessage(content=RESEARCH_ROUTER_PROMPT),
        *sanitize_messages_for_llm(state["messages"]),
    ])

    return {"next_step": response.route}


def route_next(state: TravelState):
    """Router for the router node: research, orchestration, or direct reply."""
    return state.get("next_step") or "main_llm"
