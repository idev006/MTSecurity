"""FrameBuffer — thread-safe single-slot buffer per camera."""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Frame:
    camera_id: int
    data: bytes           # JPEG-encoded
    width: int
    height: int
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FrameBuffer:
    """
    Holds the most-recent frame for every active camera.

    deque(maxlen=1) per camera_id — old frame auto-dropped when new one arrives.
    Thread-safe: CameraThread writes, AIPipeline + WebSocket reads.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._slots: dict[int, deque[Frame]] = {}

    def put(self, frame: Frame) -> None:
        with self._lock:
            if frame.camera_id not in self._slots:
                self._slots[frame.camera_id] = deque(maxlen=1)
            self._slots[frame.camera_id].append(frame)

    def get(self, camera_id: int) -> Frame | None:
        with self._lock:
            slot = self._slots.get(camera_id)
            if slot:
                return slot[-1]
            return None

    def get_all_latest(self) -> dict[int, Frame]:
        with self._lock:
            return {
                cam_id: slot[-1]
                for cam_id, slot in self._slots.items()
                if slot
            }

    def remove(self, camera_id: int) -> None:
        with self._lock:
            self._slots.pop(camera_id, None)

    def active_camera_ids(self) -> list[int]:
        with self._lock:
            return [cid for cid, slot in self._slots.items() if slot]

    def __len__(self) -> int:
        with self._lock:
            return len(self._slots)
