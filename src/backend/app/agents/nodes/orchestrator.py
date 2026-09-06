from langchain_core.messages import SystemMessage
from langgraph.types import Send
from app.agents.llm import llm
from app.agents.state import OrchestrationPlan, TravelState
from app.agents.utils import sanitize_messages_for_llm

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
You are the travel research orchestrator.

Based on the user's latest request and current travel requirements, decide
which specialist agents are needed to provide the requested information.

Available agents:
{agents}

Only activate agents relevant to the user's request. Never select an agent
that is not in the available list above.

For each selected agent, write a clear task describing exactly what it should
research, using the user's requirements as context.

Each task must be self-contained: include all information the specialist
needs to perform its research without accessing the main conversation state.
Do not omit known dates, locations, travelers, budget, or relevant constraints.

Do not perform research yourself and do not invent requirements.
"""

orchestrator_llm = llm.with_structured_output(OrchestrationPlan)

async def orchestrator(state: TravelState):
    requirements = state["requirements"]
    agents = "\n".join(f"- {name}: {AGENT_DESCRIPTIONS[name]}" for name in AVAILABLE_AGENTS)

    response = await orchestrator_llm.ainvoke([
        SystemMessage(content=ORCHESTRATOR_PROMPT_TEMPLATE.format(agents=agents)),
        SystemMessage(
            content=f"Current travel requirements:\n{requirements}"
        ),
        *sanitize_messages_for_llm(state["messages"]),
    ])

    return {
        "orchestration_plan": response.tasks
    }


def route_to_agents(state: TravelState):
    """Fan-out: Send each AgentTask to its specialist subagent."""
    tasks = [t for t in (state.get("orchestration_plan") or []) if t.agent in AVAILABLE_AGENTS]
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
