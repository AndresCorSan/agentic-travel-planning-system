"""AsyncSqliteSaver factory for LangGraph checkpointing.

Kept in its own file/DB so graph execution state stays a separate concern
from app data (architecture.md section 9).
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_DEFAULT_CHECKPOINTS = _BACKEND_DIR / "data" / "checkpoints.db"


def checkpoint_path() -> Path:
    raw = os.getenv("CHECKPOINT_DB_URL", str(_DEFAULT_CHECKPOINTS))
    # Allow both plain paths and sqlite conn strings.
    for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
    return Path(raw).expanduser()


@asynccontextmanager
async def checkpoint_saver():
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    path = checkpoint_path()
    if str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(path)) as saver:
        yield saver
