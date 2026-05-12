"""Unit tests for WebSocketHub."""

from __future__ import annotations

import asyncio
import json

import pytest

from api.websocket.hub import WebSocketHub


class _FakeWebSocket:
    """Minimal WebSocket stub."""

    def __init__(self):
        self.sent: list[str] = []
        self.accepted = False
        self.closed = False

    async def accept(self):
        self.accepted = True

    async def send_text(self, text: str):
        if self.closed:
            raise RuntimeError("closed")
        self.sent.append(text)

    async def close(self, code=1000):
        self.closed = True


class TestWebSocketHub:
    async def test_connect_accepts_socket(self):
        hub = WebSocketHub()
        ws = _FakeWebSocket()
        client = await hub.connect(ws)
        assert ws.accepted
        assert hub.client_count == 1

    async def test_disconnect_removes_client(self):
        hub = WebSocketHub()
        ws = _FakeWebSocket()
        client = await hub.connect(ws)
        await hub.disconnect(client)
        assert hub.client_count == 0

    async def test_broadcast_alert_reaches_all_clients(self):
        hub = WebSocketHub()
        ws1, ws2 = _FakeWebSocket(), _FakeWebSocket()
        await hub.connect(ws1)
        await hub.connect(ws2)
        await hub.broadcast_alert({"event_id": 1, "rule_name": "test"})
        assert len(ws1.sent) == 1
        assert len(ws2.sent) == 1
        msg = json.loads(ws1.sent[0])
        assert msg["type"] == "alert_fired"
        assert msg["data"]["event_id"] == 1

    async def test_broadcast_frame_filtered_by_camera(self):
        hub = WebSocketHub()
        ws_all = _FakeWebSocket()
        ws_cam1 = _FakeWebSocket()
        c_all = await hub.connect(ws_all)      # subscribed to all
        c_cam1 = await hub.connect(ws_cam1)
        c_cam1.camera_ids = {1}                # only camera 1

        await hub.broadcast_frame(2, {"camera_id": 2})  # cam 2 frame
        assert len(ws_all.sent) == 1    # no filter → receives
        assert len(ws_cam1.sent) == 0   # filtered out

    async def test_broadcast_frame_reaches_subscribed_camera(self):
        hub = WebSocketHub()
        ws = _FakeWebSocket()
        c = await hub.connect(ws)
        c.camera_ids = {5}
        await hub.broadcast_frame(5, {"camera_id": 5})
        assert len(ws.sent) == 1

    async def test_handle_subscribe_message(self):
        hub = WebSocketHub()
        ws = _FakeWebSocket()
        client = await hub.connect(ws)
        await hub.handle_message(client, json.dumps({"type": "subscribe", "camera_ids": [3, 7]}))
        assert client.camera_ids == {3, 7}

    async def test_broken_client_removed_on_send(self):
        hub = WebSocketHub()
        ws = _FakeWebSocket()
        ws.closed = True   # already broken
        await hub.connect(ws)
        assert hub.client_count == 1
        await hub.broadcast_alert({"event_id": 1})
        assert hub.client_count == 0   # auto-removed after failed send
