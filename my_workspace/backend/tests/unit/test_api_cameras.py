"""Unit tests for cameras router."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from auth.password import hash_password
from models.user import User


async def _seed_admin(db: AsyncSession) -> User:
    user = User(username="admin", hashed_password=hash_password("Admin1234"), role="ADMIN")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def app():
    from api.app import create_test_app
    from config import Settings
    from db.session import get_session_factory, init_engine
    from models.base import Base
    from protocol.message_bus import MessageBus
    from ssot.config_service import ConfigService
    from ssot.state_registry import StateRegistry

    cfg = Settings(
        jwt_secret_key="test-secret-key-at-least-32-characters-long",
        encryption_key="ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=",
        debug=True,
    )
    engine = init_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    bus = MessageBus()
    await bus.start()
    config_svc = ConfigService(get_session_factory, bus)
    state_reg = StateRegistry()
    app = create_test_app(cfg=cfg, config_svc=config_svc, state_reg=state_reg, bus=bus)

    factory = get_session_factory()
    async with factory() as session:
        await _seed_admin(session)

    yield app
    await bus.stop()
    await engine.dispose()


@pytest.fixture
async def auth_client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/auth/login",
                          json={"username": "admin", "password": "Admin1234"})
        token = r.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestCamerasCRUD:
    _RTSP = "rtsp://user:pass@192.168.1.100/stream"

    async def test_list_empty(self, auth_client):
        r = await auth_client.get("/api/v1/cameras")
        assert r.status_code == 200
        assert r.json() == []

    async def test_create_camera(self, auth_client):
        r = await auth_client.post("/api/v1/cameras", json={
            "name": "Front Gate",
            "rtsp_url": self._RTSP,
            "location": "Gate",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Front Gate"
        assert "rtsp_url" not in data   # never returned

    async def test_get_camera(self, auth_client):
        created = (await auth_client.post("/api/v1/cameras", json={
            "name": "Lobby", "rtsp_url": self._RTSP,
        })).json()
        r = await auth_client.get(f"/api/v1/cameras/{created['id']}")
        assert r.status_code == 200
        assert r.json()["name"] == "Lobby"

    async def test_get_camera_not_found(self, auth_client):
        r = await auth_client.get("/api/v1/cameras/9999")
        assert r.status_code == 404

    async def test_update_camera(self, auth_client):
        cam = (await auth_client.post("/api/v1/cameras", json={
            "name": "Old Name", "rtsp_url": self._RTSP,
        })).json()
        r = await auth_client.patch(f"/api/v1/cameras/{cam['id']}",
                                      json={"name": "New Name"})
        assert r.status_code == 200
        assert r.json()["name"] == "New Name"

    async def test_delete_camera_forbidden_for_admin(self, auth_client):
        # cameras:delete is SUPERADMIN only
        cam = (await auth_client.post("/api/v1/cameras", json={
            "name": "ToDelete", "rtsp_url": self._RTSP,
        })).json()
        r = await auth_client.delete(f"/api/v1/cameras/{cam['id']}")
        assert r.status_code == 403

    async def test_camera_status(self, auth_client):
        cam = (await auth_client.post("/api/v1/cameras", json={
            "name": "StatusCam", "rtsp_url": self._RTSP,
        })).json()
        r = await auth_client.get(f"/api/v1/cameras/{cam['id']}/status")
        assert r.status_code == 200
        data = r.json()
        assert "state" in data
        assert data["camera_id"] == cam["id"]

    async def test_unauthenticated(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/cameras")
            assert r.status_code == 401
