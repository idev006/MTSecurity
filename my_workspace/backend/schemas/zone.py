"""Zone and Rule Pydantic v2 schemas."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Literal, Union, List, Any, Annotated

from pydantic import BaseModel, Field, field_validator


class ZoneCreate(BaseModel):
    camera_id: int
    name: str = Field(..., min_length=1, max_length=128)
    coordinates: list[list[float]] = Field(..., min_length=3, max_length=50)
    color: str = Field("#FF6B6B", pattern=r"^#[0-9a-fA-F]{6}$")

    @field_validator("coordinates")
    @classmethod
    def validate_coords(cls, v: list[list[float]]) -> list[list[float]]:
        for point in v:
            if len(point) != 2:
                raise ValueError("Each coordinate must be [x, y]")
            if not (0.0 <= point[0] <= 1.0 and 0.0 <= point[1] <= 1.0):
                raise ValueError("Coordinates must be normalised 0.0–1.0")
        return v


class ZoneUpdate(BaseModel):
    name: str | None = None
    coordinates: list[list[float]] | None = None
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    is_active: bool | None = None


class ZoneRead(BaseModel):
    id: int
    camera_id: int
    name: str
    coordinates: list[list[float]]
    color: str
    is_active: bool
    created_at: datetime

    @field_validator("coordinates", mode="before")
    @classmethod
    def parse_coords(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    model_config = {"from_attributes": True}




class LogicLeaf(BaseModel):
    type: Literal["time", "space", "object", "behavior"]
    params: dict[str, Any] = Field(default_factory=dict)

class LogicNode(BaseModel):
    operator: Literal["AND", "OR", "NOT"]
    conditions: List[Union[LogicNode, LogicLeaf]]

class RuleCreate(BaseModel):
    zone_id: int
    name: str = Field(..., min_length=1, max_length=128)
    behavior: str = Field(..., pattern=r"^(intrusion|loitering|line_crossing|crowd_density|abandoned_object)$")
    confidence_threshold: float = Field(0.6, ge=0.1, le=1.0)
    dwell_threshold_seconds: int = Field(30, ge=1, le=3600)
    cooldown_seconds: int = Field(60, ge=10, le=3600)
    severity: str = Field("medium", pattern=r"^(low|medium|high|critical)$")
    schedule: dict | None = None
    logic: LogicNode | LogicLeaf | None = None


class RuleUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    confidence_threshold: float | None = Field(None, ge=0.1, le=1.0)
    dwell_threshold_seconds: int | None = Field(None, ge=1, le=3600)
    cooldown_seconds: int | None = Field(None, ge=10, le=3600)
    severity: str | None = Field(None, pattern=r"^(low|medium|high|critical)$")
    schedule: dict | None = None
    logic: LogicNode | LogicLeaf | None = None


class RuleRead(BaseModel):
    id: int
    zone_id: int
    name: str
    behavior: str
    is_active: bool
    confidence_threshold: float
    dwell_threshold_seconds: int
    cooldown_seconds: int
    severity: str
    schedule: dict | None = None
    logic: LogicNode | LogicLeaf | None = None
    created_at: datetime

    @field_validator("schedule", "logic", mode="before")
    @classmethod
    def parse_json_fields(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v

    model_config = {"from_attributes": True}
