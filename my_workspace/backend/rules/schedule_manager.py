"""ScheduleManager — time-based rule activation."""

from __future__ import annotations

import json
from datetime import datetime, time, timezone


def is_rule_active(schedule_json: str | None, now: datetime | None = None) -> bool:
    """
    Check if a rule is active at the given time.

    Schedule JSON format:
        {"start": "22:00", "end": "06:00", "days": [0,1,2,3,4,5,6]}

    - days: 0=Mon … 6=Sun (Python weekday convention)
    - start > end means overnight (e.g. 22:00–06:00)
    - None schedule → always active
    """
    if schedule_json is None:
        return True

    if now is None:
        now = datetime.now(timezone.utc)

    try:
        sched = json.loads(schedule_json)
    except (json.JSONDecodeError, TypeError):
        return True   # malformed → fail open (always active)

    days = sched.get("days")
    if days is not None and now.weekday() not in days:
        return False

    start_str = sched.get("start")
    end_str = sched.get("end")
    if not start_str or not end_str:
        return True

    start = _parse_time(start_str)
    end = _parse_time(end_str)
    current = now.time().replace(tzinfo=None)

    if start <= end:
        return start <= current <= end
    else:
        # Overnight: active if current >= start OR current <= end
        return current >= start or current <= end


def _parse_time(t_str: str) -> time:
    h, m = t_str.split(":")
    return time(int(h), int(m))


class ScheduleManager:
    """Cache schedule JSON per rule_id for quick lookup."""

    def __init__(self) -> None:
        self._schedules: dict[int, str | None] = {}

    def update(self, rule_id: int, schedule_json: str | None) -> None:
        self._schedules[rule_id] = schedule_json

    def remove(self, rule_id: int) -> None:
        self._schedules.pop(rule_id, None)

    def is_active(self, rule_id: int, now: datetime | None = None) -> bool:
        return is_rule_active(self._schedules.get(rule_id), now)
