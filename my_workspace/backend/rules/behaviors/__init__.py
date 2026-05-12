from rules.behaviors.abandoned_object import AbandonedObjectBehavior
from rules.behaviors.base import RuleBehavior, TriggerResult
from rules.behaviors.crowd_density import CrowdDensityBehavior
from rules.behaviors.intrusion import IntrusionBehavior
from rules.behaviors.line_crossing import LineCrossingBehavior
from rules.behaviors.loitering import LoiteringBehavior

BEHAVIOR_REGISTRY: dict[str, RuleBehavior] = {
    "intrusion":        IntrusionBehavior(),
    "loitering":        LoiteringBehavior(),
    "line_crossing":    LineCrossingBehavior(),
    "crowd_density":    CrowdDensityBehavior(),
    "abandoned_object": AbandonedObjectBehavior(),
}

__all__ = [
    "RuleBehavior", "TriggerResult", "BEHAVIOR_REGISTRY",
    "IntrusionBehavior", "LoiteringBehavior", "LineCrossingBehavior",
    "CrowdDensityBehavior", "AbandonedObjectBehavior",
]
