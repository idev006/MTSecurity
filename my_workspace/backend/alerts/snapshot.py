"""Snapshot — annotate frame with bounding boxes + labels → JPEG."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_FONT = cv2.FONT_HERSHEY_SIMPLEX
_COLORS = {
    "low":      (0, 255, 0),      # green
    "medium":   (0, 165, 255),    # orange
    "high":     (0, 0, 255),      # red
    "critical": (128, 0, 128),    # purple
}


def annotate_frame(
    frame: np.ndarray,
    detections: list[dict],
    rule_name: str = "",
    severity: str = "medium",
    timestamp: datetime | None = None,
) -> np.ndarray:
    """
    Draw bounding boxes, labels, rule name, timestamp on a BGR frame.
    Returns annotated copy (does not mutate original).
    """
    out = frame.copy()
    h, w = out.shape[:2]
    color = _COLORS.get(severity, _COLORS["medium"])

    for det in detections:
        bbox = det.get("bbox", {})
        x1 = int(bbox.get("x1", 0) * w)
        y1 = int(bbox.get("y1", 0) * h)
        x2 = int(bbox.get("x2", 1) * w)
        y2 = int(bbox.get("y2", 1) * h)

        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)

        label = det.get("label", "")
        conf = det.get("confidence", 0.0)
        track_id = det.get("track_id")
        text = f"{label} {conf:.0%}"
        if track_id is not None:
            text += f" #{track_id}"

        (tw, th), _ = cv2.getTextSize(text, _FONT, 0.5, 1)
        cv2.rectangle(out, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
        cv2.putText(out, text, (x1 + 2, y1 - 3), _FONT, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

    # Overlay banner
    ts = (timestamp or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M:%S UTC")
    banner = f"[{severity.upper()}] {rule_name} | {ts}"
    cv2.rectangle(out, (0, 0), (w, 26), (0, 0, 0), -1)
    cv2.putText(out, banner, (6, 18), _FONT, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

    return out


def save_snapshot(
    frame: np.ndarray,
    detections: list[dict],
    rule_name: str,
    severity: str,
    snapshot_dir: Path,
    camera_id: int,
    event_id: int,
) -> Path:
    """Annotate and save JPEG. Returns the saved path."""
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc)
    annotated = annotate_frame(frame, detections, rule_name, severity, ts)
    filename = f"cam{camera_id}_{event_id}_{ts.strftime('%Y%m%d_%H%M%S')}.jpg"
    path = snapshot_dir / filename
    cv2.imwrite(str(path), annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
    logger.debug("Snapshot saved: %s", path)
    return path
