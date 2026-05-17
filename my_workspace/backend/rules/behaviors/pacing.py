"""Pacing behavior — triggers when object repeatedly reverses direction (back-and-forth movement)."""

from __future__ import annotations

import math
from collections import deque
from typing import TYPE_CHECKING, Any

from rules.behaviors.base import RuleBehavior, TriggerResult

if TYPE_CHECKING:
    from ai.tracker import Track
    from rules.dwell_tracker import DwellTracker
    from rules.zone_manager import ZoneManager


class PacingBehavior(RuleBehavior):
    name = "pacing"

    def __init__(self) -> None:
        self._history: dict[tuple[int, int], deque] = {}

    def evaluate(
        self,
        track: "Track",
        rule_id: int,
        zone_id: int,
        zone_manager: "ZoneManager",
        dwell_tracker: "DwellTracker",
        config: dict[str, Any],
    ) -> TriggerResult:
        threshold = config.get("confidence_threshold", 0.6)
        if track.confidence < threshold:
            return TriggerResult.no()

        if not zone_manager.is_inside(zone_id, track.centroid):
            return TriggerResult.no()

        params = config.get("behavior_params") or {}
        reversal_threshold = params.get("reversal_threshold", 4)
        history_size = params.get("history_size", 40)
        min_displacement = params.get("min_displacement", 0.01)

        key = (rule_id, track.track_id)
        if key not in self._history:
            self._history[key] = deque(maxlen=history_size)

        self._history[key].append(track.centroid)
        pts = list(self._history[key])

        if len(pts) < 6:
            return TriggerResult.no()

        reversals = _count_reversals(pts, min_displacement)
        if reversals >= reversal_threshold:
            confidence = min(1.0, reversals / reversal_threshold)
            return TriggerResult.yes(
                confidence=confidence,
                track_id=track.track_id,
                reversals=reversals,
                centroid=track.centroid,
                bbox=track.bbox,
            )

        return TriggerResult.no()


def _count_reversals(pts: list, min_displacement: float) -> int:
    vectors = []
    for i in range(1, len(pts)):
        dx = pts[i][0] - pts[i - 1][0]
        dy = pts[i][1] - pts[i - 1][1]
        mag = math.sqrt(dx * dx + dy * dy)
        if mag >= min_displacement:
            vectors.append((dx / mag, dy / mag))

    if len(vectors) < 2:
        return 0

    reversals = 0
    for i in range(1, len(vectors)):
        dot = vectors[i - 1][0] * vectors[i][0] + vectors[i - 1][1] * vectors[i][1]
        # dot < cos(120°) = -0.5 means angle > 120° → reversal
        if dot < -0.5:
            reversals += 1

    return reversals
