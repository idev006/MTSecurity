"""Phase 1 Gate — Unit tests for protocol layer (MTP + MessageBus)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from protocol.message_bus import MessageBus
from protocol.mtp import MTPMessage, MTPMsgType, MTPPriority


# ── MTPMessage ────────────────────────────────────────────────────────────────

def test_mtp_message_defaults():
    msg = MTPMessage(msg_type=MTPMsgType.HEALTH_BEAT, payload={"cpu": 10.0})
    assert msg.priority == MTPPriority.NORMAL
    assert msg.message_id != msg.correlation_id   # both unique UUIDs
    assert msg.source == "unknown"


def test_mtp_message_is_frozen():
    msg = MTPMessage(msg_type=MTPMsgType.HEALTH_BEAT, payload={})
    with pytest.raises(Exception):
        msg.source = "hacked"  # type: ignore[misc]


def test_mtp_message_not_expired():
    msg = MTPMessage(msg_type=MTPMsgType.HEALTH_BEAT, payload={}, ttl_seconds=30)
    assert msg.is_expired() is False


def test_mtp_message_expired():
    past = datetime.now(timezone.utc) - timedelta(seconds=60)
    msg = MTPMessage(
        msg_type=MTPMsgType.HEALTH_BEAT, payload={}, ttl_seconds=30, timestamp=past
    )
    assert msg.is_expired() is True


def test_mtp_priority_ordering():
    critical = MTPMessage(msg_type="X", payload={}, priority=MTPPriority.CRITICAL)
    low = MTPMessage(msg_type="X", payload={}, priority=MTPPriority.LOW)
    assert critical < low   # lower int = higher priority


# ── MessageBus ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bus_starts_and_stops():
    bus = MessageBus()
    await bus.start()
    assert bus._running is True
    await bus.stop()
    assert bus._running is False


@pytest.mark.asyncio
async def test_bus_subscribe_and_dispatch(bus: MessageBus):
    received: list[MTPMessage] = []

    async def handler(msg: MTPMessage) -> None:
        received.append(msg)

    bus.subscribe(MTPMsgType.HEALTH_BEAT, handler)
    msg = MTPMessage(msg_type=MTPMsgType.HEALTH_BEAT, payload={"cpu": 5.0})
    await bus.publish(msg)
    await asyncio.sleep(0.1)

    assert len(received) == 1
    assert received[0].payload["cpu"] == 5.0


@pytest.mark.asyncio
async def test_bus_priority_order(bus: MessageBus):
    """HIGH priority message dispatched before LOW from same flush."""
    order: list[str] = []

    async def handler(msg: MTPMessage) -> None:
        order.append(msg.priority.name)

    bus.subscribe(MTPMsgType.ALERT_FIRED, handler)
    bus.subscribe(MTPMsgType.HEALTH_BEAT, handler)

    low_msg = MTPMessage(msg_type=MTPMsgType.HEALTH_BEAT, payload={}, priority=MTPPriority.LOW)
    high_msg = MTPMessage(msg_type=MTPMsgType.ALERT_FIRED, payload={}, priority=MTPPriority.HIGH)

    await bus.publish(low_msg)
    await bus.publish(high_msg)
    await asyncio.sleep(0.15)

    assert order[0] == "HIGH"
    assert order[1] == "LOW"


@pytest.mark.asyncio
async def test_bus_drops_expired_message(bus: MessageBus):
    received: list[MTPMessage] = []

    async def handler(msg: MTPMessage) -> None:
        received.append(msg)

    past = datetime.now(timezone.utc) - timedelta(seconds=60)
    bus.subscribe(MTPMsgType.HEALTH_BEAT, handler)
    expired = MTPMessage(
        msg_type=MTPMsgType.HEALTH_BEAT, payload={}, ttl_seconds=10, timestamp=past
    )
    await bus.publish(expired)
    await asyncio.sleep(0.1)

    assert len(received) == 0   # silently dropped


@pytest.mark.asyncio
async def test_bus_handler_exception_does_not_crash(bus: MessageBus):
    async def bad_handler(msg: MTPMessage) -> None:
        raise RuntimeError("intentional test error")

    bus.subscribe(MTPMsgType.HEALTH_BEAT, bad_handler)
    msg = MTPMessage(msg_type=MTPMsgType.HEALTH_BEAT, payload={})
    await bus.publish(msg)
    await asyncio.sleep(0.1)

    # Bus is still running after handler exception
    assert bus._running is True


@pytest.mark.asyncio
async def test_bus_unsubscribe(bus: MessageBus):
    received: list[MTPMessage] = []

    async def handler(msg: MTPMessage) -> None:
        received.append(msg)

    bus.subscribe(MTPMsgType.HEALTH_BEAT, handler)
    bus.unsubscribe(MTPMsgType.HEALTH_BEAT, handler)

    await bus.publish(MTPMessage(msg_type=MTPMsgType.HEALTH_BEAT, payload={}))
    await asyncio.sleep(0.1)

    assert len(received) == 0


@pytest.mark.asyncio
async def test_bus_multiple_handlers(bus: MessageBus):
    counts = [0, 0]

    async def h1(msg): counts[0] += 1
    async def h2(msg): counts[1] += 1

    bus.subscribe(MTPMsgType.CAMERA_STATUS, h1)
    bus.subscribe(MTPMsgType.CAMERA_STATUS, h2)
    await bus.publish(MTPMessage(msg_type=MTPMsgType.CAMERA_STATUS, payload={}))
    await asyncio.sleep(0.1)

    assert counts == [1, 1]
