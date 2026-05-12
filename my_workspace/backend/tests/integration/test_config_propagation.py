"""Phase 1 Gate — Integration: config change propagates through MessageBus."""

from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from models import Base
from models.camera import Camera
from models.zone import Zone
from protocol.message_bus import MessageBus
from protocol.mtp import MTPMessage, MTPMsgType
from ssot.config_service import ConfigService


@pytest_asyncio.fixture
async def setup():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Seed a camera and zone
    async with factory() as session:
        cam = Camera(
            name="TestCam",
            rtsp_url_encrypted="encrypted_rtsp",
            resolution_width=1920,
            resolution_height=1080,
        )
        session.add(cam)
        await session.flush()
        zone = Zone(
            camera_id=cam.id,
            name="Zone A",
            coordinates="[[0.1,0.1],[0.9,0.1],[0.9,0.9],[0.1,0.9]]",
        )
        session.add(zone)
        await session.commit()
        cam_id = cam.id
        zone_id = zone.id

    bus = MessageBus()
    await bus.start()

    config_svc = ConfigService(lambda: factory, bus)
    await config_svc.initialize()

    yield config_svc, bus, cam_id, zone_id

    await bus.stop()
    await engine.dispose()


@pytest.mark.asyncio
async def test_camera_update_publishes_config_changed(setup):
    config_svc, bus, cam_id, _ = setup
    received: list[MTPMessage] = []

    async def capture(msg: MTPMessage) -> None:
        received.append(msg)

    bus.subscribe(MTPMsgType.CONFIG_CHANGED, capture)

    await config_svc.update_camera(cam_id, {"name": "Updated Cam"}, actor="admin")
    await asyncio.sleep(0.1)

    assert len(received) == 1
    assert received[0].payload["scope"] == "camera"
    assert received[0].payload["entity_id"] == cam_id
    assert received[0].payload["changed_by"] == "admin"


@pytest.mark.asyncio
async def test_zone_update_publishes_config_changed(setup):
    config_svc, bus, _, zone_id = setup
    received: list[MTPMessage] = []

    async def capture(msg: MTPMessage) -> None:
        received.append(msg)

    bus.subscribe(MTPMsgType.CONFIG_CHANGED, capture)

    await config_svc.update_zone(zone_id, {"name": "Zone Updated"}, actor="superadmin")
    await asyncio.sleep(0.1)

    assert len(received) == 1
    assert received[0].payload["scope"] == "zone"
    assert received[0].payload["entity_id"] == zone_id


@pytest.mark.asyncio
async def test_cache_is_populated_after_initialize(setup):
    config_svc, _, cam_id, zone_id = setup

    cam = await config_svc.get_camera(cam_id)
    assert cam is not None
    assert cam.name == "TestCam"

    zone = await config_svc.get_zone(zone_id)
    assert zone is not None
    assert zone.name == "Zone A"


@pytest.mark.asyncio
async def test_cache_invalidated_after_update(setup):
    config_svc, bus, cam_id, _ = setup

    # Populate cache
    cam_before = await config_svc.get_camera(cam_id)
    assert cam_before.name == "TestCam"

    # Update name
    await config_svc.update_camera(cam_id, {"name": "New Name"}, actor="admin")
    await asyncio.sleep(0.05)

    cam_after = await config_svc.get_camera(cam_id)
    assert cam_after.name == "New Name"
