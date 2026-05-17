"""Event / Alert Pydantic v2 schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EventRead(BaseModel):
    id: int
    camera_id: int | None
    rule_id: int | None
    behavior: str
    severity: str
    confidence: float
    track_id: int | None
    snapshot_url: str | None   # API builds URL from snapshot_path
    clip_url: str | None
    occurred_at: datetime
    status: str
    acknowledged_at: datetime | None
    acknowledged_by: str | None

    model_config = {"from_attributes": True}


class EventFilter(BaseModel):
    camera_id: int | None = None
    behavior: str | None = None
    severity: str | None = None
    status: str | None = None
    from_dt: datetime | None = None
    to_dt: datetime | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=200)


class EventPage(BaseModel):
    items: list[EventRead]
    total: int
    page: int
    page_size: int


class AlertAckRequest(BaseModel):
    note: str | None = None


class AlertSilenceRequest(BaseModel):
    duration_seconds: int = Field(300, ge=60, le=86400)


class AlertEscalateRequest(BaseModel):
    reason: str = Field(..., min_length=1)


class AlertNoteCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=4096)


class EventPurgeRequest(BaseModel):
    """Filter for bulk event purge.  All fields optional (omit = no restriction)."""
    before_dt: datetime | None = None
    camera_id: int | None = None
    statuses: list[str] | None = None    # e.g. ["ACKNOWLEDGED","SILENCED"]
    dry_run: bool = False                 # True → count only, no deletion


class EventPurgeResponse(BaseModel):
    deleted: int
    dry_run: bool
