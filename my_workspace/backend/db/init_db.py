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
    SQLite's ALTER TABLE does not support IF NOT EXISTS — catch the error instead.
    """
    migrations = [
        # Phase: webcam support
        "ALTER TABLE cameras ADD COLUMN source_type VARCHAR(16) NOT NULL DEFAULT 'rtsp'",
        "ALTER TABLE cameras ADD COLUMN device_index INTEGER",
        # Phase: hotplug / index-stability
        "ALTER TABLE cameras ADD COLUMN device_name VARCHAR(256)",
        # Phase: Advanced Rule Engine (Logic Trees)
        "ALTER TABLE rules ADD COLUMN logic TEXT",
        # Phase: Behavior-specific parameters
        "ALTER TABLE rules ADD COLUMN behavior_params TEXT",
    ]
    async with engine.begin() as conn:
        for sql in migrations:
            try:
                await conn.execute(text(sql))
                logger.info("Migration applied: %s", sql[:60])
            except Exception:
                pass  # Column already exists — safe to ignore


async def drop_tables(engine: AsyncEngine) -> None:
    """Used in tests only."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
