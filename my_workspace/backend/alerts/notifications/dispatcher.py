"""Dispatcher — sends to multiple channels concurrently."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from alerts.notifications.base import AlertPayload, NotificationChannel, SendResult

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """
    Dispatches to all registered channels concurrently (asyncio.gather).
    Individual channel failures are logged but do NOT stop other channels.
    """

    def __init__(self) -> None:
        self._channels: list[NotificationChannel] = []

    def add_channel(self, channel: NotificationChannel) -> None:
        self._channels.append(channel)
        logger.info("Registered notification channel: %s", channel.channel_name)

    def remove_channel(self, name: str) -> None:
        self._channels = [c for c in self._channels if c.channel_name != name]

    async def dispatch(self, payload: AlertPayload) -> list[SendResult]:
        if not self._channels:
            return []

        results = await asyncio.gather(
            *[ch.send(payload) for ch in self._channels],
            return_exceptions=True,
        )

        send_results: list[SendResult] = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                name = self._channels[i].channel_name
                logger.error("Channel %s raised exception: %s", name, r)
                send_results.append(SendResult(channel=name, success=False, error=str(r)))
            else:
                send_results.append(r)

        ok = sum(1 for r in send_results if r.success)
        logger.info(
            "Notification dispatched — %d/%d channels succeeded", ok, len(send_results)
        )
        return send_results

    @property
    def channel_count(self) -> int:
        return len(self._channels)
