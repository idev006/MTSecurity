"""SessionRegistry — maps track_id to its originating camera_id."""

from __future__ import annotations

import threading


class SessionRegistry:
    """Thread-safe track-ID → camera-ID lookup."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._map: dict[int, int] = {}   # track_id → camera_id

    def register(self, track_id: int, camera_id: int) -> None:
        with self._lock:
            self._map[track_id] = camera_id

    def get_camera(self, track_id: int) -> int | None:
        with self._lock:
            return self._map.get(track_id)

    def remove_track(self, track_id: int) -> None:
        with self._lock:
            self._map.pop(track_id, None)

    def remove_camera(self, camera_id: int) -> None:
        with self._lock:
            self._map = {tid: cid for tid, cid in self._map.items() if cid != camera_id}

    def active_tracks(self, camera_id: int) -> list[int]:
        with self._lock:
            return [tid for tid, cid in self._map.items() if cid == camera_id]

    def __len__(self) -> int:
        with self._lock:
            return len(self._map)
