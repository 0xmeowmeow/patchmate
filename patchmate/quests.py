"""Quests: "find someone who just got back from Japan".

A quest gives a guest a reason to walk up to strangers. Searching means asking
several people, so one quest starts many conversations, not just the one at
the end. Clues are written only from what a guest offered to be found for.
"""

from __future__ import annotations

import hashlib
import secrets

from .llm import LLM
from .models import Guest, Quest, shared_connections

SYSTEM = """You turn something a party guest offered into a quest clue for other guests, \
like "Find someone who just got back from Japan".

Rules:
- use only what the guest offered; add nothing about them;
- never describe looks, clothes, costume, age, gender, job, or anything else that \
picks them out without talking to them; the seeker should have to ask around;
- keep it short, warm and a little playful;
- if the offer touches health, politics, money troubles or anything private, \
or would be awkward to be asked about in public, reply ok=false.

Reply as JSON: {"ok": true, "clue": "Find someone who ..."}"""

WORDS = [
    "moth", "lantern", "comet", "fern", "otter", "ember", "tide", "quartz",
    "maple", "heron", "nebula", "acorn", "kelp", "falcon", "lichen", "pebble",
]


def write_clue(llm: LLM, guest: Guest) -> str | None:
    """A clue for finding this guest, or None if they offered nothing usable."""
    offer = guest.find_me_for.strip()
    if not offer:
        return None
    reply = llm.json(SYSTEM, f"The guest offered to be found for: {offer}")
    clue = (reply.get("clue") or "").strip()
    return clue if reply.get("ok") and clue else None


def assign(guests: list[Guest], clues: dict[str, str], per_seeker: int = 1) -> list[Quest]:
    """Give each guest up to `per_seeker` quests, spreading the searching evenly.

    A guest never seeks themselves, and only seeks someone they share a
    connection type with. The least-sought targets are picked first.
    """
    sought = {t: 0 for t in clues}
    quests = []
    for seeker in guests:
        options = [t for t in clues if t != seeker.id
                   and shared_connections(seeker, _by_id(guests, t))]
        options.sort(key=lambda t: sought[t])
        for target in options[:per_seeker]:
            sought[target] += 1
            qid = hashlib.sha1(f"{seeker.id}->{target}".encode()).hexdigest()[:10]
            quests.append(Quest(qid, clues[target], seeker.id, target, secrets.choice(WORDS)))
    return quests


def quests_for_all(llm: LLM, guests: list[Guest], per_seeker: int = 1) -> list[Quest]:
    clues = {g.id: c for g in guests if (c := write_clue(llm, g))}
    return assign(guests, clues, per_seeker)


def _by_id(guests: list[Guest], gid: str) -> Guest:
    return next(g for g in guests if g.id == gid)
