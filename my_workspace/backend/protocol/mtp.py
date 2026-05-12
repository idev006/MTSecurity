"""MTP — MTSecurity Transport Protocol: envelope for all in-process messages."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import IntEnum, auto
from typing import Any

from pydantic import BaseModel, Field


class MTPPriority(IntEnum):
    CRITICAL = 1   # system shutdown, fatal error
    HIGH = 2       # alert fired, security event
    NORMAL = 3     # detection results, config changes
    LOW = 4        # health beats, analytics


class MTPMsgType(str):
    """String-based message type constants — extensible without enum fragility."""

    # Ingestion → AI
    FRAME_READY = "FRAME_READY"

    # AI → Rules
    TRACK_UPDATE = "TRACK_UPDATE"
    DETECTION_RESULT = "DETECTION_RESULT"

    # Rules → Alerts
    RULE_TRIGGERED = "RULE_TRIGGERED"

    # Alerts → API/WebSocket
    ALERT_FIRED = "ALERT_FIRED"
    ALERT_ACKNOWLEDGED = "ALERT_ACKNOWLEDGED"
    ALERT_SILENCED = "ALERT_SILENCED"
    ALERT_ESCALATED = "ALERT_ESCALATED"

    # SSOT → All
    CONFIG_CHANGED = "CONFIG_CHANGED"
    STATE_CHANGED = "STATE_CHANGED"

    # Camera lifecycle
    CAMERA_STATUS = "CAMERA_STATUS"
    CAMERA_RECONNECT = "CAMERA_RECONNECT"

    # System
    HEALTH_BEAT = "HEALTH_BEAT"
    SYSTEM_SHUTDOWN = "SYSTEM_SHUTDOWN"
    SYSTEM_ERROR = "SYSTEM_ERROR"

    # LPR
    LPR_DETECTED = "LPR_DETECTED"


class MTPMessage(BaseModel):
    """Immutable envelope for every message on the internal bus."""

    msg_type: str
    payload: dict[str, Any]
    priority: MTPPriority = MTPPriority.NORMAL
    source: str = "unknown"
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: float = 30.0

    model_config = {"frozen": True}

    def is_expired(self) -> bool:
        age = (datetime.now(timezone.utc) - self.timestamp).total_seconds()
        return age > self.ttl_seconds

    def __lt__(self, other: "MTPMessage") -> bool:
        """Enable priority queue ordering (lower int = higher priority)."""
        return self.priority < other.priority
