from langchain_mcp_adapters.client import MultiServerMCPClient

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


async def load_mcp_tools(client: MultiServerMCPClient) -> dict:
    """Fetch all tools and split them per agent. Returns dict with
    weather_tools, ticketlens_tools, trvl_tool, rental_cars_tool."""
    tools = await client.get_tools()

    weather_tools = []
    ticketlens_tools = []
    trvl_tool = None
    rental_cars_tool = None

    for t in tools:
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
        else:
            continue

    return {
        "weather_tools": weather_tools,
        "ticketlens_tools": ticketlens_tools,
        "trvl_tool": trvl_tool,
        "rental_cars_tool": rental_cars_tool,
    }
