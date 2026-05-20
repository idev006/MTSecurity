"""EvidenceStore — pins the last-inferred frame + all active tracks per camera.

Why this exists
---------------
The live FrameBuffer is overwritten on every camera tick (30+ fps).
By the time AlertManager handles a RULE_TRIGGERED message, the frame that
actually triggered the rule may already be gone — the snapshot ends up showing
a later frame, or even a frame where the subject has left the scene.

EvidenceStore solves this by letting AIPipeline "pin" the frame it just ran
inference on (together with the full list of active tracks) immediately after
inference.  AlertManager then reads from here instead of the live buffer,
guaranteeing:
  1. The snapshot shows the exact moment the rule fired (frame pinning).
  2. All objects visible at that moment are annotated (all-tracks evidence).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from ingestion.frame_buffer import Frame


@dataclass
class PinnedEvidence:
    """Snapshot of inference state for one camera at one point in time."""
    frame: Frame
    tracks: list[dict[str, Any]] = field(default_factory=list)
    # tracks schema per item:
    # {
    #   "track_id": int,
    #   "label":    str,
    #   "confidence": float,
    #   "bbox": {"x1": float, "y1": float, "x2": float, "y2": float},
    # }


class EvidenceStore:
    """
    Thread-safe store of the most-recently-inferred frame + tracks per camera.

    Writers:  AIPipeline (background thread) — calls pin() after every inference.
    Readers:  AlertManager (async event loop) — calls get() when saving a snapshot.

    One slot per camera; old evidence is replaced on every inference cycle.
    The lock is held only for the dict update / lookup — no I/O inside the lock.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: dict[int, PinnedEvidence] = {}

    # ── Write ────────────────────────────────────────────────────────────────

    def pin(
        self,
        camera_id: int,
        frame: Frame,
        tracks: list[dict[str, Any]],
    ) -> None:
        """Replace the pinned evidence for *camera_id*."""
        evidence = PinnedEvidence(frame=frame, tracks=list(tracks))
        with self._lock:
            self._store[camera_id] = evidence

    # ── Read ─────────────────────────────────────────────────────────────────

    def get(self, camera_id: int) -> PinnedEvidence | None:
        """Return pinned evidence for *camera_id*, or None if not yet available."""
        with self._lock:
            return self._store.get(camera_id)

    def remove(self, camera_id: int) -> None:
        """Drop evidence for a camera that has been removed."""
        with self._lock:
            self._store.pop(camera_id, None)

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)
