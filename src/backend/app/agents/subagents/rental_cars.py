from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode
from app.agents.ai_models import low_reasoning_llm
from app.agents.subagents._base import SubagentState, build_subagent_graph
from app.agents.usage import collect_usage
from app.agents.utils import current_date_message, sanitize_messages_for_llm

RENTAL_CARS_AGENT_PROMPT = """
You are the rental-car research specialist.

Complete the assigned research task using the available rental-car tools.

Choose the appropriate tool and parameters based on the task.
Consider vehicle preferences, dates, pickup/dropoff location, passengers,
budget, and other explicitly stated constraints.

You may make multiple searches when necessary.
If a tool returns an error caused by incorrect arguments, correct the parameters
and retry.

Do not invent prices, vehicle availability, specifications, or missing information.

Output:
- Report only the 3-5 most relevant rental options with their key factual
  details and a short summary of the remaining results.
- When comparing several vehicles or rental options, use a table whenever practical.
- Clearly identify vehicle, rental period, pickup/dropoff location, price,
  rental conditions, and booking information when available.
- Preserve tool-returned values exactly.
- Distinguish verified prices from estimates or incomplete results.
- End with a brief "Key findings" section for the main travel planner.

Do not research flights, accommodations, weather, or activities.
"""


def build_rental_cars_subgraph(rental_cars_tool):
    bound_llm = low_reasoning_llm.bind_tools([rental_cars_tool])

    async def rental_cars_agent(state: SubagentState):
        task = state["task"]

        response = await bound_llm.ainvoke([
            SystemMessage(content=RENTAL_CARS_AGENT_PROMPT),
            SystemMessage(content=f"Assigned task:\n{task}"),
            current_date_message(),
            *sanitize_messages_for_llm(state["messages"]),
        ])

        return {"messages": [response]}

    subgraph = build_subagent_graph(
        rental_cars_agent,
        ToolNode([rental_cars_tool])
    )

    async def run_rental_cars_agent(state: SubagentState):
        result = await subgraph.ainvoke({
            "task": state["task"],
            "messages": [],
            "result": None,
        })

        return {
            "rental_car_results": [result["result"]],
            "turn_usage": collect_usage(result["messages"], "rental_cars_agent"),
        }

    return run_rental_cars_agent
