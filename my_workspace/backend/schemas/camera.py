"""Camera Pydantic v2 schemas."""

from __future__ import annotations

import re
import sys
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

_RTSP_RE = re.compile(r"^rtsp://[^\s]+$")


class CameraCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    source_type: Literal["rtsp", "webcam"] = "rtsp"

    # RTSP fields (required when source_type == "rtsp")
    rtsp_url: str | None = Field(None, description="Plain RTSP URL — encrypted before storage")

    # Webcam fields (required when source_type == "webcam")
    device_index: int | None = Field(None, ge=0, le=9, description="Local webcam index 0-9")

    location: str | None = None
    resolution_width: int = Field(1920, ge=320, le=3840)
    resolution_height: int = Field(1080, ge=240, le=2160)
    fps: float = Field(15.0, ge=1.0, le=60.0)

    @model_validator(mode="after")
    def validate_source(self) -> "CameraCreate":
        if self.source_type == "rtsp":
            if not self.rtsp_url:
                raise ValueError("rtsp_url is required for source_type='rtsp'")
            if not _RTSP_RE.match(self.rtsp_url):
                raise ValueError("rtsp_url must be a valid rtsp:// URL")
        elif self.source_type == "webcam":
            if self.device_index is None:
                raise ValueError("device_index (0-9) is required for source_type='webcam'")
        return self


class CameraUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    location: str | None = None
    is_active: bool | None = None
    fps: float | None = Field(None, ge=1.0, le=60.0)


class CameraRead(BaseModel):
    id: int
    name: str
    source_type: str
    device_index: int | None
    location: str | None
    is_active: bool
    resolution_width: int
    resolution_height: int
    fps: float
    created_at: datetime
    updated_at: datetime
    # RTSP URL is never returned in API responses

    model_config = {"from_attributes": True}


class CameraStatus(BaseModel):
    camera_id: int
    state: str
    fps: float
    latency_ms: float
    last_frame_at: datetime | None
    error_msg: str | None


class WebcamDevice(BaseModel):
    """Available local webcam detected by probing device indices."""
    index: int
    label: str
