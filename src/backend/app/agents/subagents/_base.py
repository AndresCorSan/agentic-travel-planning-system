from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import tools_condition

class SubagentState(TypedDict):
    task: str
    messages: Annotated[list, add_messages]
    result: str | None

# Helper for storing the subagent's response into the main graph's state
def finalize_subagent(state: SubagentState):
    return {
        "result": state["messages"][-1].content
    }

# Helper for building each subagent's graph
def build_subagent_graph(agent_node, tool_node):
    graph_builder = StateGraph(SubagentState)

    graph_builder.add_node("agent", agent_node)
    graph_builder.add_node("tools", tool_node)
    graph_builder.add_node("finalize", finalize_subagent)

    graph_builder.add_edge(START, "agent")
    graph_builder.add_conditional_edges(
        "agent",
        tools_condition,
        {
            "tools": "tools",
            END: "finalize",
        },
    )
    graph_builder.add_edge("tools", "agent")
    graph_builder.add_edge("finalize", END)

    return graph_builder.compile()