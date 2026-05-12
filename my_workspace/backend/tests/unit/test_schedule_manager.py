"""Unit tests for ScheduleManager."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from rules.schedule_manager import ScheduleManager, is_rule_active


def _dt(hour: int, minute: int, weekday: int = 0) -> datetime:
    """Create a UTC datetime with given time on a Monday-anchored weekday."""
    # 2026-05-11 is a Monday (weekday=0)
    day_offset = weekday
    return datetime(2026, 5, 11 + day_offset, hour, minute, tzinfo=timezone.utc)


def _sched(start: str, end: str, days: list[int] | None = None) -> str:
    return json.dumps({"start": start, "end": end, "days": days or list(range(7))})


# ── is_rule_active (standalone function) ─────────────────────────────────────

class TestIsRuleActive:
    def test_none_schedule_always_active(self):
        assert is_rule_active(None) is True

    def test_within_window(self):
        assert is_rule_active(_sched("08:00", "18:00"), _dt(12, 0)) is True

    def test_before_window(self):
        assert is_rule_active(_sched("08:00", "18:00"), _dt(7, 59)) is False

    def test_after_window(self):
        assert is_rule_active(_sched("08:00", "18:00"), _dt(18, 1)) is False

    def test_at_exact_start(self):
        assert is_rule_active(_sched("08:00", "18:00"), _dt(8, 0)) is True

    def test_overnight_after_midnight(self):
        assert is_rule_active(_sched("22:00", "06:00"), _dt(2, 0)) is True

    def test_overnight_evening(self):
        assert is_rule_active(_sched("22:00", "06:00"), _dt(23, 30)) is True

    def test_overnight_midday_outside(self):
        assert is_rule_active(_sched("22:00", "06:00"), _dt(12, 0)) is False

    def test_day_filter_allowed(self):
        sched = _sched("08:00", "18:00", days=[0, 1, 2])
        assert is_rule_active(sched, _dt(12, 0, weekday=1)) is True

    def test_day_filter_disallowed(self):
        sched = _sched("08:00", "18:00", days=[0, 1, 2])
        assert is_rule_active(sched, _dt(12, 0, weekday=5)) is False

    def test_malformed_json_fails_open(self):
        assert is_rule_active("not-json") is True


# ── ScheduleManager class ─────────────────────────────────────────────────────

class TestScheduleManager:
    def test_no_schedule_always_active(self):
        mgr = ScheduleManager()
        assert mgr.is_active(99, _dt(0, 0)) is True

    def test_update_and_is_active(self):
        mgr = ScheduleManager()
        mgr.update(1, _sched("08:00", "18:00"))
        assert mgr.is_active(1, _dt(12, 0)) is True

    def test_update_and_is_inactive(self):
        mgr = ScheduleManager()
        mgr.update(1, _sched("08:00", "18:00"))
        assert mgr.is_active(1, _dt(20, 0)) is False

    def test_remove_reverts_to_always_active(self):
        mgr = ScheduleManager()
        mgr.update(1, _sched("08:00", "09:00"))
        assert mgr.is_active(1, _dt(20, 0)) is False
        mgr.remove(1)
        assert mgr.is_active(1, _dt(20, 0)) is True

    def test_multiple_rules_independent(self):
        mgr = ScheduleManager()
        mgr.update(1, _sched("08:00", "12:00"))
        mgr.update(2, _sched("13:00", "17:00"))
        now = _dt(10, 0)
        assert mgr.is_active(1, now) is True
        assert mgr.is_active(2, now) is False
