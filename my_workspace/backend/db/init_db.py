"""Database initialisation — create all tables and apply lightweight migrations."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from models.base import Base

logger = logging.getLogger(__name__)


async def create_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created / verified")
    await _migrate(engine)


async def _migrate(engine: AsyncEngine) -> None:
    """
    Idempotent column additions for existing databases.

    SQLite: ALTER TABLE … ADD COLUMN does not support IF NOT EXISTS — catch the
    duplicate-column error instead.
    PostgreSQL: supports ADD COLUMN IF NOT EXISTS natively.
    Fresh databases (create_all handles all columns) — all statements are no-ops.
    """
    dialect = engine.dialect.name
    is_pg = dialect == "postgresql"

    # PostgreSQL supports IF NOT EXISTS; SQLite does not
    def _col(table: str, col: str, definition: str) -> str:
        if is_pg:
            return f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {definition}"
        return f"ALTER TABLE {table} ADD COLUMN {col} {definition}"

    migrations = [
        _col("cameras", "source_type", "VARCHAR(16) NOT NULL DEFAULT 'rtsp'"),
        _col("cameras", "device_index", "INTEGER"),
        _col("cameras", "device_name",  "VARCHAR(256)"),
        _col("rules",   "logic",        "TEXT"),
        _col("rules",   "behavior_params", "TEXT"),
    ]
    async with engine.begin() as conn:
        for sql in migrations:
            try:
                await conn.execute(text(sql))
                logger.info("Migration applied: %s", sql[:70])
            except Exception:
                pass  # Column already exists (SQLite) — safe to ignore


async def drop_tables(engine: AsyncEngine) -> None:
    """Used in tests only."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
