"""WebSocket connection hub — broadcasts bus events to connected clients."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field

from fastapi import WebSocket

from protocol.mtp import MTPMessage, MTPMsgType

logger = logging.getLogger(__name__)


@dataclass
class _Client:
    ws: WebSocket
    camera_ids: set[int] = field(default_factory=set)  # empty = subscribed to all


class WebSocketHub:
    """
    Manages all connected WebSocket clients.

    Clients send a subscribe message to filter by camera:
        {"type": "subscribe", "camera_ids": [1, 2, 3]}

    Hub pushes two event types:
        {"type": "alert_fired", "data": {...}}
        {"type": "frame_ready", "camera_id": N, "data": {...}}
    """

    def __init__(self) -> None:
        self._clients: list[_Client] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> _Client:
        await ws.accept()
        client = _Client(ws=ws)
        async with self._lock:
            self._clients.append(client)
        logger.info("WS client connected (total=%d)", len(self._clients))
        return client

    async def disconnect(self, client: _Client) -> None:
        async with self._lock:
            self._clients = [c for c in self._clients if c is not client]
        logger.info("WS client disconnected (total=%d)", len(self._clients))

    async def handle_message(self, client: _Client, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return
        if msg.get("type") == "subscribe":
            ids = msg.get("camera_ids", [])
            client.camera_ids = set(ids)

    async def broadcast_alert(self, payload: dict) -> None:
        envelope = json.dumps({"type": "alert_fired", "data": payload})
        await self._broadcast_all(envelope)

    async def broadcast_frame(self, camera_id: int, payload: dict) -> None:
        envelope = json.dumps({"type": "frame_ready", "camera_id": camera_id, "data": payload})
        await self._broadcast_filtered(camera_id, envelope)

    async def _broadcast_all(self, text: str) -> None:
        async with self._lock:
            clients = list(self._clients)
        await asyncio.gather(*[self._safe_send(c, text) for c in clients], return_exceptions=True)

    async def _broadcast_filtered(self, camera_id: int, text: str) -> None:
        async with self._lock:
            clients = [c for c in self._clients
                       if not c.camera_ids or camera_id in c.camera_ids]
        await asyncio.gather(*[self._safe_send(c, text) for c in clients], return_exceptions=True)

    async def _safe_send(self, client: _Client, text: str) -> None:
        try:
            await client.ws.send_text(text)
        except Exception:
            await self.disconnect(client)

    def register(self, bus) -> None:
        """Subscribe to bus events — called at startup."""
        bus.subscribe(MTPMsgType.ALERT_FIRED, self._on_alert_fired)
        bus.subscribe(MTPMsgType.FRAME_READY, self._on_frame_ready)

    async def _on_alert_fired(self, msg: MTPMessage) -> None:
        await self.broadcast_alert(msg.payload)

    async def _on_frame_ready(self, msg: MTPMessage) -> None:
        camera_id = msg.payload.get("camera_id", 0)
        await self.broadcast_frame(camera_id, msg.payload)

    @property
    def client_count(self) -> int:
        return len(self._clients)
