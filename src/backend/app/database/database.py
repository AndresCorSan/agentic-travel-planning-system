"""Async SQLite engine + session factory (phase 9 persistence).

Single DATABASE_URL env so a future Postgres move is a config change, not
a code change. Defaults to a file DB under src/backend/data/ (gitignored).
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.models import Base

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_DEFAULT_DB = _BACKEND_DIR / "data" / "app.db"

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{_DEFAULT_DB}")

engine = create_async_engine(DATABASE_URL, future=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Create data dir + tables (no Alembic yet: greenfield schema)."""
    # Ensure the SQLite file's parent exists (no-op for server DB URLs).
    if DATABASE_URL.startswith("sqlite"):
        path = DATABASE_URL.split("sqlite+aiosqlite:///")[-1].split("?")[0]
        parent = Path(path).expanduser().parent
        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
