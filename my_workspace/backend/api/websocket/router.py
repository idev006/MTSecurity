"""WebSocket endpoint — /api/v1/ws"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from api.websocket.hub import WebSocketHub
from auth.jwt_handler import decode_token

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def ws_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
) -> None:
    cfg = websocket.app.state.cfg
    try:
        payload = decode_token(
            token,
            cfg.jwt_secret_key.get_secret_value(),
            cfg.jwt_algorithm,
        )
        if payload.get("type") != "access":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    hub: WebSocketHub = websocket.app.state.ws_hub
    client = await hub.connect(websocket)
    logger.info("WS authenticated: user=%s", payload.get("sub"))

    try:
        while True:
            raw = await websocket.receive_text()
            await hub.handle_message(client, raw)
    except WebSocketDisconnect:
        await hub.disconnect(client)
