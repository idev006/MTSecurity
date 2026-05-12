"""Slack Incoming Webhook notification channel."""

from __future__ import annotations

import logging

import httpx

from alerts.notifications.base import AlertPayload, NotificationChannel, SendResult

logger = logging.getLogger(__name__)

_EMOJI = {"critical": ":red_circle:", "high": ":large_orange_circle:",
          "medium": ":large_yellow_circle:", "low": ":large_green_circle:"}


class SlackWebhookChannel(NotificationChannel):
    channel_name = "slack"

    def __init__(self, webhook_url: str) -> None:
        self._url = webhook_url

    async def send(self, payload: AlertPayload) -> SendResult:
        emoji = _EMOJI.get(payload.severity, ":white_circle:")
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{emoji} {payload.rule_name}"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Camera:*\n{payload.camera_name}"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n{payload.severity.upper()}"},
                    {"type": "mrkdwn", "text": f"*Behavior:*\n{payload.behavior}"},
                    {"type": "mrkdwn", "text": f"*Confidence:*\n{payload.confidence:.0%}"},
                    {"type": "mrkdwn", "text": f"*Time:*\n{payload.occurred_at}"},
                ],
            },
        ]
        if payload.snapshot_url:
            blocks.append({"type": "image", "image_url": payload.snapshot_url,
                           "alt_text": "snapshot"})

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self._url, json={"blocks": blocks})
                resp.raise_for_status()
            return self._result(True)
        except Exception as e:
            logger.error("Slack send failed: %s", e)
            return self._result(False, str(e))
