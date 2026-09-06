from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv(override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.graph import build_graph
from app.agents.mcp.client import load_mcp_tools
from app.api.router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging

    logger = logging.getLogger("uvicorn.error")
    try:
        mcp_tools = await load_mcp_tools()
        logger.info(
            "MCP tools ready: weather=%d ticketlens=%d trvl=%s rental_cars=%s",
            len(mcp_tools["weather_tools"]),
            len(mcp_tools["ticketlens_tools"]),
            mcp_tools["trvl_tool"].name if mcp_tools["trvl_tool"] else None,
            mcp_tools["rental_cars_tool"].name if mcp_tools["rental_cars_tool"] else None,
        )
        app.state.graph = build_graph(mcp_tools)
        logger.info("Graph built: %d nodes", len(app.state.graph.get_graph().nodes))
        from app.agents.nodes.orchestrator import AVAILABLE_AGENTS

        logger.info("Enabled research agents: %s", ", ".join(AVAILABLE_AGENTS) or "none")
    except Exception:
        logger.exception("MCP/graph init failed, continuing without graph")
        app.state.graph = None
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
