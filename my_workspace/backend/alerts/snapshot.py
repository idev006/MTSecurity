"""Snapshot — annotate frame with bounding boxes + labels → JPEG."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_FONT      = cv2.FONT_HERSHEY_SIMPLEX
_COLORS = {
    "low":      (0, 255, 0),      # green
    "medium":   (0, 165, 255),    # orange
    "high":     (0, 0, 255),      # red
    "critical": (128, 0, 128),    # purple
}


def _scale_params(w: int, cfg_font_scale: float = 0.0, cfg_box_thickness: int = 0) -> tuple[float, int, int]:
    """
    Return (font_scale, text_thickness, box_thickness) sized for image width.

    Auto-scale keeps text legible across all evidence tiers:
      THUMBNAIL  320 px → scale ≈ 0.40  thin lines
      MONITOR    640 px → scale ≈ 0.50
      DETAIL    1280 px → scale ≈ 0.90  thicker lines
      EVIDENCE  1920 px → scale ≈ 1.20  (capped)

    Pass cfg_font_scale > 0 (from ANNOTATION_FONT_SCALE in .env) to override.
    Pass cfg_box_thickness > 0 (from ANNOTATION_BOX_THICKNESS in .env) to override.
    """
    if cfg_font_scale > 0:
        font_scale = cfg_font_scale
    else:
        # Target: ~0.80 at 640px, ~1.20 at 960px, capped at 1.50
        font_scale = max(0.65, min(1.50, w / 800.0))

    text_thickness = max(1, int(font_scale * 1.5))

    if cfg_box_thickness > 0:
        box_thickness = cfg_box_thickness
    else:
        box_thickness = max(1, int(w / 400))

    return font_scale, text_thickness, box_thickness


def annotate_frame(
    frame: np.ndarray,
    detections: list[dict],
    rule_name: str = "",
    severity: str = "medium",
    timestamp: datetime | None = None,
) -> np.ndarray:
    """
    Draw bounding boxes, labels, rule name, timestamp on a BGR frame.
    Font sizes scale automatically with image resolution.
    Returns annotated copy (does not mutate original).
    """
    from config import get_settings
    cfg = get_settings()

    out = frame.copy()
    h, w = out.shape[:2]
    color = _COLORS.get(severity, _COLORS["medium"])
    font_scale, text_thick, box_thick = _scale_params(
        w,
        cfg_font_scale=cfg.annotation_font_scale,
        cfg_box_thickness=cfg.annotation_box_thickness,
    )
    pad = max(4, int(w / 200))   # label background padding scales too

    for det in detections:
        bbox = det.get("bbox", {})
        x1 = int(bbox.get("x1", 0) * w)
        y1 = int(bbox.get("y1", 0) * h)
        x2 = int(bbox.get("x2", 1) * w)
        y2 = int(bbox.get("y2", 1) * h)

        cv2.rectangle(out, (x1, y1), (x2, y2), color, box_thick)

        label = det.get("label", "")
        conf = det.get("confidence", 0.0)
        track_id = det.get("track_id")
        text = f"{label} {conf:.0%}"
        if track_id is not None:
            text += f" #{track_id}"

        (tw, th), _ = cv2.getTextSize(text, _FONT, font_scale, text_thick)
        ty = max(y1 - pad, th + pad)   # keep label inside frame top
        cv2.rectangle(out, (x1, ty - th - pad), (x1 + tw + pad, ty), color, -1)
        cv2.putText(out, text, (x1 + pad // 2, ty - pad // 2),
                    _FONT, font_scale, (255, 255, 255), text_thick, cv2.LINE_AA)

    # Overlay banner — height + font scale with image
    banner_h = max(24, int(h * 0.038))
    ts = (timestamp or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M:%S UTC")
    banner = f"[{severity.upper()}] {rule_name} | {ts}"
    cv2.rectangle(out, (0, 0), (w, banner_h), (0, 0, 0), -1)
    cv2.putText(out, banner, (pad, banner_h - pad),
                _FONT, font_scale * 0.85, (255, 255, 255), text_thick, cv2.LINE_AA)

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
