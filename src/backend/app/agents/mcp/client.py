import functools
import logging

from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger("uvicorn.error")

MCP_SERVERS = {
    "ticketlens": {
        "transport": "http",
        "url": "https://mcp.ticketlens.com/",
    },
    "weather": {
        "transport": "stdio",
        "command": "npx",
        "args": [
            "-y",
            "@dangahagan/weather-mcp@latest"
        ],
        "env": {
            "ENABLED_TOOLS": "basic,+historical,+air_quality",
            "WEATHER_UNITS": "metric"
        },
    },
    "trvl": {
        "transport": "stdio",
        "command": "trvl",
        "args": ["mcp"],
    },
    "octotrip-rental-cars": {
        "transport": "http",
        "url": "https://mcp.octotrip.app/rental-cars/mcp",
    },
}

# From TicketLens and Weather MCPs, we only want a subset of the tools
TICKETLENS_TOOL_NAMES = {"search_pois", "search_tours", "get_tour"}
WEATHER_TOOL_NAMES = {
    "get_weather_summary", "get_forecast", "get_current_conditions",
    "get_alerts", "search_location", "get_historical_weather", "get_air_quality"
}

def create_mcp_client() -> MultiServerMCPClient:
    return MultiServerMCPClient(MCP_SERVERS)


def _guard_tool(tool):
    """Wrap an MCP tool so service failures come back as text, not exceptions.

    Without this, a transport failure (e.g. 429/500 from the MCP server)
    raises through ToolNode, kills the whole graph, and aborts the SSE
    stream. As plain text, the subagent LLM sees the failure and reports
    the limitation gracefully instead of crashing the flow.
    """
    run = tool.coroutine
    if run is None:
        return tool

    @functools.wraps(run)
    async def _safe_run(*args, **kwargs):
        try:
            return await run(*args, **kwargs)
        except Exception as e:
            logger.warning("MCP tool %s failed: %s", tool.name, e)
            error_text = (
                f"TOOL ERROR: '{tool.name}' failed "
                f"({type(e).__name__}: {e}). "
                "This data is unavailable right now. Do NOT retry the "
                "identical call more than once; report in your result which "
                "information is missing and why, without inventing it."
            )
            # MCP tools use response_format="content_and_artifact": the
            # coroutine must return a (content, artifact) tuple, not a str.
            if getattr(tool, "response_format", None) == "content_and_artifact":
                return error_text, None
            return error_text

    tool.coroutine = _safe_run
    return tool


async def load_mcp_tools() -> dict:
    """Fetch tools per server, tolerating individual server failures.

    Returns dict with weather_tools, ticketlens_tools, trvl_tool,
    rental_cars_tool. Entries for unreachable servers come back empty
    (lists) or None (single tools); the graph is built with whatever
    is available instead of failing the whole backend.
    """
    weather_tools = []
    ticketlens_tools = []
    trvl_tool = None
    rental_cars_tool = None

    for server_name, params in MCP_SERVERS.items():
        try:
            server_tools = await MultiServerMCPClient({server_name: params}).get_tools()
            logger.info("MCP server %s: %d tools loaded", server_name, len(server_tools))
        except Exception:
            logger.warning("Skipping MCP server %s: load failed", server_name, exc_info=True)
            continue
        for t in server_tools:
            t = _guard_tool(t)
            if t.name in TICKETLENS_TOOL_NAMES:
                ticketlens_tools.append(t)
            elif t.name == "travel":
                trvl_tool = t
            elif t.name == "search":
                # Renamed to avoid conflicts with other MCPs
                t.name = "search_rental_cars"
                rental_cars_tool = t
            elif t.name in WEATHER_TOOL_NAMES:
                weather_tools.append(t)

    return {
        "weather_tools": weather_tools,
        "ticketlens_tools": ticketlens_tools,
        "trvl_tool": trvl_tool,
        "rental_cars_tool": rental_cars_tool,
    }
