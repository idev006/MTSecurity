"""Unit tests for ZoneManager — point_in_polygon, line_crossing_direction, zone cache."""

from __future__ import annotations

import pytest

from rules.zone_manager import ZoneManager, point_in_polygon, line_crossing_direction


SQUARE = [(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)]


# ── point_in_polygon ──────────────────────────────────────────────────────────

class TestPointInPolygon:
    def test_center_inside(self):
        assert point_in_polygon((0.5, 0.5), SQUARE) is True

    def test_corner_outside(self):
        assert point_in_polygon((0.1, 0.1), SQUARE) is False

    def test_on_edge_no_crash(self):
        result = point_in_polygon((0.5, 0.2), SQUARE)
        assert isinstance(result, bool)

    def test_far_outside(self):
        assert point_in_polygon((0.0, 0.0), SQUARE) is False

    def test_near_corner_inside(self):
        assert point_in_polygon((0.21, 0.21), SQUARE) is True

    def test_concave_polygon_inside(self):
        poly = [(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (1.0, 0.5),
                (1.0, 1.0), (0.0, 1.0)]
        assert point_in_polygon((0.25, 0.25), poly) is True

    def test_concave_polygon_outside(self):
        poly = [(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (1.0, 0.5),
                (1.0, 1.0), (0.0, 1.0)]
        assert point_in_polygon((0.75, 0.25), poly) is False


# ── line_crossing_direction ───────────────────────────────────────────────────

class TestLineCrossingDirection:
    # Vertical line at x=0.5
    LS = (0.5, 0.0)
    LE = (0.5, 1.0)

    def test_left_to_right_returns_positive(self):
        d = line_crossing_direction((0.3, 0.5), (0.7, 0.5), self.LS, self.LE)
        assert d == 1

    def test_right_to_left_returns_negative(self):
        d = line_crossing_direction((0.7, 0.5), (0.3, 0.5), self.LS, self.LE)
        assert d == -1

    def test_same_side_returns_zero(self):
        d = line_crossing_direction((0.2, 0.5), (0.3, 0.5), self.LS, self.LE)
        assert d == 0

    def test_no_crossing_both_right(self):
        d = line_crossing_direction((0.6, 0.5), (0.8, 0.5), self.LS, self.LE)
        assert d == 0


# ── ZoneManager ───────────────────────────────────────────────────────────────

class TestZoneManager:
    def test_update_and_is_inside(self):
        zm = ZoneManager()
        zm.update_zone(1, "[[0.2,0.2],[0.8,0.2],[0.8,0.8],[0.2,0.8]]")
        assert zm.is_inside(1, (0.5, 0.5)) is True

    def test_point_outside_zone(self):
        zm = ZoneManager()
        zm.update_zone(1, "[[0.2,0.2],[0.8,0.2],[0.8,0.8],[0.2,0.8]]")
        assert zm.is_inside(1, (0.1, 0.1)) is False

    def test_unknown_zone_returns_false(self):
        zm = ZoneManager()
        assert zm.is_inside(99, (0.5, 0.5)) is False

    def test_remove_zone(self):
        zm = ZoneManager()
        zm.update_zone(2, "[[0.2,0.2],[0.8,0.2],[0.8,0.8],[0.2,0.8]]")
        zm.remove_zone(2)
        assert zm.is_inside(2, (0.5, 0.5)) is False

    def test_get_polygon(self):
        zm = ZoneManager()
        zm.update_zone(5, "[[0.5,0.0],[0.5,1.0],[0.5,1.0],[0.5,1.0]]")
        poly = zm.get_polygon(5)
        assert poly is not None
        assert len(poly) == 4

    def test_unknown_polygon_returns_none(self):
        zm = ZoneManager()
        assert zm.get_polygon(99) is None

    def test_update_zone_twice_uses_latest(self):
        zm = ZoneManager()
        zm.update_zone(1, "[[0.0,0.0],[0.3,0.0],[0.3,0.3],[0.0,0.3]]")
        assert zm.is_inside(1, (0.5, 0.5)) is False
        zm.update_zone(1, "[[0.2,0.2],[0.8,0.2],[0.8,0.8],[0.2,0.8]]")
        assert zm.is_inside(1, (0.5, 0.5)) is True
