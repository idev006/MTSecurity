"""Unit tests for DwellTracker."""

from __future__ import annotations

import time

import pytest

from rules.dwell_tracker import DwellTracker


class TestDwellTracker:
    def test_initial_dwell_is_zero(self):
        dt = DwellTracker()
        assert dt.get_dwell(1, 1) == 0.0

    def test_touch_creates_entry(self):
        dt = DwellTracker()
        dt.touch(1, 1)
        assert (1, 1) in dt._entries

    def test_get_dwell_non_negative(self):
        dt = DwellTracker()
        dt.touch(1, 1)
        time.sleep(0.05)
        assert dt.get_dwell(1, 1) >= 0.0

    def test_dwell_increases_over_time(self):
        dt = DwellTracker()
        dt.touch(1, 1)
        time.sleep(0.05)
        d1 = dt.get_dwell(1, 1)
        time.sleep(0.05)
        dt.touch(1, 1)
        d2 = dt.get_dwell(1, 1)
        assert d2 >= d1

    def test_exit_removes_entry(self):
        dt = DwellTracker()
        dt.touch(1, 1)
        dt.exit(1, 1)
        assert dt.get_dwell(1, 1) == 0.0
        assert (1, 1) not in dt._entries

    def test_enter_does_not_overwrite_existing(self):
        dt = DwellTracker()
        dt.touch(1, 1)
        time.sleep(0.05)
        dt.enter(1, 1)   # should NOT reset first_seen
        dt.touch(1, 1)   # advance last_seen so dwell is measurable
        assert dt.get_dwell(1, 1) >= 0.04

    def test_independent_rule_track_pairs(self):
        dt = DwellTracker()
        dt.touch(1, 1)
        time.sleep(0.05)
        dt.touch(2, 2)
        d1 = dt.get_dwell(1, 1)
        d2 = dt.get_dwell(2, 2)
        assert d1 >= d2

    def test_remove_track_clears_all_rules(self):
        dt = DwellTracker()
        dt.touch(1, 42)
        dt.touch(2, 42)
        dt.touch(3, 42)
        dt.remove_track(42)
        assert dt.get_dwell(1, 42) == 0.0
        assert dt.get_dwell(2, 42) == 0.0

    def test_purge_stale_removes_old_entries(self):
        dt = DwellTracker()
        dt.touch(1, 1)
        entry = dt._entries[(1, 1)]
        entry.last_seen = entry.last_seen - 20   # simulate 20s ago
        removed = dt.purge_stale()
        assert removed == 1
        assert dt.get_dwell(1, 1) == 0.0

    def test_purge_stale_keeps_fresh_entries(self):
        dt = DwellTracker()
        dt.touch(1, 1)
        removed = dt.purge_stale()
        assert removed == 0
        assert (1, 1) in dt._entries

    def test_has_entry_true_after_touch(self):
        dt = DwellTracker()
        assert dt.has_entry(1, 1) is False
        dt.touch(1, 1)
        assert dt.has_entry(1, 1) is True

    def test_has_entry_false_after_exit(self):
        dt = DwellTracker()
        dt.touch(1, 1)
        dt.exit(1, 1)
        assert dt.has_entry(1, 1) is False

    def test_len(self):
        dt = DwellTracker()
        assert len(dt) == 0
        dt.touch(1, 1)
        dt.touch(1, 2)
        assert len(dt) == 2
