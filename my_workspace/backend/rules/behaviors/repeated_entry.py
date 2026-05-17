"""Repeated entry behavior — triggers when object enters a zone more than N times in a time window."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from rules.behaviors.base import RuleBehavior, TriggerResult

if TYPE_CHECKING:
    from ai.tracker import Track
    from rules.dwell_tracker import DwellTracker
    from rules.zone_manager import ZoneManager


class RepeatedEntryBehavior(RuleBehavior):
    name = "repeated_entry"

    def __init__(self) -> None:
        self._entry_times: dict[tuple[int, int], list[float]] = {}
        self._was_inside: dict[tuple[int, int], bool] = {}

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
        max_entries = params.get("max_entries", 3)
        time_window_seconds = params.get("time_window_seconds", 300)

        key = (rule_id, track.track_id)
        currently_inside = zone_manager.is_inside(zone_id, track.centroid)
        was_inside = self._was_inside.get(key, False)

        if currently_inside and not was_inside:
            now = time.monotonic()
            entries = self._entry_times.get(key, [])
            entries.append(now)
            entries = [t for t in entries if now - t < time_window_seconds]
            self._entry_times[key] = entries

            if len(entries) >= max_entries:
                confidence = min(1.0, len(entries) / max_entries)
                self._was_inside[key] = currently_inside
                return TriggerResult.yes(
                    confidence=confidence,
                    track_id=track.track_id,
                    entry_count=len(entries),
                    centroid=track.centroid,
                    bbox=track.bbox,
                )

        self._was_inside[key] = currently_inside
        return TriggerResult.no()
