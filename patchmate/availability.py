"""An "I'm free" signal: you'd welcome a call or a catch-up, for a short while.

Signals are only shown to people you share a patch with. Strangers never see
who is free or where; with strangers, availability goes through topics
(see topics.py), so people find a subject, not a person.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Kind(str, Enum):
    CALL = "call"   # happy to take a call or a message
    MEET = "meet"   # up for a catch-up in person


@dataclass
class Signal:
    guest_id: str
    kind: Kind
    until: datetime
    area: str = ""  # only for MEET; rough area, never an address
    note: str = ""  # e.g. "walking the dog, call me"


@dataclass
class Availability:
    signals: dict[str, Signal] = field(default_factory=dict)  # one live signal per guest

    def signal(self, s: Signal) -> None:
        self.signals[s.guest_id] = s

    def clear(self, guest_id: str) -> None:
        self.signals.pop(guest_id, None)

    def open_now(self, viewer: str, circle: set[str], now: datetime) -> list[Signal]:
        """Live signals from people in the viewer's patches. Expired ones are dropped."""
        for gid in [g for g, s in self.signals.items() if s.until <= now]:
            del self.signals[gid]
        return [s for gid, s in self.signals.items() if gid in circle and gid != viewer]
