"""Guests, question cards and the consent rules around them."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Connection(str, Enum):
    """Kinds of connection a guest is open to. Never shown to anyone else.

    Romance and professional networking sit among the others so that neither
    is a separate box that people feel pressure to lie about.
    """

    CONVERSATION = "conversation"
    FRIENDSHIP = "friendship"
    COLLABORATION = "collaboration"
    EXPLORING = "exploring"          # someone to explore things with
    MENTORING = "mentoring"          # mentoring or being mentored
    PROFESSIONAL = "professional"
    ROMANCE = "romance"


class Audience(str, Enum):
    """Who may see a piece of a guest's information."""

    AGENT = "agent"   # only the AI, to be kind; never displayed
    HOST = "host"     # the human host's view
    GUESTS = "guests" # other guests (still never tied to a name before a match)


@dataclass
class Guest:
    id: str
    nickname: str
    curious_about: str = ""
    excited_about: str = ""
    nervous_about: str = ""  # always AGENT-only, see visible_to()
    open_to: set[Connection] = field(default_factory=lambda: {Connection.CONVERSATION})
    share_with_host: bool = False
    allow_recording: bool = False

    def visible_to(self, audience: Audience) -> dict[str, str]:
        """The parts of this guest an audience may see."""
        if audience is Audience.AGENT:
            return {
                "curious_about": self.curious_about,
                "excited_about": self.excited_about,
                "nervous_about": self.nervous_about,
            }
        if audience is Audience.HOST and self.share_with_host:
            return {"curious_about": self.curious_about, "excited_about": self.excited_about}
        return {}


def shared_connections(a: Guest, b: Guest) -> set[Connection]:
    """Connection types both guests are open to. Empty means never pair them."""
    return a.open_to & b.open_to


def may_record(guests: list[Guest]) -> bool:
    """Recording is allowed only if everyone in the interaction said yes."""
    return bool(guests) and all(g.allow_recording for g in guests)


@dataclass
class Card:
    """A question written for one pair, which neither can close alone.

    Guests see only `text`. The rest is for the agent and, with consent, the host.
    """

    id: str
    text: str
    pair: tuple[str, str]
    why: str = ""  # the hidden link between the two, used for host introductions
