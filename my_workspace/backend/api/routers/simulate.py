"""Simulate router — inject fake detections for testing Rule+Alert pipeline (dev only)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from api.deps import require
from protocol.mtp import MTPMessage, MTPMsgType, MTPPriority

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simulate", tags=["simulate"])


class SimulateDetectionRequest(BaseModel):
    camera_id: int = Field(..., description="Camera ID to simulate detection on")
    zone_id: int = Field(..., description="Zone ID the detection occurs in")
    behavior: str = Field("intrusion", description="Behavior type: intrusion | loitering | line_crossing")
    confidence: float = Field(0.85, ge=0.0, le=1.0, description="Detection confidence")
    track_id: int = Field(1, description="Track ID of the simulated object")


@router.post(
    "/detection",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[require("cameras:read")],
    summary="Simulate a detection event (dev/test only)",
    description="Publishes a fake TRACK_UPDATE message that triggers rule evaluation → alert pipeline.",
)
async def simulate_detection(body: SimulateDetectionRequest, request: Request) -> dict:
    """
    Injects a fake detection into the message bus.
    RuleEngine will evaluate active rules for the given camera/zone.
    If a matching rule exists, RULE_TRIGGERED → AlertManager → ALERT_FIRED.
    """
    bus = request.app.state.bus

    # Build a fake detection payload matching what AI pipeline would produce
    payload = {
        "camera_id": body.camera_id,
        "detections": [
            {
                "track_id": body.track_id,
                "label": "person",
                "confidence": body.confidence,
                "zone_id": body.zone_id,
                "bbox": {
                    "x1": 0.3,
                    "y1": 0.3,
                    "x2": 0.6,
                    "y2": 0.9,
                },
            }
        ],
    }

    msg = MTPMessage(
        msg_type=MTPMsgType.TRACK_UPDATE,
        payload=payload,
        priority=MTPPriority.NORMAL,
        source="simulate",
    )
    await bus.publish(msg)

    logger.info(
        "Simulate detection — camera=%d zone=%d behavior=%s confidence=%.2f",
        body.camera_id, body.zone_id, body.behavior, body.confidence,
    )
    return {
        "status": "published",
        "message": "TRACK_UPDATE published — check RuleEngine log for rule evaluation",
        "camera_id": body.camera_id,
        "zone_id": body.zone_id,
        "behavior": body.behavior,
    }
