"""LINE Messaging API notification channel."""

from __future__ import annotations

import logging

import httpx

from alerts.notifications.base import AlertPayload, NotificationChannel, SendResult

logger = logging.getLogger(__name__)

_LINE_API = "https://api.line.me/v2/bot/message/broadcast"


class LineMessagingChannel(NotificationChannel):
    channel_name = "line"

    def __init__(self, access_token: str) -> None:
        self._token = access_token

    async def send(self, payload: AlertPayload) -> SendResult:
        severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
            payload.severity, "⚪"
        )
        text = (
            f"{severity_emoji} [{payload.severity.upper()}] {payload.rule_name}\n"
            f"📷 Camera: {payload.camera_name}\n"
            f"🎯 Event: {payload.behavior} ({payload.confidence:.0%})\n"
            f"🕐 {payload.occurred_at}"
        )
        body = {"messages": [{"type": "text", "text": text}]}
        if payload.snapshot_url:
            body["messages"].append({
                "type": "image",
                "originalContentUrl": payload.snapshot_url,
                "previewImageUrl": payload.snapshot_url,
            })
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    _LINE_API,
                    json=body,
                    headers={"Authorization": f"Bearer {self._token}"},
                )
                resp.raise_for_status()
            return self._result(True)
        except Exception as e:
            logger.error("LINE send failed: %s", e)
            return self._result(False, str(e))
