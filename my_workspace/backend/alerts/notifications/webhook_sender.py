"""Generic HTTP POST webhook channel."""

from __future__ import annotations

import logging

import httpx

from alerts.notifications.base import AlertPayload, NotificationChannel, SendResult

logger = logging.getLogger(__name__)


class WebhookChannel(NotificationChannel):
    channel_name = "webhook"

    def __init__(self, url: str, secret: str | None = None) -> None:
        self._url = url
        self._secret = secret

    async def send(self, payload: AlertPayload) -> SendResult:
        headers = {"Content-Type": "application/json"}
        if self._secret:
            headers["X-MTSecurity-Secret"] = self._secret

        body = {
            "event_id": payload.event_id,
            "rule_name": payload.rule_name,
            "camera_id": payload.camera_id,
            "camera_name": payload.camera_name,
            "behavior": payload.behavior,
            "severity": payload.severity,
            "confidence": payload.confidence,
            "snapshot_url": payload.snapshot_url,
            "occurred_at": payload.occurred_at,
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self._url, json=body, headers=headers)
                resp.raise_for_status()
            return self._result(True)
        except Exception as e:
            logger.error("Webhook send failed: %s", e)
            return self._result(False, str(e))
