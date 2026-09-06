from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode
from app.agents.llm import subagent_llm
from app.agents.subagents._base import SubagentState, build_subagent_graph
from app.agents.utils import current_date_message, sanitize_messages_for_llm

from app.agents.utils import sanitize_messages_for_llm

TRANSPORTATION_AGENT_PROMPT = """
You are the transportation research specialist in a travel-planning system.

Complete the assigned task using the TRVL travel tool.

Use only transportation intents:
- search_flights for air travel.
- search_ground for trains, buses, and ferries.

For flights, use origin, destination, departure_date, and passengers when known.
For round trips, also provide return_date.

Use relevant filters when explicitly requested, such as cabin_class, max_stops,
max_price, max_duration, airlines, departure-time windows, or baggage requirements.

For ground transport, use from, to, date, and type when known.
type must be exactly one of: train, bus, ferry.

Use relevant ground filters when requested.

If the tool returns an error caused by incorrect arguments, correct the parameters
and retry. Do not invent prices, schedules, availability, or missing information.

Output:
- Report only the 3-5 most relevant transport options with their key factual
  details and a short summary of the remaining results.
- When comparing several options, use a table whenever practical.
- Clearly separate flights, trains, buses, and ferries when multiple modes are found.
- For each option, clearly identify price, duration, stops, times, and provider
  when available.
- Distinguish per-person prices from total prices.
- Preserve tool-returned values exactly and state uncertainty where present.
- End with a brief "Key findings" section for the main travel planner.

Do not research accommodations, weather, activities, or rental cars.
"""


def build_transportation_subgraph(trvl_tool):
    bound_llm = subagent_llm.bind_tools([trvl_tool])

    async def transportation_agent(state: SubagentState):
        task = state["task"]

        response = await bound_llm.ainvoke([
            SystemMessage(content=TRANSPORTATION_AGENT_PROMPT),
            SystemMessage(content=f"Assigned task:\n{task}"),
            current_date_message(),
            *sanitize_messages_for_llm(state["messages"]),
        ])

        return {"messages": [response]}

    subgraph = build_subagent_graph(
        transportation_agent,
        ToolNode([trvl_tool])
    )

    async def run_transportation_agent(state: SubagentState):
        result = await subgraph.ainvoke({
            "task": state["task"],
            "messages": [],
            "result": None,
        })

        return {
            "transportation_results": [result["result"]]
        }

    return run_transportation_agent
