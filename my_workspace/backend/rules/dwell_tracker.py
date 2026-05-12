"""DwellTracker — accumulates dwell time per (rule_id, track_id) pair."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class DwellEntry:
    first_seen: float = field(default_factory=time.monotonic)
    last_seen: float = field(default_factory=time.monotonic)

    @property
    def dwell_seconds(self) -> float:
        return self.last_seen - self.first_seen

    def touch(self) -> None:
        self.last_seen = time.monotonic()


_STALE_SECONDS = 10.0   # remove entry if not seen for this long


class DwellTracker:
    """
    Tracks how long each object (track_id) has been inside each rule zone.

    Key: (rule_id, track_id)
    Value: DwellEntry with first_seen / last_seen timestamps

    Call enter() when object enters zone, touch() each frame, exit() on leave.
    """

    def __init__(self) -> None:
        self._entries: dict[tuple[int, int], DwellEntry] = {}

    def has_entry(self, rule_id: int, track_id: int) -> bool:
        return (rule_id, track_id) in self._entries

    def enter(self, rule_id: int, track_id: int) -> None:
        key = (rule_id, track_id)
        if key not in self._entries:
            self._entries[key] = DwellEntry()

    def touch(self, rule_id: int, track_id: int) -> float:
        """Update last_seen and return current dwell time in seconds."""
        key = (rule_id, track_id)
        if key not in self._entries:
            self._entries[key] = DwellEntry()
        entry = self._entries[key]
        entry.touch()
        return entry.dwell_seconds

    def get_dwell(self, rule_id: int, track_id: int) -> float:
        entry = self._entries.get((rule_id, track_id))
        return entry.dwell_seconds if entry else 0.0

    def exit(self, rule_id: int, track_id: int) -> None:
        self._entries.pop((rule_id, track_id), None)

    def remove_track(self, track_id: int) -> None:
        """Remove all entries for a track_id (called when track is lost)."""
        stale = [k for k in self._entries if k[1] == track_id]
        for k in stale:
            self._entries.pop(k, None)

    def purge_stale(self) -> int:
        """Remove entries not touched recently. Returns count removed."""
        now = time.monotonic()
        stale = [k for k, v in self._entries.items()
                 if now - v.last_seen > _STALE_SECONDS]
        for k in stale:
            self._entries.pop(k, None)
        return len(stale)

    def __len__(self) -> int:
        return len(self._entries)
