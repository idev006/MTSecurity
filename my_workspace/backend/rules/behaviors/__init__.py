from rules.behaviors.abandoned_object import AbandonedObjectBehavior
from rules.behaviors.base import RuleBehavior, TriggerResult
from rules.behaviors.crowd_density import CrowdDensityBehavior
from rules.behaviors.crouching import CrouchingBehavior
from rules.behaviors.fall_detection import FallDetectionBehavior
from rules.behaviors.intrusion import IntrusionBehavior
from rules.behaviors.line_crossing import LineCrossingBehavior
from rules.behaviors.loitering import LoiteringBehavior
from rules.behaviors.pacing import PacingBehavior
from rules.behaviors.repeated_entry import RepeatedEntryBehavior
from rules.behaviors.running import RunningBehavior
from rules.behaviors.sudden_gathering import SuddenGatheringBehavior

BEHAVIOR_REGISTRY: dict[str, RuleBehavior] = {
    "intrusion":         IntrusionBehavior(),
    "loitering":         LoiteringBehavior(),
    "line_crossing":     LineCrossingBehavior(),
    "crowd_density":     CrowdDensityBehavior(),
    "abandoned_object":  AbandonedObjectBehavior(),
    "running":           RunningBehavior(),
    "fall_detection":    FallDetectionBehavior(),
    "crouching":         CrouchingBehavior(),
    "repeated_entry":    RepeatedEntryBehavior(),
    "pacing":            PacingBehavior(),
    "sudden_gathering":  SuddenGatheringBehavior(),
}

__all__ = [
    "RuleBehavior", "TriggerResult", "BEHAVIOR_REGISTRY",
    "IntrusionBehavior", "LoiteringBehavior", "LineCrossingBehavior",
    "CrowdDensityBehavior", "AbandonedObjectBehavior",
    "RunningBehavior", "FallDetectionBehavior", "CrouchingBehavior",
    "RepeatedEntryBehavior", "PacingBehavior", "SuddenGatheringBehavior",
]
