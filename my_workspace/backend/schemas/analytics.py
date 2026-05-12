"""Analytics response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EventSummary(BaseModel):
    total_events: int
    by_severity: dict[str, int]
    by_behavior: dict[str, int]
    by_camera: dict[str, int]
    period_start: datetime
    period_end: datetime


class HourlyStats(BaseModel):
    hour: int    # 0–23
    count: int


class HealthBeat(BaseModel):
    cpu_percent: float
    ram_mb: float
    disk_free_gb: float
    active_cameras: int
    queue_size: int
    uptime_seconds: float
    boot_state: str
    camera_states: dict[str, str]   # camera_id → state string
