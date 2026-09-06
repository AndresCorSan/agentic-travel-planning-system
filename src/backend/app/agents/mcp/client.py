import logging

from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger("uvicorn.error")

MCP_SERVERS = {
    "ticketlens": {
        "transport": "http",
        "url": "https://mcp.ticketlens.com/",
    },
    # Alternative OpenMeteo MCP for testing weather tools
    # https://github.com/cyanheads/open-meteo-mcp-server
    "weather": {
        "transport": "streamable_http",
        "url": "https://open-meteo.caseyjhand.com/mcp",
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

# Only these TicketLens tools are kept (see notebooks phase3-5).
TICKETLENS_TOOL_NAMES = {"search_pois", "search_tours", "get_tour"}


def create_mcp_client() -> MultiServerMCPClient:
    return MultiServerMCPClient(MCP_SERVERS)


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
            if t.name.startswith("openmeteo"):
                weather_tools.append(t)
            elif t.name in TICKETLENS_TOOL_NAMES:
                ticketlens_tools.append(t)
            elif t.name == "travel":
                trvl_tool = t
            elif t.name == "search":
                # Renamed to avoid conflicts with other MCPs
                t.name = "search_rental_cars"
                rental_cars_tool = t

    return {
        "weather_tools": weather_tools,
        "ticketlens_tools": ticketlens_tools,
        "trvl_tool": trvl_tool,
        "rental_cars_tool": rental_cars_tool,
    }
