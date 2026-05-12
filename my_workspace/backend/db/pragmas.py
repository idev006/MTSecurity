"""SQLite performance and safety pragmas applied at connection startup."""

from __future__ import annotations

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine


def apply_pragmas(engine: AsyncEngine) -> None:
    """Register SQLite pragmas via sync event (aiosqlite runs them on connect)."""

    @event.listens_for(engine.sync_engine, "connect")
    def set_pragmas(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")   # 64 MB page cache
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()
