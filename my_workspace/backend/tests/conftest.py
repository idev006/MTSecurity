"""Shared pytest fixtures for all test suites."""

from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from models import Base
from protocol.message_bus import MessageBus


# ── Database ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db() -> AsyncSession:
    """In-memory SQLite — auto-created and auto-dropped per test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def db_factory():
    """Session factory for ConfigService tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


# ── MessageBus ────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def bus() -> MessageBus:
    """Real MessageBus — started and stopped per test."""
    b = MessageBus()
    await b.start()
    yield b
    await b.stop()


# ── FastAPI test client ───────────────────────────────────────────────────────

@pytest.fixture
def anyio_backend():
    return "asyncio"
