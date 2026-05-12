"""Phase 2 Gate — ObjectTracker: IoU matching, track IDs, age-out."""

from __future__ import annotations

from ai.detector import Detection
from ai.tracker import ObjectTracker


def _det(x1=0.1, y1=0.1, x2=0.5, y2=0.5, conf=0.9, label="person") -> Detection:
    return Detection(label=label, class_id=0, confidence=conf, x1=x1, y1=y1, x2=x2, y2=y2)


# ── Track creation ────────────────────────────────────────────────────────────

def test_first_frame_creates_tracks():
    tracker = ObjectTracker()
    tracks = tracker.update([_det()])
    assert len(tracks) == 1
    assert tracks[0].track_id == 1


def test_track_ids_are_unique():
    tracker = ObjectTracker()
    tracks = tracker.update([_det(0.0, 0.0, 0.3, 0.3), _det(0.5, 0.5, 0.9, 0.9)])
    ids = {t.track_id for t in tracks}
    assert len(ids) == 2


def test_empty_detections_returns_empty_first_frame():
    tracker = ObjectTracker()
    tracks = tracker.update([])
    assert tracks == []


# ── Matching and persistence ──────────────────────────────────────────────────

def test_same_box_keeps_same_track_id():
    tracker = ObjectTracker()
    t1 = tracker.update([_det(0.1, 0.1, 0.5, 0.5)])
    tid = t1[0].track_id
    # Slightly moved box — still high IoU
    t2 = tracker.update([_det(0.11, 0.11, 0.51, 0.51)])
    assert t2[0].track_id == tid


def test_non_overlapping_boxes_spawn_new_tracks():
    tracker = ObjectTracker()
    tracker.update([_det(0.0, 0.0, 0.2, 0.2)])  # track 1
    # Completely different position
    t2 = tracker.update([_det(0.7, 0.7, 0.9, 0.9)])
    ids = {t.track_id for t in t2}
    # Track 1 aged out eventually; new track spawned
    assert any(tid > 1 for tid in ids)


def test_hits_increment_on_match():
    tracker = ObjectTracker()
    t1 = tracker.update([_det()])
    assert t1[0].hits == 1
    t2 = tracker.update([_det(0.1, 0.1, 0.51, 0.51)])
    assert t2[0].hits == 2


# ── Age-out ───────────────────────────────────────────────────────────────────

def test_track_ages_out_when_no_detections():
    tracker = ObjectTracker(max_age=2)
    tracker.update([_det()])           # create track, age=0
    tracker.update([])                 # age=1
    tracker.update([])                 # age=2
    tracks = tracker.update([])        # age=3 > max_age=2 → removed
    assert tracks == []


def test_track_survives_within_max_age():
    tracker = ObjectTracker(max_age=3)
    tracker.update([_det()])
    tracker.update([])  # age=1
    tracker.update([])  # age=2
    tracks = tracker.update([])  # age=3 == max_age → still alive
    assert len(tracks) == 1


# ── Reset ─────────────────────────────────────────────────────────────────────

def test_reset_clears_all_tracks():
    tracker = ObjectTracker()
    tracker.update([_det(), _det(0.5, 0.5, 0.9, 0.9)])
    tracker.reset()
    tracks = tracker.update([_det()])
    assert tracks[0].track_id == 1   # IDs reset to 1


# ── SessionRegistry ───────────────────────────────────────────────────────────

def test_session_registry_register_and_get():
    from ai.session_registry import SessionRegistry
    reg = SessionRegistry()
    reg.register(1, 5)
    reg.register(2, 5)
    assert reg.get_camera(1) == 5
    assert reg.get_camera(2) == 5
    assert reg.get_camera(99) is None


def test_session_registry_remove_track():
    from ai.session_registry import SessionRegistry
    reg = SessionRegistry()
    reg.register(1, 5)
    reg.remove_track(1)
    assert reg.get_camera(1) is None


def test_session_registry_active_tracks_per_camera():
    from ai.session_registry import SessionRegistry
    reg = SessionRegistry()
    reg.register(1, 5)
    reg.register(2, 5)
    reg.register(3, 7)
    assert set(reg.active_tracks(5)) == {1, 2}
    assert set(reg.active_tracks(7)) == {3}
