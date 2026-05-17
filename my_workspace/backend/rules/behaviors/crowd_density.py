"""CrowdDensity behavior — triggers when too many objects are in a zone."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rules.behaviors.base import RuleBehavior, TriggerResult

if TYPE_CHECKING:
    from ai.tracker import Track
    from rules.dwell_tracker import DwellTracker
    from rules.zone_manager import ZoneManager


class CrowdDensityBehavior(RuleBehavior):
    """
    Evaluated at the zone level (not per-track).
    RuleEngine calls this once per zone per frame, passing the lead track.
    The zone_count is injected via config["zone_count"].
    """

    name = "crowd_density"

    def evaluate(
        self,
        track: "Track",
        rule_id: int,
        zone_id: int,
        zone_manager: "ZoneManager",
        dwell_tracker: "DwellTracker",
        config: dict[str, Any],
    ) -> TriggerResult:
        zone_count: int = config.get("zone_count", 0)
        # max_persons lives in behavior_params (set via UI).
        # Default 5: trigger when more than 5 people are detected in the zone.
        # (dwell_threshold_seconds is meaningless for crowd_density and is ignored.)
        bp: dict = config.get("behavior_params") or {}
        max_count: int = bp.get("max_persons", 5)
        threshold = config.get("confidence_threshold", 0.6)

        if track.confidence < threshold:
            return TriggerResult.no()

        if zone_count > max_count:
            return TriggerResult.yes(
                confidence=min(1.0, zone_count / (max_count + 1)),
                zone_count=zone_count,
                max_allowed=max_count,
                zone_id=zone_id,
            )
        return TriggerResult.no()
