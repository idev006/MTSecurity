"""AbandonedObject behavior — triggers when an object stays still for too long.

Design note — position-based dwell (not track-id-based):
  Stationary objects cause confidence to flicker, which makes the IoU tracker
  drop and re-create tracks frequently (TRK-100 → TRK-101 → ...).  A track-id-
  keyed dwell timer resets to 0 every time the ID changes, so the threshold is
  never reached.

  This implementation keys dwell on a *spatial grid cell* (4 % of frame width/
  height).  As long as a detection lands in the same cell, the timer continues
  regardless of track_id.  A ghost TTL keeps the cell alive for brief detection
  gaps (flickering confidence), and the ghost is cleared if no detection arrives
  within ghost_ttl seconds.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from rules.behaviors.base import RuleBehavior, TriggerResult

if TYPE_CHECKING:
    from ai.tracker import Track
    from rules.dwell_tracker import DwellTracker
    from rules.zone_manager import ZoneManager

logger = logging.getLogger(__name__)

_MOVEMENT_THRESHOLD = 0.02  # normalised units — reset if object moves > 2 % of frame
_GRID_SIZE = 0.04           # spatial cell size — detections within 4 % are the same object
_GHOST_TTL_MULTIPLIER = 2   # ghost survives for 2 × dwell_threshold after last detection


class AbandonedObjectBehavior(RuleBehavior):
    """
    Fires when a stationary object (centroid barely moves) stays in zone
    beyond dwell_threshold_seconds. Useful for detecting bags, packages, etc.

    Dwell is keyed on a spatial grid cell so track_id changes (caused by
    flickering confidence on still objects) do not reset the timer.
    """

    name = "abandoned_object"

    # pos_key → (first_seen_monotonic, last_seen_monotonic, anchor_centroid)
    _PosState = tuple[float, float, tuple[float, float]]

    def __init__(self) -> None:
        self._pos_state: dict[tuple, "AbandonedObjectBehavior._PosState"] = {}

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _pos_key(rule_id: int, centroid: tuple[float, float], grid: float = _GRID_SIZE) -> tuple:
        """Quantise centroid to a grid cell — coarse position fingerprint."""
        cx, cy = centroid
        return (rule_id, int(cx / grid), int(cy / grid))

    def _purge_stale(self, ghost_ttl: float) -> None:
        """Remove grid cells not touched within ghost_ttl seconds."""
        now = time.monotonic()
        dead = [k for k, (_, last, _) in self._pos_state.items() if now - last > ghost_ttl]
        for k in dead:
            del self._pos_state[k]

    # ── Main evaluate ─────────────────────────────────────────────────────────

    def evaluate(
        self,
        track: "Track",
        rule_id: int,
        zone_id: int,
        zone_manager: "ZoneManager",
        dwell_tracker: "DwellTracker",  # kept for API compatibility, not used here
        config: dict[str, Any],
    ) -> TriggerResult:
        threshold       = config.get("confidence_threshold", 0.6)
        dwell_threshold = config.get("dwell_threshold_seconds", 60)
        bp: dict        = config.get("behavior_params") or {}
        move_thresh     = bp.get("movement_threshold", _MOVEMENT_THRESHOLD)
        ghost_ttl       = max(dwell_threshold * _GHOST_TTL_MULTIPLIER, 30.0)

        logger.debug(
            "AbandonedObject rule=%d track=%d label=%s conf=%.2f centroid=%s zone=%d dwell_threshold=%ds",
            rule_id, track.track_id, track.label, track.confidence, track.centroid, zone_id, dwell_threshold,
        )

        if track.confidence < threshold:
            logger.debug(
                "AbandonedObject: SKIP track=%d — conf %.2f < threshold %.2f",
                track.track_id, track.confidence, threshold,
            )
            return TriggerResult.no()

        if not zone_manager.is_inside(zone_id, track.centroid):
            logger.debug(
                "AbandonedObject: SKIP track=%d label=%s — outside zone %d",
                track.track_id, track.label, zone_id,
            )
            return TriggerResult.no()

        # Housekeeping — drop cells that haven't been touched recently
        self._purge_stale(ghost_ttl)

        cx, cy = track.centroid
        pos_k  = self._pos_key(rule_id, (cx, cy))
        now    = time.monotonic()

        if pos_k not in self._pos_state:
            # First time we see something in this cell
            self._pos_state[pos_k] = (now, now, (cx, cy))
            logger.debug("AbandonedObject: NEW cell %s track=%d", pos_k, track.track_id)
            return TriggerResult.no()

        first_seen, _last_seen, (ax, ay) = self._pos_state[pos_k]
        dist = ((cx - ax) ** 2 + (cy - ay) ** 2) ** 0.5

        if dist > move_thresh:
            # Object moved significantly within the cell — reset the cell timer
            logger.debug(
                "AbandonedObject: MOVED cell %s track=%d dist=%.4f > %.4f — resetting",
                pos_k, track.track_id, dist, move_thresh,
            )
            self._pos_state[pos_k] = (now, now, (cx, cy))
            return TriggerResult.no()

        # Object still in same position — update last_seen, keep first_seen intact
        self._pos_state[pos_k] = (first_seen, now, (ax, ay))
        dwell = now - first_seen

        logger.debug(
            "AbandonedObject: STATIONARY cell %s track=%d dwell=%.1fs / %ds",
            pos_k, track.track_id, dwell, dwell_threshold,
        )

        if dwell >= dwell_threshold:
            return TriggerResult.yes(
                confidence=track.confidence,
                track_id=track.track_id,
                dwell_seconds=round(dwell, 1),
                stationary_at=track.centroid,
            )
        return TriggerResult.no()
