"""Unit tests for auth router — login, logout, refresh, me."""

from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from auth.password import hash_password
from models.user import User


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _seed_user(db: AsyncSession, username="testadmin", password="Admin1234",
                     role="ADMIN") -> User:
    user = User(username=username, hashed_password=hash_password(password), role=role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def app(db_factory):
    from api.app import create_app
    from config import Settings
    from protocol.message_bus import MessageBus
    from ssot.config_service import ConfigService
    from ssot.state_registry import StateRegistry
    from db.session import init_engine, get_session_factory

    cfg = Settings(
        jwt_secret_key="test-secret-key-at-least-32-characters-long",
        encryption_key="ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=",
    )
    engine = init_engine("sqlite+aiosqlite:///:memory:")
    from models.base import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    bus = MessageBus()
    await bus.start()
    config_svc = ConfigService(get_session_factory, bus)
    state_reg = StateRegistry()

    app = create_app(cfg, config_svc, state_reg, bus, engine)
    yield app
    await bus.stop()
    await engine.dispose()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def seeded_db(app):
    from db.session import get_session_factory
    factory = get_session_factory()
    async with factory() as session:
        user = await _seed_user(session)
        yield user


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestLogin:
    async def test_login_success(self, client, seeded_db):
        r = await client.post("/api/v1/auth/login",
                               json={"username": "testadmin", "password": "Admin1234"})
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client, seeded_db):
        r = await client.post("/api/v1/auth/login",
                               json={"username": "testadmin", "password": "WrongPass1"})
        assert r.status_code == 401

    async def test_login_unknown_user(self, client, seeded_db):
        r = await client.post("/api/v1/auth/login",
                               json={"username": "nobody", "password": "Admin1234"})
        assert r.status_code == 401


class TestMe:
    async def test_me_returns_user(self, client, seeded_db):
        login = await client.post("/api/v1/auth/login",
                                   json={"username": "testadmin", "password": "Admin1234"})
        token = login.json()["access_token"]
        r = await client.get("/api/v1/auth/me",
                              headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["username"] == "testadmin"

    async def test_me_unauthenticated(self, client):
        r = await client.get("/api/v1/auth/me")
        assert r.status_code == 401


class TestLogout:
    async def test_logout_then_me_fails(self, client, seeded_db):
        login = await client.post("/api/v1/auth/login",
                                   json={"username": "testadmin", "password": "Admin1234"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = await client.post("/api/v1/auth/logout", headers=headers)
        assert r.status_code == 204

        r2 = await client.get("/api/v1/auth/me", headers=headers)
        assert r2.status_code == 401
