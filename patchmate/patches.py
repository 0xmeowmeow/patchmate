"""Patches: small groups formed after the party from private "see again" marks.

Each guest marks people they met: AGAIN, NOT, or nothing (neutral). Marks are
never shown to anyone. A patch only forms where nobody has marked anybody else
in it NOT, and everyone in it has at least one mutual AGAIN inside it, so
nobody lands in a group where no one wanted them.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum

from .models import Guest, shared_connections


class Feeling(str, Enum):
    AGAIN = "again"
    NOT = "not"


Marks = dict[tuple[str, str], Feeling]  # (from, about) -> feeling; missing means neutral


@dataclass
class Patch:
    id: str
    members: list[str]


def _blocked(a: Guest, b: Guest, marks: Marks) -> bool:
    return (marks.get((a.id, b.id)) is Feeling.NOT
            or marks.get((b.id, a.id)) is Feeling.NOT
            or not shared_connections(a, b))


def _mutual(a: str, b: str, marks: Marks) -> bool:
    return marks.get((a, b)) is Feeling.AGAIN and marks.get((b, a)) is Feeling.AGAIN


def _warmth(a: str, b: str, marks: Marks) -> int:
    """2 for a mutual AGAIN, 1 for one-way, 0 for neutral."""
    return (marks.get((a, b)) is Feeling.AGAIN) + (marks.get((b, a)) is Feeling.AGAIN)


def form_patches(guests: list[Guest], marks: Marks, max_size: int = 4) -> list[Patch]:
    """Greedily grow groups from the warmest mutual pairs. Each guest joins at most one patch."""
    by_id = {g.id: g for g in guests}
    free = set(by_id)
    pairs = sorted(
        ((a.id, b.id) for i, a in enumerate(guests) for b in guests[i + 1:]
         if _mutual(a.id, b.id, marks) and not _blocked(a, b, marks))
    )
    patches = []
    for a, b in pairs:
        if a not in free or b not in free:
            continue
        members = [a, b]
        free -= {a, b}
        while len(members) < max_size:
            options = [
                c for c in sorted(free)
                if not any(_blocked(by_id[c], by_id[m], marks) for m in members)
                and any(_mutual(c, m, marks) for m in members)
            ]
            if not options:
                break
            best = max(options, key=lambda c: sum(_warmth(c, m, marks) for m in members))
            members.append(best)
            free.discard(best)
        pid = hashlib.sha1("|".join(sorted(members)).encode()).hexdigest()[:10]
        patches.append(Patch(pid, members))
    return patches
