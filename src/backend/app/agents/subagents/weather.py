from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode
from app.agents.llm import subagent_llm
from app.agents.mcp.client import weather_tools
from backend.app.agents.subagents._base import SubagentState, build_subagent_graph
from app.agents.utils import sanitize_messages_for_llm

WEATHER_AGENT_PROMPT = """
You are the weather research specialist in a travel-planning system.

Complete the research task using the available weather tools.

Use the user's requirements and the task provided by the orchestrator.
Choose the appropriate weather tools and provide all required parameters.
You may make multiple tool calls when necessary.

Use forecast data when it is appropriate for the travel dates and historical
climate data when it helps describe typical conditions.

Avoid retrieving large raw datasets when a smaller query, summary, or aggregate
can answer the task. Do not request multi-year daily historical data unless it
is necessary. When historical data is useful, retrieve only the minimum period,
locations, and variables needed.

Prefer aggregated, summarized, or directly relevant weather information over
large collections of individual daily records.

Do not research other travel categories.

Output:
- Present the most relevant weather findings clearly and concisely.
- When comparing several periods, locations, or weather conditions, use a table
  when it improves clarity; otherwise organize the information into short sections.
- Report only the most relevant findings and include a short summary of any
  remaining results rather than listing everything.
- Distinguish forecast data, historical climate patterns, and uncertainty.
- Preserve dates and values exactly as returned by the tools.
- Do not invent specific weather conditions, forecasts, or climate statistics.
- End with a brief "Key findings" section for the main travel planner.
"""

weather_llm = subagent_llm.bind_tools(weather_tools)

async def weather_agent(state: SubagentState):
    task = state["task"]

    response = await weather_llm.ainvoke([
        SystemMessage(content=WEATHER_AGENT_PROMPT),
        SystemMessage(content=f"Assigned task:\n{task}"),
        *sanitize_messages_for_llm(state["messages"]),
    ])

    return {"messages": [response]}

weather_graph = build_subagent_graph(
    weather_agent, 
    ToolNode(weather_tools)
)
async def run_weather_agent(state: SubagentState):
    # Wrapper used to map the subagent's private state/output to the main TravelState.
    result = await weather_graph.ainvoke({
        "task": state["task"],
        "messages": [],
        "result": None,
    })

    return {
        "weather_results": [result["result"]]
    }