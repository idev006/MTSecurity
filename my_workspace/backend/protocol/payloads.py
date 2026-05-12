"""Typed payload schemas for each MTPMsgType — validated before publish."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class _Payload(BaseModel):
    model_config = {"frozen": True}


# ── Ingestion ────────────────────────────────────────────────────────────────

class FrameReadyPayload(_Payload):
    camera_id: int
    frame_bytes: bytes          # JPEG-encoded frame
    width: int
    height: int
    captured_at: datetime


# ── AI ──────────────────────────────────────────────────────────────────────

class BoundingBox(_Payload):
    x1: float   # normalised 0.0–1.0
    y1: float
    x2: float
    y2: float

    @property
    def centroid(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)


class Detection(_Payload):
    label: str
    confidence: float
    bbox: BoundingBox
    track_id: int | None = None


class TrackUpdatePayload(_Payload):
    camera_id: int
    detections: list[Detection]
    frame_timestamp: datetime


class DetectionResultPayload(_Payload):
    camera_id: int
    detections: list[Detection]
    inference_ms: float


class LPRDetectedPayload(_Payload):
    camera_id: int
    plate_text: str
    confidence: float
    bbox: BoundingBox
    is_whitelisted: bool


# ── Rules ────────────────────────────────────────────────────────────────────

class RuleTriggeredPayload(_Payload):
    rule_id: int
    rule_name: str
    camera_id: int
    zone_id: int | None
    track_id: int | None
    behavior: str               # "intrusion", "loitering", etc.
    confidence: float
    snapshot_path: str | None
    metadata: dict[str, Any] = {}


# ── Alerts ───────────────────────────────────────────────────────────────────

class AlertFiredPayload(_Payload):
    alert_id: int
    rule_name: str
    camera_id: int
    behavior: str
    severity: str               # "low", "medium", "high", "critical"
    snapshot_url: str | None
    clip_url: str | None
    channels_notified: list[str]


class AlertAcknowledgedPayload(_Payload):
    alert_id: int
    acknowledged_by: str        # actor username
    note: str | None = None


class AlertSilencedPayload(_Payload):
    alert_id: int
    silenced_by: str
    duration_seconds: int


class AlertEscalatedPayload(_Payload):
    alert_id: int
    escalated_by: str
    reason: str


# ── SSOT ─────────────────────────────────────────────────────────────────────

class ConfigChangedPayload(_Payload):
    scope: str                  # "camera", "zone", "rule", "global"
    entity_id: int | None
    changed_by: str
    changes: dict[str, Any]


class StateChangedPayload(_Payload):
    entity_type: str            # "camera", "alert"
    entity_id: int
    old_state: str
    new_state: str


# ── Camera ───────────────────────────────────────────────────────────────────

class CameraStatusPayload(_Payload):
    camera_id: int
    status: str                 # "online", "offline", "reconnecting", "error"
    fps: float | None = None
    latency_ms: float | None = None
    error_msg: str | None = None


class CameraReconnectPayload(_Payload):
    camera_id: int
    attempt: int
    backoff_seconds: float


# ── System ───────────────────────────────────────────────────────────────────

class HealthBeatPayload(_Payload):
    cpu_percent: float
    ram_mb: float
    disk_free_gb: float
    active_cameras: int
    queue_size: int
    uptime_seconds: float


class SystemShutdownPayload(_Payload):
    reason: str
    graceful: bool = True


class SystemErrorPayload(_Payload):
    component: str
    error: str
    fatal: bool = False
