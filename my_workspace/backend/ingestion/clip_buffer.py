"""ClipBuffer — per-camera ring buffer of JPEG frames; saves MP4 clips on demand."""

from __future__ import annotations

import logging
import shutil
import subprocess
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


def _resolve_ffmpeg(ffmpeg_path: str = "") -> str | None:
    """
    Return the path to the ffmpeg executable.

    Priority:
      1. ``ffmpeg_path`` setting (if non-empty and the file exists)
      2. ``ffmpeg`` / ``ffmpeg.exe`` found anywhere on PATH
      3. ``None`` → caller should warn and skip ffmpeg processing
    """
    if ffmpeg_path:
        p = Path(ffmpeg_path)
        if p.is_file():
            return str(p)
        logger.warning(
            "ClipBuffer: configured FFMPEG_PATH '%s' not found — falling back to PATH", ffmpeg_path
        )
    found = shutil.which("ffmpeg")
    if found:
        return found
    logger.warning(
        "ffmpeg not found (PATH and configured FFMPEG_PATH).  "
        "Clips will have moov-at-end; browser may show 0:00 duration."
    )
    return None


def _apply_faststart(
    src: Path,
    ffmpeg_exe: str | None,
    out_width: int = 0,
    out_height: int = 0,
    crf: int = 23,
) -> Path:
    """
    Re-encode / remux the clip via FFmpeg:
      - Scale to ``out_width × out_height`` (keeps AR when both > 0).
        Pass 0/0 to skip scaling.
      - Apply ``-movflags +faststart`` so the moov atom is at the front.

    If FFmpeg is unavailable the original file is returned unchanged.
    """
    if ffmpeg_exe is None:
        return src

    tmp = src.with_suffix(".tmp.mp4")

    # Build video filter: scale only if dimensions requested
    vf_parts: list[str] = []
    if out_width > 0 and out_height > 0:
        # force_original_aspect_ratio=decrease → letterbox to fit exactly
        vf_parts.append(
            f"scale={out_width}:{out_height}:force_original_aspect_ratio=decrease,"
            f"pad={out_width}:{out_height}:(ow-iw)/2:(oh-ih)/2"
        )

    cmd = [ffmpeg_exe, "-y", "-i", str(src)]
    if vf_parts:
        cmd += ["-vf", "".join(vf_parts), "-c:v", "libx264", "-crf", str(crf), "-preset", "fast"]
    else:
        cmd += ["-c", "copy"]
    cmd += ["-movflags", "+faststart", str(tmp)]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode == 0:
            src.unlink()
            tmp.rename(src)
            logger.debug("ClipBuffer: ffmpeg OK → %s", src)
        else:
            logger.warning(
                "ClipBuffer: ffmpeg failed (rc=%d): %s",
                result.returncode,
                result.stderr.decode(errors="replace")[-600:],
            )
            tmp.unlink(missing_ok=True)
    except Exception as exc:
        logger.warning("ClipBuffer: ffmpeg error — %s", exc)
        tmp.unlink(missing_ok=True)

    return src


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
        ffmpeg_path: str = "",
        out_width: int = 0,
        out_height: int = 0,
        crf: int = 23,
        pre_seconds: float = 0,
    ) -> Path | None:
        """
        Write buffered frames to an MP4 file, then run FFmpeg post-processing:
          - scale to ``out_width × out_height`` (0/0 = keep original)
          - apply faststart so browsers can determine clip duration

        ``pre_seconds`` trims the snapshot to at most ``pre_seconds * fps`` frames
        from the END of the buffer.  Pass 0 to use all buffered frames (legacy).
        Call this method after sleeping ``post_seconds`` so the buffer already
        contains post-event footage — the trim then selects exactly:
          [last pre_seconds of pre-event] + [post-event that arrived during sleep]

        Returns the Path on success, None if the buffer is empty or encoding fails.
        The file is named ``clip_<camera_id>_<event_id>.mp4``.
        """
        frames = self.snapshot(camera_id)
        if not frames:
            logger.warning("ClipBuffer: no frames for camera %d — skipping clip", camera_id)
            return None

        # Trim to at most (pre_seconds * fps) frames from the tail of the buffer.
        # At call time the buffer already contains post-event footage so the tail
        # naturally includes [pre_seconds of pre-event] + [post-event frames].
        if pre_seconds > 0:
            max_frames = int(pre_seconds * fps)
            if len(frames) > max_frames:
                frames = frames[-max_frames:]

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

            # ── FFmpeg: scale to target resolution + faststart ────────────────
            # cv2/mp4v writes moov at end-of-file; ffmpeg re-encodes/remuxes
            # to move moov to front AND resize to the configured output size.
            ffmpeg_exe = _resolve_ffmpeg(ffmpeg_path)
            out_path = _apply_faststart(out_path, ffmpeg_exe, out_width, out_height, crf)

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
