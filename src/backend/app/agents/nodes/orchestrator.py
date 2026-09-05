from langchain_core.messages import SystemMessage
from langgraph.types import Send
from app.agents.llm import llm
from app.agents.state import OrchestrationPlan, TravelState
from app.agents.utils import sanitize_messages_for_llm

ORCHESTRATOR_PROMPT = """
You are the travel research orchestrator.

Based on the user's latest request and current travel requirements, decide
which specialist agents are needed to provide the requested information.

Available agents:
- weather_agent: weather and climate information
- accommodation_agent: hotels and other accommodation options
- transportation_agent: flights, trains, buses, and ferries
- activities_agent: attractions, activities, tours, and experiences
- rental_cars_agent: rental car options

Only activate agents relevant to the user's request.

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

    response = await orchestrator_llm.ainvoke([
        SystemMessage(content=ORCHESTRATOR_PROMPT),
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
    return [
        Send(
            task.agent,
            {
                "task": task.task,
                "messages": [],
                "result": None,
            },
        )
        for task in state["orchestration_plan"]
    ]
