"""Discord Webhook notification channel."""

from __future__ import annotations

import logging

import httpx

from alerts.notifications.base import AlertPayload, NotificationChannel, SendResult

logger = logging.getLogger(__name__)

_COLOR = {"critical": 0x9B59B6, "high": 0xE74C3C, "medium": 0xF39C12, "low": 0x2ECC71}


class DiscordWebhookChannel(NotificationChannel):
    channel_name = "discord"

    def __init__(self, webhook_url: str) -> None:
        self._url = webhook_url

    async def send(self, payload: AlertPayload) -> SendResult:
        embed = {
            "title": f"[{payload.severity.upper()}] {payload.rule_name}",
            "color": _COLOR.get(payload.severity, 0x95A5A6),
            "fields": [
                {"name": "Camera", "value": payload.camera_name, "inline": True},
                {"name": "Behavior", "value": payload.behavior, "inline": True},
                {"name": "Confidence", "value": f"{payload.confidence:.0%}", "inline": True},
                {"name": "Time", "value": payload.occurred_at, "inline": False},
            ],
        }
        if payload.snapshot_url:
            embed["image"] = {"url": payload.snapshot_url}

        body = {"embeds": [embed]}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self._url, json=body)
                resp.raise_for_status()
            return self._result(True)
        except Exception as e:
            logger.error("Discord send failed: %s", e)
            return self._result(False, str(e))
