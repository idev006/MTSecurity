"""NotificationChannel ABC — all channels implement this interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AlertPayload:
    event_id: int
    rule_name: str
    camera_id: int
    camera_name: str
    behavior: str
    severity: str
    confidence: float
    snapshot_url: str | None
    clip_url: str | None
    occurred_at: str   # ISO 8601 string


@dataclass
class SendResult:
    channel: str
    success: bool
    error: str | None = None


class NotificationChannel(ABC):
    @property
    @abstractmethod
    def channel_name(self) -> str: ...

    @abstractmethod
    async def send(self, payload: AlertPayload) -> SendResult: ...

    def _result(self, success: bool, error: str | None = None) -> SendResult:
        return SendResult(channel=self.channel_name, success=success, error=error)
