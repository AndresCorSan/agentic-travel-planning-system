from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from app.agents.nodes.destinations import destination_research, display_destination_results, wait_for_decision
from app.agents.nodes.extract import extract_requirements
from app.agents.nodes.main_llm import main_llm_node, main_tools
from app.agents.nodes.orchestrator import orchestrator, route_to_agents, set_available_agents
from app.agents.nodes.router import research_router, route_next
from app.agents.state import TravelState
from app.agents.subagents.accommodation import build_accommodation_subgraph
from app.agents.subagents.activities import build_activities_subgraph
from app.agents.subagents.rental_cars import build_rental_cars_subgraph
from app.agents.subagents.transportation import build_transportation_subgraph
from app.agents.subagents.weather import build_weather_subgraph

def build_graph(mcp_tools, checkpointer=None):
    builder = StateGraph(TravelState)

    # ---- Nodes ----
    builder.add_node("extract_requirements", extract_requirements)
    builder.add_node("router", research_router)

    builder.add_node("destination_research", destination_research)
    # TODO(phase8): display_results (print) and wait_for_decision (console
    # interrupt) block the request; replace with SSE events / resume endpoint.
    builder.add_node("display_results", display_destination_results)
    builder.add_node("wait_for_decision", wait_for_decision)

    # Parallel multi-agent orchestration. Only subagents with working
    # MCP tools are registered; the orchestrator is told which are on.
    builder.add_node("orchestrator", orchestrator)
    subagents = {}
    if mcp_tools.get("weather_tools"):
        subagents["weather_agent"] = build_weather_subgraph(mcp_tools["weather_tools"])
    if mcp_tools.get("trvl_tool"):
        subagents["accommodation_agent"] = build_accommodation_subgraph(mcp_tools["trvl_tool"])
        subagents["transportation_agent"] = build_transportation_subgraph(mcp_tools["trvl_tool"])
    if mcp_tools.get("ticketlens_tools"):
        subagents["activities_agent"] = build_activities_subgraph(mcp_tools["ticketlens_tools"])
    if mcp_tools.get("rental_cars_tool"):
        subagents["rental_cars_agent"] = build_rental_cars_subgraph(mcp_tools["rental_cars_tool"])
    set_available_agents(list(subagents))
    for name, run_fn in subagents.items():
        builder.add_node(name, run_fn)
    builder.add_node("main_llm", main_llm_node)
    builder.add_node("main_tools", ToolNode(main_tools))

    # ---- Edges ----
    builder.add_edge(START, "extract_requirements")
    builder.add_edge("extract_requirements", "router")

    builder.add_conditional_edges(
        "router",
        route_next,
        {
            "destination_research": "destination_research",
            "orchestrator": "orchestrator",
            "main_llm": "main_llm",
        },
    )

    builder.add_edge("destination_research", "display_results")
    builder.add_edge("display_results", "wait_for_decision")
    builder.add_edge("wait_for_decision", "main_llm")

    # New edges for parallel multi-agent orchestration
    builder.add_conditional_edges(
        "orchestrator",
        route_to_agents,
        list(subagents) + ["main_llm"],
    )
    # Bind agents to main LLM
    for name in subagents:
        builder.add_edge(name, "main_llm")
    builder.add_conditional_edges(
        "main_llm",
        tools_condition,
        {
            "tools": "main_tools",
            END: END,
        },
    )
    builder.add_edge("main_tools", "main_llm")

    # ---- Compile ----
    if checkpointer is None:
        checkpointer = InMemorySaver()
    return builder.compile(checkpointer=checkpointer)
