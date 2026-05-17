"""Sudden gathering behavior — triggers when person count in a zone spikes rapidly."""

from __future__ import annotations

import time
from collections import deque
from typing import TYPE_CHECKING, Any

from rules.behaviors.base import RuleBehavior, TriggerResult

if TYPE_CHECKING:
    from ai.tracker import Track
    from rules.dwell_tracker import DwellTracker
    from rules.zone_manager import ZoneManager


class SuddenGatheringBehavior(RuleBehavior):
    name = "sudden_gathering"

    def __init__(self) -> None:
        # Keyed by rule_id only (zone-level, not per-track)
        self._count_history: dict[int, deque] = {}

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

        params = config.get("behavior_params") or {}
        min_persons = params.get("min_persons", 3)
        rate_window_seconds = params.get("rate_window_seconds", 10)
        min_increase = params.get("min_increase", 2)

        zone_count = config.get("zone_count", 0)

        if rule_id not in self._count_history:
            self._count_history[rule_id] = deque()

        now = time.monotonic()
        history = self._count_history[rule_id]
        history.append((now, zone_count))

        # Prune old entries
        while history and now - history[0][0] > rate_window_seconds:
            history.popleft()

        if len(history) < 2:
            return TriggerResult.no()

        counts = [c for _, c in history]
        increase = max(counts) - min(counts)

        if zone_count >= min_persons and increase >= min_increase:
            confidence = min(1.0, zone_count / (min_persons * 2))
            return TriggerResult.yes(
                confidence=confidence,
                track_id=track.track_id,
                zone_count=zone_count,
                increase=increase,
                centroid=track.centroid,
                bbox=track.bbox,
            )

        return TriggerResult.no()
