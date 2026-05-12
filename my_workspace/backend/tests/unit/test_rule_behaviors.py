"""Phase 3 Gate — Unit tests for all 5 rule behaviors."""

from __future__ import annotations

import time

import pytest

from rules.behaviors.abandoned_object import AbandonedObjectBehavior
from rules.behaviors.crowd_density import CrowdDensityBehavior
from rules.behaviors.intrusion import IntrusionBehavior
from rules.behaviors.line_crossing import LineCrossingBehavior
from rules.behaviors.loitering import LoiteringBehavior
from rules.dwell_tracker import DwellTracker
from rules.zone_manager import ZoneManager

# ── Fixtures ──────────────────────────────────────────────────────────────────

SQUARE_ZONE = "[[0.2,0.2],[0.8,0.2],[0.8,0.8],[0.2,0.8]]"
LINE_ZONE   = "[[0.5,0.0],[0.5,1.0],[0.5,1.0],[0.5,1.0]]"


def _zone_mgr(zone_id=1, coords=SQUARE_ZONE) -> ZoneManager:
    zm = ZoneManager()
    zm.update_zone(zone_id, coords)
    return zm


def _dwell() -> DwellTracker:
    return DwellTracker()


def _cfg(**kwargs):
    base = {"confidence_threshold": 0.5, "dwell_threshold_seconds": 2, "cooldown_seconds": 60}
    base.update(kwargs)
    return base


class _Track:
    def __init__(self, track_id=1, centroid=(0.5, 0.5), confidence=0.9,
                 label="person", class_id=0):
        self.track_id = track_id
        self.centroid = centroid
        self.confidence = confidence
        self.label = label
        self.class_id = class_id
        self.x1, self.y1 = centroid[0] - 0.05, centroid[1] - 0.1
        self.x2, self.y2 = centroid[0] + 0.05, centroid[1] + 0.1


# ── Intrusion ─────────────────────────────────────────────────────────────────

class TestIntrusionBehavior:
    def test_triggers_on_first_entry(self):
        b = IntrusionBehavior()
        track = _Track(centroid=(0.5, 0.5))   # inside square
        r = b.evaluate(track, 1, 1, _zone_mgr(), _dwell(), _cfg())
        assert r.triggered

    def test_no_trigger_outside_zone(self):
        b = IntrusionBehavior()
        track = _Track(centroid=(0.1, 0.1))   # outside
        r = b.evaluate(track, 1, 1, _zone_mgr(), _dwell(), _cfg())
        assert not r.triggered

    def test_no_trigger_on_second_frame_same_entry(self):
        b = IntrusionBehavior()
        dwell = _dwell()
        zm = _zone_mgr()
        track = _Track(centroid=(0.5, 0.5))
        b.evaluate(track, 1, 1, zm, dwell, _cfg())   # first frame — triggers
        r = b.evaluate(track, 1, 1, zm, dwell, _cfg())   # second frame — no retrigger
        assert not r.triggered

    def test_no_trigger_below_confidence(self):
        b = IntrusionBehavior()
        track = _Track(centroid=(0.5, 0.5), confidence=0.3)
        r = b.evaluate(track, 1, 1, _zone_mgr(), _dwell(), _cfg(confidence_threshold=0.6))
        assert not r.triggered


# ── Loitering ─────────────────────────────────────────────────────────────────

class TestLoiteringBehavior:
    def test_triggers_after_dwell_threshold(self):
        b = LoiteringBehavior()
        dwell = _dwell()
        zm = _zone_mgr()
        track = _Track(centroid=(0.5, 0.5))
        cfg = _cfg(dwell_threshold_seconds=0)   # 0 threshold → trigger immediately

        r = b.evaluate(track, 1, 1, zm, dwell, cfg)
        assert r.triggered
        assert "dwell_seconds" in r.metadata

    def test_no_trigger_before_threshold(self):
        b = LoiteringBehavior()
        dwell = _dwell()
        zm = _zone_mgr()
        track = _Track(centroid=(0.5, 0.5))
        cfg = _cfg(dwell_threshold_seconds=9999)

        r = b.evaluate(track, 1, 1, zm, dwell, cfg)
        assert not r.triggered

    def test_exits_zone_resets_dwell(self):
        b = LoiteringBehavior()
        dwell = _dwell()
        zm = _zone_mgr()
        track_in  = _Track(centroid=(0.5, 0.5))
        track_out = _Track(centroid=(0.1, 0.1))

        b.evaluate(track_in, 1, 1, zm, dwell, _cfg(dwell_threshold_seconds=0))
        b.evaluate(track_out, 1, 1, zm, dwell, _cfg())   # exits — resets
        assert dwell.get_dwell(1, 1) == 0.0


# ── LineCrossing ──────────────────────────────────────────────────────────────

class TestLineCrossingBehavior:
    def test_crossing_left_to_right_triggers(self):
        b = LineCrossingBehavior()
        zm = ZoneManager()
        zm.update_zone(1, "[[0.5,0.0],[0.5,1.0]]")
        dwell = _dwell()

        track_left  = _Track(track_id=1, centroid=(0.3, 0.5))
        track_right = _Track(track_id=1, centroid=(0.7, 0.5))

        b.evaluate(track_left, 1, 1, zm, dwell, _cfg())
        r = b.evaluate(track_right, 1, 1, zm, dwell, _cfg())
        assert r.triggered
        assert r.metadata.get("direction") in ("entry", "exit")

    def test_no_trigger_same_side(self):
        b = LineCrossingBehavior()
        zm = ZoneManager()
        zm.update_zone(1, "[[0.5,0.0],[0.5,1.0]]")
        dwell = _dwell()

        t1 = _Track(track_id=1, centroid=(0.2, 0.5))
        t2 = _Track(track_id=1, centroid=(0.3, 0.5))

        b.evaluate(t1, 1, 1, zm, dwell, _cfg())
        r = b.evaluate(t2, 1, 1, zm, dwell, _cfg())
        assert not r.triggered

    def test_no_trigger_on_first_frame(self):
        b = LineCrossingBehavior()
        zm = ZoneManager()
        zm.update_zone(1, "[[0.5,0.0],[0.5,1.0]]")
        track = _Track(centroid=(0.3, 0.5))
        r = b.evaluate(track, 1, 1, zm, _dwell(), _cfg())
        assert not r.triggered   # no previous position


# ── CrowdDensity ──────────────────────────────────────────────────────────────

class TestCrowdDensityBehavior:
    def test_triggers_when_count_exceeds_max(self):
        b = CrowdDensityBehavior()
        track = _Track()
        cfg = _cfg(dwell_threshold_seconds=3, zone_count=5)  # max=3, count=5
        r = b.evaluate(track, 1, 1, _zone_mgr(), _dwell(), cfg)
        assert r.triggered
        assert r.metadata["zone_count"] == 5

    def test_no_trigger_within_limit(self):
        b = CrowdDensityBehavior()
        track = _Track()
        cfg = _cfg(dwell_threshold_seconds=10, zone_count=3)
        r = b.evaluate(track, 1, 1, _zone_mgr(), _dwell(), cfg)
        assert not r.triggered


# ── AbandonedObject ───────────────────────────────────────────────────────────

class TestAbandonedObjectBehavior:
    def test_triggers_when_stationary_long_enough(self):
        b = AbandonedObjectBehavior()
        dwell = _dwell()
        zm = _zone_mgr()
        track = _Track(centroid=(0.5, 0.5))
        cfg = _cfg(dwell_threshold_seconds=0)  # immediate trigger

        b.evaluate(track, 1, 1, zm, dwell, cfg)   # enter
        r = b.evaluate(track, 1, 1, zm, dwell, cfg)  # stationary → trigger
        assert r.triggered

    def test_no_trigger_when_moving(self):
        b = AbandonedObjectBehavior()
        dwell = _dwell()
        zm = _zone_mgr()
        cfg = _cfg(dwell_threshold_seconds=0, movement_threshold=0.01)

        t1 = _Track(track_id=1, centroid=(0.3, 0.3))
        t2 = _Track(track_id=1, centroid=(0.5, 0.5))   # moved > 0.01

        b.evaluate(t1, 1, 1, zm, dwell, cfg)
        r = b.evaluate(t2, 1, 1, zm, dwell, cfg)  # reset anchor
        assert not r.triggered
