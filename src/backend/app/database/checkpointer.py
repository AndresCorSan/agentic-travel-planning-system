"""AsyncSqliteSaver factory for LangGraph checkpointing.

Kept in its own file/DB so graph execution state stays a separate concern
from app data (architecture.md section 9).
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from app.database.database import resolve_sqlite_path

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_DEFAULT_CHECKPOINTS = _BACKEND_DIR / "data" / "checkpoints.db"


def checkpoint_path() -> Path:
    """Resolve the LangGraph checkpoint database path.

    Reads CHECKPOINT_DB_URL and falls back to data/checkpoints.db, accepting
    the same formats as DATABASE_URL (full URL or plain path).

    Returns:
        The resolved checkpoint database path.
    """
    raw = os.getenv("CHECKPOINT_DB_URL", str(_DEFAULT_CHECKPOINTS))
    # Same formats as DATABASE_URL (full URL or plain path).
    return resolve_sqlite_path(raw)


@asynccontextmanager
async def checkpoint_saver():
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    path = checkpoint_path()
    if str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(path)) as saver:
        yield saver
