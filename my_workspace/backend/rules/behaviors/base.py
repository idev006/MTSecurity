"""RuleBehavior ABC — all behavior plugins implement this interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai.tracker import Track
    from rules.dwell_tracker import DwellTracker
    from rules.zone_manager import ZoneManager


@dataclass
class TriggerResult:
    triggered: bool
    confidence: float = 0.0
    metadata: dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @classmethod
    def no(cls) -> "TriggerResult":
        return cls(triggered=False)

    @classmethod
    def yes(cls, confidence: float = 1.0, **meta) -> "TriggerResult":
        return cls(triggered=True, confidence=confidence, metadata=meta)


class RuleBehavior(ABC):
    """
    Each behavior evaluates one track against one rule/zone configuration
    and returns a TriggerResult.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Behavior identifier — matches Rule.behavior DB field."""
        ...

    @abstractmethod
    def evaluate(
        self,
        track: "Track",
        rule_id: int,
        zone_id: int,
        zone_manager: "ZoneManager",
        dwell_tracker: "DwellTracker",
        config: dict[str, Any],
    ) -> TriggerResult:
        """
        Evaluate whether this track triggers the rule.

        Args:
            track          — current track state
            rule_id        — DB rule ID (for keying dwell entries)
            zone_id        — DB zone ID
            zone_manager   — polygon lookup
            dwell_tracker  — dwell time accumulator
            config         — rule configuration dict
                             (confidence_threshold, dwell_threshold_seconds, etc.)
        """
        ...
