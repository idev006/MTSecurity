"""ZoneManager — polygon geometry helpers for zone evaluation."""

from __future__ import annotations

import json
from typing import Sequence


Point = tuple[float, float]   # (x, y) normalised 0.0–1.0
Polygon = list[Point]


def point_in_polygon(point: Point, polygon: Polygon) -> bool:
    """
    Ray-casting algorithm — O(n) in number of polygon vertices.
    Works for convex and concave polygons.
    Returns True if point is strictly inside or on the boundary.
    """
    x, y = point
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def polygon_from_json(coords_json: str) -> Polygon:
    """Parse [[x,y], ...] JSON string to list of (x,y) tuples."""
    raw = json.loads(coords_json)
    return [(float(p[0]), float(p[1])) for p in raw]


def line_crossing_direction(
    prev: Point,
    curr: Point,
    line_start: Point,
    line_end: Point,
) -> int:
    """
    Check if the vector prev→curr crosses the segment line_start→line_end.

    Returns:
        +1  crossed left-to-right (entry)
        -1  crossed right-to-left (exit)
         0  no crossing
    """
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    d1 = cross(line_start, line_end, prev)
    d2 = cross(line_start, line_end, curr)

    if d1 * d2 >= 0:
        return 0   # same side or on the line

    d3 = cross(prev, curr, line_start)
    d4 = cross(prev, curr, line_end)

    if d3 * d4 >= 0:
        return 0   # segments don't intersect

    return 1 if d2 < 0 else -1


def polygon_area(polygon: Polygon) -> float:
    """Shoelace formula — area of polygon in normalised coords."""
    n = len(polygon)
    area = 0.0
    j = n - 1
    for i in range(n):
        area += (polygon[j][0] + polygon[i][0]) * (polygon[j][1] - polygon[i][1])
        j = i
    return abs(area) / 2.0


def centroid_in_zone(
    centroid: Point,
    zone_coords_json: str,
) -> bool:
    polygon = polygon_from_json(zone_coords_json)
    return point_in_polygon(centroid, polygon)


class ZoneManager:
    """Cache zone polygons parsed from DB JSON strings."""

    def __init__(self) -> None:
        self._cache: dict[int, Polygon] = {}

    def update_zone(self, zone_id: int, coords_json: str) -> None:
        self._cache[zone_id] = polygon_from_json(coords_json)

    def remove_zone(self, zone_id: int) -> None:
        self._cache.pop(zone_id, None)

    def is_inside(self, zone_id: int, point: Point) -> bool:
        polygon = self._cache.get(zone_id)
        if polygon is None:
            return False
        return point_in_polygon(point, polygon)

    def get_polygon(self, zone_id: int) -> Polygon | None:
        return self._cache.get(zone_id)
