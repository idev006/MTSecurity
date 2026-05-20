"""Unit tests for EvidenceStore — thread safety, pin/get/remove."""

from __future__ import annotations

import threading
from datetime import datetime, timezone

import pytest

from ingestion.evidence_store import EvidenceStore, PinnedEvidence
from ingestion.frame_buffer import Frame


# ── Helpers ───────────────────────────────────────────────────────────────────

def _frame(camera_id: int = 1) -> Frame:
    return Frame(
        camera_id=camera_id,
        data=b"\xff\xd8\xff",   # minimal JPEG header bytes
        width=640,
        height=360,
        captured_at=datetime.now(timezone.utc),
    )


def _tracks(n: int = 2) -> list[dict]:
    return [
        {
            "track_id": i,
            "label": "person",
            "confidence": 0.9,
            "bbox": {"x1": 0.1 * i, "y1": 0.1, "x2": 0.2 * i, "y2": 0.3},
        }
        for i in range(1, n + 1)
    ]


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestEvidenceStorePinGet:
    def test_get_returns_none_before_pin(self):
        store = EvidenceStore()
        assert store.get(99) is None

    def test_pin_then_get_returns_evidence(self):
        store = EvidenceStore()
        frame = _frame(camera_id=1)
        tracks = _tracks(3)
        store.pin(1, frame, tracks)

        pinned = store.get(1)
        assert pinned is not None
        assert pinned.frame is frame
        assert len(pinned.tracks) == 3

    def test_pin_overwrites_previous_evidence(self):
        store = EvidenceStore()
        store.pin(1, _frame(), _tracks(1))
        new_frame = _frame()
        store.pin(1, new_frame, _tracks(5))

        pinned = store.get(1)
        assert pinned.frame is new_frame
        assert len(pinned.tracks) == 5

    def test_pin_is_isolated_per_camera(self):
        store = EvidenceStore()
        store.pin(1, _frame(1), _tracks(2))
        store.pin(2, _frame(2), _tracks(4))

        assert len(store.get(1).tracks) == 2
        assert len(store.get(2).tracks) == 4

    def test_tracks_are_copied_not_shared(self):
        """Mutating the original list must not affect stored evidence."""
        store = EvidenceStore()
        tracks = _tracks(2)
        store.pin(1, _frame(), tracks)
        tracks.clear()   # mutate original

        pinned = store.get(1)
        assert len(pinned.tracks) == 2   # store is unaffected

    def test_remove_drops_camera(self):
        store = EvidenceStore()
        store.pin(1, _frame(), _tracks(1))
        store.remove(1)
        assert store.get(1) is None

    def test_remove_nonexistent_camera_is_safe(self):
        store = EvidenceStore()
        store.remove(999)   # must not raise

    def test_len_reflects_cameras_pinned(self):
        store = EvidenceStore()
        assert len(store) == 0
        store.pin(1, _frame(), _tracks(1))
        store.pin(2, _frame(), _tracks(1))
        assert len(store) == 2
        store.remove(1)
        assert len(store) == 1


class TestEvidenceStoreThreadSafety:
    """Concurrent writers from multiple threads must not corrupt the store."""

    def test_concurrent_pins_do_not_corrupt(self):
        store = EvidenceStore()
        errors: list[Exception] = []

        def _writer(camera_id: int, n_tracks: int) -> None:
            try:
                for _ in range(100):
                    store.pin(camera_id, _frame(camera_id), _tracks(n_tracks))
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=_writer, args=(cam_id, cam_id))
            for cam_id in range(1, 6)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"
        # All cameras should have evidence
        for cam_id in range(1, 6):
            assert store.get(cam_id) is not None

    def test_concurrent_read_write_does_not_raise(self):
        store = EvidenceStore()
        store.pin(1, _frame(), _tracks(2))
        errors: list[Exception] = []

        def _reader() -> None:
            try:
                for _ in range(200):
                    store.get(1)
            except Exception as exc:
                errors.append(exc)

        def _writer() -> None:
            try:
                for i in range(200):
                    store.pin(1, _frame(), _tracks(i % 5 + 1))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_reader) for _ in range(3)]
        threads += [threading.Thread(target=_writer) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
