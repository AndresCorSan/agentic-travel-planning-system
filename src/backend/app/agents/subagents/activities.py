from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode
from app.agents.llm import subagent_llm
from app.agents.subagents._base import SubagentState, build_subagent_graph
from app.agents.utils import current_date_message, sanitize_messages_for_llm

from app.agents.utils import sanitize_messages_for_llm

ACTIVITIES_AGENT_PROMPT = """
You are the activities and experiences research specialist.

Complete the assigned research task using the available TicketLens tools.

Search for activities, attractions, tours, and experiences relevant to the
destination, travel dates, and user's interests.

Use multiple tool calls when useful and retrieve additional details when the
task requires them.

Do not research flights, accommodations, weather, or rental cars.

Output:
- Report only the 3-5 most relevant activities with their key factual details
  and a short summary of the remaining results.
- When comparing several activities, use a table whenever practical; otherwise
  organize them into short sections.
- For each activity, include its name, type, location, price, availability,
  rating, and booking information when returned by the tools.
- Distinguish confirmed tool data from missing or uncertain information.
- Do not invent opening times, prices, availability, or activity details.
- End with a brief "Key findings" section for the main travel planner.
"""


def build_activities_subgraph(ticketlens_tools):
    bound_llm = subagent_llm.bind_tools(ticketlens_tools)

    async def activities_agent(state: SubagentState):
        task = state["task"]

        response = await bound_llm.ainvoke([
            SystemMessage(content=ACTIVITIES_AGENT_PROMPT),
            SystemMessage(content=f"Assigned task:\n{task}"),
            current_date_message(),
            *sanitize_messages_for_llm(state["messages"]),
        ])

        return {"messages": [response]}

    subgraph = build_subagent_graph(
        activities_agent,
        ToolNode(ticketlens_tools)
    )

    async def run_activities_agent(state: SubagentState):
        result = await subgraph.ainvoke({
            "task": state["task"],
            "messages": [],
            "result": None,
        })

        return {
            "activity_results": [result["result"]]
        }

    return run_activities_agent
