"""Orchestrator node: turns requirements into parallel subagent tasks.

Invalid plans degrade to main_llm instead of failing; agent invocations
are guarded so one missing toolset never kills the turn.
"""
from langchain_core.messages import SystemMessage
from langgraph.types import Send
import logging
from app.agents.ai_models import llm
from app.agents.state import OrchestrationPlan, TravelState
from app.agents.usage import collect_usage
from app.agents.utils import current_date_message, sanitize_messages_for_llm

logger = logging.getLogger("uvicorn.error")

AGENT_DESCRIPTIONS = {
    "weather_agent": "weather and climate information",
    "accommodation_agent": "hotels and other accommodation options",
    "transportation_agent": "flights, trains, buses, and ferries",
    "activities_agent": "attractions, activities, tours, and experiences",
    "rental_cars_agent": "rental car options",
}

# Agents with working tools, set by build_graph at startup. If an MCP
# server is down, its agents are hidden from the orchestrator instead
# of failing the whole backend.
AVAILABLE_AGENTS: list[str] = list(AGENT_DESCRIPTIONS)


def set_available_agents(names: list[str]) -> None:
    global AVAILABLE_AGENTS
    AVAILABLE_AGENTS = [n for n in names if n in AGENT_DESCRIPTIONS]


ORCHESTRATOR_PROMPT_TEMPLATE = """
You are the travel research orchestrator. You NEVER answer the user directly.

Based on the user's latest request and current travel requirements, decide
which specialist agents are needed to provide the requested information.

Available agents:
{agents}

Only activate agents relevant to the user's request. Never select an agent
that is not in the available list above.

If no specialist research is needed (e.g. a general question answerable
from general knowledge), return an empty task list — do not write an answer
yourself.

For each selected agent, write a clear task describing exactly what it should
research, using the user's requirements as context.

Each task must be self-contained: include all information the specialist
needs to perform its research without accessing the main conversation state.
Do not omit known dates, locations, travelers, budget, or relevant constraints.

Do not perform research yourself and do not invent requirements.
"""

orchestrator_llm = llm.with_structured_output(
    OrchestrationPlan,
    # Keep the raw response for usage stats; parse errors land in
    # parsing_error instead of raising (same fallback as before).
    include_raw=True,
)

async def orchestrator(state: TravelState, config: dict | None = None):
    requirements = state["requirements"]
    agents = "\n".join(f"- {name}: {AGENT_DESCRIPTIONS[name]}" for name in AVAILABLE_AGENTS)

    result = await orchestrator_llm.ainvoke([
        SystemMessage(content=ORCHESTRATOR_PROMPT_TEMPLATE.format(agents=agents)),
        SystemMessage(
            content=f"Current travel requirements:\n{requirements}"
        ),
        current_date_message(),
        *sanitize_messages_for_llm(state["messages"]),
    ])
    usage = collect_usage([result["raw"]], "orchestrator")

    # The model may emit a tool call it saw in the conversation history
    # (e.g. update_requirements) instead of the OrchestrationPlan schema,
    # or answer conversationally: in that case there is nothing to
    # delegate and main_llm takes over.
    parsed = result.get("parsed")
    if result.get("parsing_error") is not None or parsed is None:
        logger.warning("Orchestrator emitted invalid schema; delegating to main_llm")
        tasks = []
    else:
        tasks = parsed.tasks
    logger.info(
        "[%s] orchestrator: %d tasks (%s)",
        (config or {}).get("configurable", {}).get("thread_id", "?"),
        len(tasks),
        ", ".join(t.agent for t in tasks),
    )
    return {
        "orchestration_plan": tasks,
        "turn_usage": usage,
    }


def route_to_agents(state: TravelState):
    """Fan-out: Send each AgentTask to its specialist subagent."""
    plan = state.get("orchestration_plan") or []
    tasks = [t for t in plan if t.agent in AVAILABLE_AGENTS]
    if len(tasks) < len(plan):
        logger.warning(
            "Orchestrator dropped unavailable agents: %s",
            sorted({t.agent for t in plan} - {t.agent for t in tasks}),
        )
    if not tasks:
        return "main_llm"
    return [
        Send(
            task.agent,
            {
                "task": task.task,
                "messages": [],
                "result": None,
            },
        )
        for task in tasks
    ]
