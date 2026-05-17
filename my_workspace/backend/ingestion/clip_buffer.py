"""ClipBuffer — per-camera ring buffer of JPEG frames; saves MP4 clips on demand."""

from __future__ import annotations

import logging
import threading
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ingestion.frame_buffer import Frame

logger = logging.getLogger(__name__)

# Default ring size: 150 frames ≈ 10 s at 15 fps.
# Kept entirely in RAM as compressed JPEGs — memory cost is low
# (≈ 30–50 KB/frame × 150 ≈ 5–8 MB per camera).
_DEFAULT_MAX_FRAMES = 150
_DEFAULT_FPS = 15.0


class ClipBuffer:
    """
    Thread-safe JPEG ring buffer per camera.

    CameraThread calls put() on every decoded frame.
    AlertManager calls save_clip() when a rule fires.

    save_clip() drains the current snapshot of frames and writes an MP4
    using cv2.VideoWriter (codec: mp4v). The clip contains the most recent
    ``max_frames`` frames — i.e. the seconds *leading up to* the alert.
    """

    def __init__(self, max_frames: int = _DEFAULT_MAX_FRAMES) -> None:
        self._max = max_frames
        self._lock = threading.Lock()
        # camera_id → deque of Frame objects (JPEG bytes)
        self._buffers: dict[int, deque] = {}

    # ── Write ─────────────────────────────────────────────────────────────────

    def put(self, frame: "Frame") -> None:
        """Append a frame to the ring buffer for its camera."""
        with self._lock:
            if frame.camera_id not in self._buffers:
                self._buffers[frame.camera_id] = deque(maxlen=self._max)
            self._buffers[frame.camera_id].append(frame)

    # ── Read (snapshot) ───────────────────────────────────────────────────────

    def snapshot(self, camera_id: int) -> list:
        """Return a stable copy of all frames currently buffered for camera_id."""
        with self._lock:
            buf = self._buffers.get(camera_id)
            if not buf:
                return []
            return list(buf)

    # ── Save ──────────────────────────────────────────────────────────────────

    def save_clip(
        self,
        camera_id: int,
        event_id: int,
        clip_dir: Path,
        fps: float = _DEFAULT_FPS,
    ) -> Path | None:
        """
        Write buffered frames to an MP4 file.

        Returns the Path on success, None if the buffer is empty or encoding fails.
        The file is named ``clip_<camera_id>_<event_id>.mp4``.
        """
        frames = self.snapshot(camera_id)
        if not frames:
            logger.warning("ClipBuffer: no frames for camera %d — skipping clip", camera_id)
            return None

        try:
            import cv2
            import numpy as np

            # Decode first frame to determine resolution
            first_img = cv2.imdecode(
                np.frombuffer(frames[0].data, np.uint8), cv2.IMREAD_COLOR
            )
            if first_img is None:
                logger.error("ClipBuffer: failed to decode first frame for camera %d", camera_id)
                return None

            h, w = first_img.shape[:2]
            clip_dir.mkdir(parents=True, exist_ok=True)
            out_path = clip_dir / f"clip_{camera_id}_{event_id}.mp4"

            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))

            writer.write(first_img)
            for frame in frames[1:]:
                img = cv2.imdecode(
                    np.frombuffer(frame.data, np.uint8), cv2.IMREAD_COLOR
                )
                if img is not None:
                    # Resize to match first frame if dimensions differ (safety)
                    if img.shape[:2] != (h, w):
                        img = cv2.resize(img, (w, h))
                    writer.write(img)

            writer.release()
            logger.info(
                "ClipBuffer: saved %d-frame clip → %s", len(frames), out_path
            )
            return out_path

        except Exception:
            logger.exception(
                "ClipBuffer: failed to save clip for camera %d event %d",
                camera_id, event_id,
            )
            return None

    def remove(self, camera_id: int) -> None:
        """Drop the buffer for a camera (called when camera is removed)."""
        with self._lock:
            self._buffers.pop(camera_id, None)
