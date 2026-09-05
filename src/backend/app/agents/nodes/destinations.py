from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt
from pydantic import BaseModel
from app.agents.llm import llm
from app.agents.state import DestinationCandidate, TravelState
from app.agents.utils import sanitize_messages_for_llm

DESTINATION_RESEARCH_PROMPT = """
You are the destination discovery step of a travel planner.

Generate 3-5 diverse destinations that best match the user's explicit
requirements. Score and order them from best to worst fit.

For each candidate provide:
- destination
- score from 0 to 10 (one decimal allowed)
- reason: a short overview of the destination followed by brief points
  explaining how it matches the user's main requirements.

Score how well the destination matches the user's requirements, not how
popular or attractive it is in general.

Use only explicit requirements. Do not invent preferences.

General, non-time-specific facts about climate, relative affordability,
culture, food, etc. are allowed. Do not provide specific prices,
availability, or other precise future-dependent facts.
"""

class DestinationResearchResult(BaseModel):
    candidates: list[DestinationCandidate]

destination_llm = llm.with_structured_output(DestinationResearchResult)

async def destination_research(state: TravelState):
    # TODO(phase8): replace print with structured logging (app.core.logging).

    requirements = state["requirements"]

    response = await destination_llm.ainvoke([
        SystemMessage(content=DESTINATION_RESEARCH_PROMPT),
        SystemMessage(content=f"Current travel requirements:\n{requirements}"),
        *sanitize_messages_for_llm(state["messages"]),
    ])

    return {
        "destination_candidates": response.candidates
    }

# ------------------------------------------------------------------------------
# TODO(phase8): replace console helpers with API/SSE responses.
# display_destination_results (print) and wait_for_decision (console interrupt)
# block the request in a backend context; they should become SSE events /
# Command(resume=...) via endpoint instead of graph nodes.
def display_destination_results(state: TravelState):
    destinations = state["destination_candidates"]

    print("\n" + "=" * 60)
    print("DESTINATION RECOMMENDATIONS")
    print("=" * 60)

    for i, candidate in enumerate(destinations, 1):
        print(f"\n{i}. {candidate.destination} — {candidate.score:.1f}/10")
        print(f"   {candidate.reason}")

    return {
        # Provide context to the next LLM call that destination research has been completed
        "messages": [
            SystemMessage(
                content=(
                    "Destination research has been completed and the recommendations "
                    "were presented to the user. The next user message is a response "
                    "to those recommendations and may select or modify a destination."
                )
            )
        ]
    }

def wait_for_decision(state: TravelState):
    user_input = interrupt("Choose a destination or provide another preference.")

    return {
        "messages": [
            HumanMessage(content=user_input)
        ]
    }