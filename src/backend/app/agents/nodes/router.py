from typing import Literal
from langchain_core.messages import SystemMessage
from pydantic import BaseModel
from app.agents.llm import light_llm
from app.agents.state import TravelState
from app.agents.utils import sanitize_messages_for_llm

RESEARCH_ROUTER_PROMPT = """
You are a travel-planning router.

Decide what should happen next based on the user's latest message.

Set route="main_llm" when no research is needed: greetings, small talk,
thanks, or questions answerable from the current conversation state
without calling any research tools.

Set route="destination_research" when the user has not committed to a single
destination and would benefit from discovering, comparing, or selecting
destinations. This includes requests that provide multiple destinations and
ask to compare or choose between them.

Set route="orchestrator" when the user has clearly chosen one specific
destination or asks for concrete options (hotels, flights, activities,
transport, rental cars, weather) that require specialist research.

Base the decision only on the user's request. Do not invent requirements.
"""

class ResearchDecision(BaseModel):
    route: Literal["destination_research", "orchestrator", "main_llm"]

structured_router_llm = light_llm.with_structured_output(ResearchDecision)

async def research_router(state: TravelState):
    response = await structured_router_llm.ainvoke([
        SystemMessage(content=RESEARCH_ROUTER_PROMPT),
        *sanitize_messages_for_llm(state["messages"]),
    ])

    return {"next_step": response.route}


def route_next(state: TravelState):
    """Router for the router node: research, orchestration, or direct reply."""
    return state.get("next_step") or "main_llm"
