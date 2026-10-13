"""Destination research node: proposes candidates, then pauses for the pick.

The frontend sends the choice back as "Let's go with <name>" (`CHOOSE_PREFIX`);
anything else re-enters the graph flow: extract -> research.
"""
from langchain_core.messages import HumanMessage, SystemMessage
import logging
from langgraph.types import interrupt
from pydantic import BaseModel
from app.agents.ai_models import llm
from app.agents.state import DestinationCandidate, TravelState
from app.agents.usage import collect_usage
from app.agents.utils import sanitize_messages_for_llm

logger = logging.getLogger("uvicorn.error")

DESTINATION_RESEARCH_PROMPT = """
You are the destination discovery step of a travel planner.

Generate 3-5 diverse destinations that best match the user's explicit
requirements. Score and order them from best to worst fit.

For each candidate provide:
- destination
- score from 0 to 10 (one decimal allowed)
- reason: a short overview of the destination followed by brief points
  explaining how it matches the user's main requirements.
- country: the country the destination is in
- country_code: its ISO 3166-1 alpha-2 code in lowercase (e.g. "es" for
  Spain, "pt" for Portugal); exactly two letters, no exceptions
- highlights: 2-3 short bullets on why it fits these requirements
- drawback: one honest, brief downside for this trip (may be empty only
  if there is genuinely nothing relevant to flag)

Score how well the destination matches the user's requirements, not how
popular or attractive it is in general.

Use only explicit requirements. Do not invent preferences.

General, non-time-specific facts about climate, relative affordability,
culture, food, etc. are allowed. Do not provide specific prices,
availability, or other precise future-dependent facts.
"""

class DestinationResearchResult(BaseModel):
    candidates: list[DestinationCandidate]

destination_llm = llm.with_structured_output(
    DestinationResearchResult,
    # Raw response kept for turn usage stats; parse errors stay raising.
    include_raw=True,
)

async def destination_research(state: TravelState, config: dict | None = None):
    """Generate scored destination candidates from explicit requirements.

    Args:
        state: Current graph state holding requirements and messages.
        config: Optional LangGraph invoke config carrying the thread id.

    Returns:
        Partial state update with destination candidates and turn usage.

    Raises:
        Exception: Reraised structured-output parsing error when candidates are unparseable.
    """
    requirements = state["requirements"]

    result = await destination_llm.ainvoke([
        SystemMessage(content=DESTINATION_RESEARCH_PROMPT),
        SystemMessage(content=f"Current travel requirements:\n{requirements}"),
        *sanitize_messages_for_llm(state["messages"]),
    ])
    if result.get("parsing_error") is not None:
        raise result["parsing_error"]

    candidates = result["parsed"].candidates
    logger.info(
        "[%s] destination_research: %d candidates (%s)",
        (config or {}).get("configurable", {}).get("thread_id", "?"),
        len(candidates),
        ", ".join(getattr(c, "destination", "?") for c in candidates),
    )
    return {
        "destination_candidates": candidates,
        "turn_usage": collect_usage([result["raw"]], "destination_research"),
    }

# Protocol with the frontend (see `ChatView.onChoose`): the carousel Choose
# button always resumes with "Let's go with <name>.". Anything else is a
# free-text reply (a change request or a manual selection) and needs the
# full extract -> router loop.
CHOOSE_PREFIX = "Let's go with "


def route_after_decision(state: TravelState):
    """Fast path for carousel selections, full loop for change requests.

    Args:
        state: Current graph state holding messages with the user reply.

    Returns:
        Next node name after the destination decision.
    """
    messages = state.get("messages") or []
    last_human = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)),
        None,
    )
    content = getattr(last_human, "content", "") or ""
    if isinstance(content, str) and content.startswith(CHOOSE_PREFIX):
        return "main_llm"
    return "extract_requirements"


# ------------------------------------------------------------------------------
# Presents the candidates to the user (via an SSE `destinations` message, see
# `api/v1/streaming.py`) and pauses for the user's decision.
# On resume returns both the context SystemMessage (recommendations were
# already presented) and the user's reply as HumanMessage, in that order.
def wait_for_decision(state: TravelState):
    """Pause for the user destination decision and resume with their reply.

    The carousel message already invites the user to choose, so the
    interrupt carries no prompt value and the resume wraps the reply with
    context that recommendations were presented.

    Args:
        state: Current graph state at the destination decision checkpoint.

    Returns:
        Partial state update with the context and user reply messages.
    """
    # No prompt text: the destinations carousel message already invites the
    # user to choose. A valueless interrupt still pauses/resumes the graph;
    # `api/v1/streaming.py` skips non-string interrupt values instead of
    # displaying them.
    user_input = interrupt(None)

    return {
        "messages": [
            SystemMessage(
                content=(
                    "Destination research has been completed and the recommendations "
                    "were presented to the user. The next user message is a response "
                    "to those recommendations and may select or modify a destination."
                )
            ),
            HumanMessage(content=user_input),
        ]
    }