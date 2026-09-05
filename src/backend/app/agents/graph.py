from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from app.agents.nodes.destinations import destination_research, display_destination_results, wait_for_decision
from app.agents.nodes.extract import extract_requirements
from app.agents.nodes.main_llm import main_llm_node, main_tools
from app.agents.nodes.orchestrator import orchestrator, route_to_agents
from app.agents.nodes.router import research_router, route_destination_research
from app.agents.state import TravelState
from app.agents.subagents.accommodation import run_accommodation_agent
from app.agents.subagents.activities import run_activities_agent
from app.agents.subagents.rental_cars import run_rental_cars_agent
from app.agents.subagents.transportation import run_transportation_agent
from app.agents.subagents.weather import run_weather_agent

def build_graph(checkpointer=None):
    builder = StateGraph(TravelState)

    # ---- Nodes ----
    builder.add_node("extract_requirements", extract_requirements)
    builder.add_node("router", research_router)

    builder.add_node("destination_research", destination_research)
    # TODO(phase8): display_results (print) and wait_for_decision (console
    # interrupt) block the request; replace with SSE events / resume endpoint.
    builder.add_node("display_results", display_destination_results)
    builder.add_node("wait_for_decision", wait_for_decision)

    # Parallel multi-agent orchestration (wrappers own their subgraphs)
    builder.add_node("orchestrator", orchestrator)
    builder.add_node("weather_agent", run_weather_agent)
    builder.add_node("accommodation_agent", run_accommodation_agent)
    builder.add_node("transportation_agent", run_transportation_agent)
    builder.add_node("activities_agent", run_activities_agent)
    builder.add_node("rental_cars_agent", run_rental_cars_agent)
    builder.add_node("main_llm", main_llm_node)
    builder.add_node("main_tools", ToolNode(main_tools))

    # ---- Edges ----
    builder.add_edge(START, "extract_requirements")
    builder.add_edge("extract_requirements", "router")

    builder.add_conditional_edges(
        "router",
        route_destination_research,
        {
            "destination_research": "destination_research",
            "orchestrator": "orchestrator",
        },
    )

    builder.add_edge("destination_research", "display_results")
    builder.add_edge("display_results", "wait_for_decision")
    builder.add_edge("wait_for_decision", "main_llm")

    # New edges for parallel multi-agent orchestration
    builder.add_conditional_edges(
        "orchestrator",
        route_to_agents,
        [
            "weather_agent",
            "accommodation_agent",
            "transportation_agent",
            "activities_agent",
            "rental_cars_agent",
        ],
    )
    # Bind agents to main LLM
    builder.add_edge("weather_agent", "main_llm")
    builder.add_edge("accommodation_agent", "main_llm")
    builder.add_edge("transportation_agent", "main_llm")
    builder.add_edge("activities_agent", "main_llm")
    builder.add_edge("rental_cars_agent", "main_llm")
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
