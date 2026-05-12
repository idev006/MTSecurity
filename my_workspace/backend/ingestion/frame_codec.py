"""FrameCodec — JPEG encode/decode + resolution tier resizing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np


class ResolutionTier(str, Enum):
    THUMBNAIL = "THUMBNAIL"    # 320×180  @ 3 fps  — 10-camera grid
    MONITOR   = "MONITOR"      # 640×360  @ 10 fps — primary single view
    DETAIL    = "DETAIL"       # 1280×720 @ 15 fps — focus/evidence
    EVIDENCE  = "EVIDENCE"     # original resolution — snapshot/clip


@dataclass(frozen=True)
class TierSpec:
    width: int
    height: int
    jpeg_quality: int


_TIER_SPECS: dict[ResolutionTier, TierSpec] = {
    ResolutionTier.THUMBNAIL: TierSpec(320,  180,  60),
    ResolutionTier.MONITOR:   TierSpec(640,  360,  75),
    ResolutionTier.DETAIL:    TierSpec(1280, 720,  85),
    ResolutionTier.EVIDENCE:  TierSpec(0,    0,    95),  # 0 = keep original
}


def encode_frame(
    frame: np.ndarray,
    tier: ResolutionTier = ResolutionTier.THUMBNAIL,
) -> bytes:
    """Resize frame to tier resolution and JPEG-encode it."""
    spec = _TIER_SPECS[tier]

    if spec.width > 0:
        h, w = frame.shape[:2]
        if w != spec.width or h != spec.height:
            frame = cv2.resize(frame, (spec.width, spec.height), interpolation=cv2.INTER_AREA)

    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, spec.jpeg_quality])
    if not ok:
        raise ValueError("JPEG encode failed")
    return buf.tobytes()


def decode_frame(data: bytes) -> np.ndarray:
    """Decode JPEG bytes to BGR ndarray."""
    arr = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("JPEG decode failed")
    return frame


def frame_to_rgb(frame: np.ndarray) -> np.ndarray:
    """Convert BGR (OpenCV default) to RGB for model inference."""
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def resize_for_inference(frame: np.ndarray, target_size: int = 640) -> np.ndarray:
    """Letterbox-resize frame to square inference input."""
    h, w = frame.shape[:2]
    scale = target_size / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    canvas = np.full((target_size, target_size, 3), 114, dtype=np.uint8)
    pad_top = (target_size - new_h) // 2
    pad_left = (target_size - new_w) // 2
    canvas[pad_top:pad_top + new_h, pad_left:pad_left + new_w] = resized
    return canvas, scale, pad_top, pad_left


def get_frame_dims(tier: ResolutionTier) -> tuple[int, int]:
    spec = _TIER_SPECS[tier]
    return spec.width, spec.height
