from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode
from app.agents.ai_models import subagent_llm
from app.agents.subagents._base import SubagentState, build_subagent_graph
from app.agents.utils import current_date_message, sanitize_messages_for_llm

ACCOMMODATION_AGENT_PROMPT = """
You are the accommodation research specialist in a travel-planning system.

Complete the assigned task using the TRVL travel tool.

For accommodation searches, always try search_accommodations first.
Use search_hotels only as a fallback when search_accommodations cannot satisfy
the task or when broad hotel discovery is explicitly requested.

For search_accommodations, provide all known required parameters explicitly:
location, check_in, check_out, guests, currency, and budget when available.
Use max_candidates=5 and max_offers=5 unless broader results are explicitly requested.

Use relevant filters when they match the task and are supported by the tool.

If the tool returns an error caused by incorrect arguments, correct them and retry.
Do not invent prices, availability, ratings, or other missing information.

Output:
- Report only the 3-5 most relevant accommodation offers with their key
  factual details and a short summary of the remaining results.
- When comparing several properties, use a table whenever practical.
- For each selected offer, clearly identify property, room, price, total price,
  taxes, cancellation/refundability, rating, and booking information when available.
- Clearly distinguish verified prices from lead-in, estimated, or unverified prices.
- Preserve tool-returned values exactly.
- Do not add property or neighborhood facts that were not returned by the tool.
- End with a brief "Key findings" section for the main travel planner.

Do not research flights, ground transport, weather, activities, or rental cars.
"""


def build_accommodation_subgraph(trvl_tool):
    bound_llm = subagent_llm.bind_tools([trvl_tool])

    async def accommodation_agent(state: SubagentState):
        task = state["task"]

        response = await bound_llm.ainvoke([
            SystemMessage(content=ACCOMMODATION_AGENT_PROMPT),
            SystemMessage(content=f"Assigned task:\n{task}"),
            current_date_message(),
            *sanitize_messages_for_llm(state["messages"]),
        ])

        return {"messages": [response]}

    subgraph = build_subagent_graph(
        accommodation_agent,
        ToolNode([trvl_tool])
    )

    async def run_accommodation_agent(state: SubagentState):
        result = await subgraph.ainvoke({
            "task": state["task"],
            "messages": [],
            "result": None,
        })

        return {
            "accommodation_results": [result["result"]]
        }

    return run_accommodation_agent
