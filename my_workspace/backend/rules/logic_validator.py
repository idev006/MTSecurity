"""LogicValidator — evaluates complex Rule Logic Trees (AND/OR)."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from rules.behaviors import BEHAVIOR_REGISTRY

if TYPE_CHECKING:
    from rules.dwell_tracker import DwellTracker
    from rules.schedule_manager import ScheduleManager
    from rules.zone_manager import ZoneManager

logger = logging.getLogger(__name__)


class LogicValidator:
    """
    Recursive validator for Rule Logic Trees.
    
    A Logic Tree is a JSON structure with operators (AND, OR, NOT) and leaf conditions.
    """

    def __init__(
        self,
        zone_mgr: "ZoneManager",
        schedule_mgr: "ScheduleManager",
        dwell_tracker: "DwellTracker"
    ) -> None:
        self._zone_mgr = zone_mgr
        self._schedule_mgr = schedule_mgr
        self._dwell = dwell_tracker

    def evaluate(self, logic_tree: dict, context: dict[str, Any]) -> bool:
        """
        Evaluate a logic tree against a specific track context.
        
        context: {
            "track": _TrackProxy,
            "rule_id": int,
            "rule_cfg": dict,
            "zone_id": int,
            "zone_count": int
        }
        """
        if not logic_tree:
            # Fallback for old behavior-only rules
            return self._evaluate_legacy(context)

        operator = logic_tree.get("operator", "AND").upper()
        conditions = logic_tree.get("conditions", [])

        if operator == "AND":
            for cond in conditions:
                if not self._evaluate_node(cond, context):
                    return False
            return True

        if operator == "OR":
            for cond in conditions:
                if self._evaluate_node(cond, context):
                    return True
            return False

        if operator == "NOT":
            # Assume NOT has exactly one child condition
            if not conditions:
                return True
            return not self._evaluate_node(conditions[0], context)

        return False

    def _evaluate_node(self, node: dict, context: dict[str, Any]) -> bool:
        """Evaluate a single node (operator or leaf condition)."""
        if "operator" in node:
            return self.evaluate(node, context)

        cond_type = node.get("type")
        params = node.get("params", {})
        
        result = False
        if cond_type == "time":
            rule_id = context["rule_id"]
            result = self._schedule_mgr.is_active(rule_id)

        elif cond_type == "space":
            # If zone_id 0 or missing, use the rule's primary zone
            target_zone_id = params.get("zone_id", 0)
            if target_zone_id == 0:
                target_zone_id = context["zone_id"]
                
            track = context["track"]
            result = self._zone_mgr.is_inside(target_zone_id, track.centroid)

        elif cond_type == "object":
            track = context["track"]
            target_class = params.get("class")
            
            # Handle 'nan' or null labels from AI
            current_label = str(track.label).lower()
            
            if target_class:
                # Special case: if AI says 'nan' but we are looking for 'person',
                # and it's a person-sized object, we might want to trigger anyway.
                # For now, let's just log and allow case-insensitive match.
                if current_label == "nan" or current_label == "none":
                    logger.warning(f"Detection label is '{current_label}' for track {track.id}. Check AI model/lighting.")
                    # Fallback: if we expect a person and get nan, treat as potential match for safety
                    if target_class.lower() == "person":
                        result = True
                    else:
                        result = False
                else:
                    result = current_label == target_class.lower()
            else:
                result = True # No class filter
            
            if result:
                target_conf = params.get("confidence", 0.0)
                result = track.confidence >= target_conf
        
        elif cond_type == "behavior":
            behavior_type = params.get("type", context["rule_cfg"].get("behavior"))
            behavior = BEHAVIOR_REGISTRY.get(behavior_type)
            if behavior:
                eval_config = {**context["rule_cfg"], **params}
                eval_config["zone_count"] = context.get("zone_count", 0)
                eval_res = behavior.evaluate(
                    track=context["track"],
                    rule_id=context["rule_id"],
                    zone_id=params.get("zone_id", context["zone_id"]),
                    zone_manager=self._zone_mgr,
                    dwell_tracker=self._dwell,
                    config=eval_config
                )
                result = eval_res.triggered

        if not result:
            logger.debug(f"Condition FAILED: {cond_type} | Params: {params} | Rule: {context['rule_id']}")
        
        return result

    def _evaluate_legacy(self, context: dict[str, Any]) -> bool:
        """Evaluates rules that don't have the new 'logic' tree (backward compatibility)."""
        # Original RuleEngine logic: Behavior only
        node = {
            "type": "behavior",
            "params": {
                "type": context["rule_cfg"].get("behavior")
            }
        }
        return self._evaluate_node(node, context)
