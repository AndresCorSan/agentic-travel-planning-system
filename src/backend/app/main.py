import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv(override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def _cors_origins() -> list[str]:
    raw = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:8080",
    )
    return [o.strip() for o in raw.split(",") if o.strip()]

from app.agents.graph import build_graph
from app.agents.mcp.client import load_mcp_tools
from app.api.router import router
from app.database.checkpointer import checkpoint_saver
from app.database.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging

    logger = logging.getLogger("uvicorn.error")
    try:
        await init_db()
        logger.info("App DB ready")
    except Exception:
        logger.exception("App DB init failed, continuing without persistence")
    try:
        async with checkpoint_saver() as saver:
            mcp_tools = await load_mcp_tools()
            logger.info(
                "MCP tools ready: weather=%d ticketlens=%d trvl=%s rental_cars=%s",
                len(mcp_tools["weather_tools"]),
                len(mcp_tools["ticketlens_tools"]),
                mcp_tools["trvl_tool"].name if mcp_tools["trvl_tool"] else None,
                mcp_tools["rental_cars_tool"].name if mcp_tools["rental_cars_tool"] else None,
            )
            app.state.graph = build_graph(mcp_tools, checkpointer=saver)
            logger.info("Graph built: %d nodes", len(app.state.graph.get_graph().nodes))
            from app.agents.nodes.orchestrator import AVAILABLE_AGENTS

            logger.info("Enabled research agents: %s", ", ".join(AVAILABLE_AGENTS) or "none")
            yield
    except Exception:
        logger.exception("MCP/graph init failed, continuing without graph")
        app.state.graph = None
        yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
