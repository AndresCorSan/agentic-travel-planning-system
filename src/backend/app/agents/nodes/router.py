from langchain_core.messages import SystemMessage
from pydantic import BaseModel
from app.agents.llm import light_llm
from app.agents.state import TravelState
from app.agents.utils import sanitize_messages_for_llm

RESEARCH_ROUTER_PROMPT = """
You are a travel-planning router.

Decide whether destination research is needed.

Set needs_research=true when the user has not committed to a single destination
and would benefit from discovering, comparing, or selecting destinations.
This includes requests that provide multiple destinations and ask to compare
or choose between them.

Set needs_research=false only when the user has clearly chosen one specific
destination, even if they want to research hotels, flights, activities, or
other options there.

Base the decision only on the user's request. Do not invent requirements.
"""

class ResearchDecision(BaseModel):
    needs_research: bool

structured_router_llm = light_llm.with_structured_output(ResearchDecision)

async def research_router(state: TravelState):
    response = await structured_router_llm.ainvoke([
        SystemMessage(content=RESEARCH_ROUTER_PROMPT),
        *sanitize_messages_for_llm(state["messages"]),
    ])

    return {"destination_research_needed": response.needs_research}


def route_destination_research(state: TravelState):
    """Router for the router node: destination research vs orchestrator."""
    if state["destination_research_needed"]:
        return "destination_research"
    return "orchestrator"
