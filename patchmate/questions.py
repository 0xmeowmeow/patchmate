"""Write "questions for two": open loops neither person can close alone."""

from __future__ import annotations

import hashlib
import itertools
import json

from .llm import LLM
from .models import Audience, Card, Guest, shared_connections

SYSTEM = """You are the quiet matchmaker at a gathering. You never introduce people by \
who they are. You write questions.

You get what two guests are curious and excited about, plus a private note that is \
only for you. Write questions that:
- neither guest could answer alone, but the two of them could explore together, \
because each holds part of it;
- are open loops: specific, surprising, and fun to chase in a conversation at a party, \
not homework and not small talk;
- never reveal anything about either guest: no names, jobs, demographics, or details \
someone could use to identify them;
- never mention or hint at the private notes. Use them only to be gentle;
- stay away from politics, health and personal problems;
- are short: under 25 words, easy to read on a phone in a loud room.

Each question must make sense to either guest reading it alone.
Also write "why": one short sentence, for a human host, naming the hidden link \
between the two. It is never shown to the guests.

Reply as JSON: {"questions": [{"text": "...", "why": "..."}]}"""


def _describe(label: str, g: Guest) -> str:
    seen = g.visible_to(Audience.AGENT)
    return (
        f"Guest {label}\n"
        f"  curious about: {seen['curious_about'] or '(not said)'}\n"
        f"  excited about: {seen['excited_about'] or '(not said)'}\n"
        f"  private note (never mention): {seen['nervous_about'] or '(none)'}"
    )


def _card_id(pair: tuple[str, str], text: str) -> str:
    return hashlib.sha1(json.dumps([pair, text]).encode()).hexdigest()[:10]


def questions_for_pair(llm: LLM, a: Guest, b: Guest, n: int = 3) -> list[Card]:
    if not shared_connections(a, b):
        return []
    user = f"{_describe('A', a)}\n\n{_describe('B', b)}\n\nWrite {n} questions."
    reply = llm.json(SYSTEM, user)
    cards = []
    for q in reply.get("questions", [])[:n]:
        text = (q.get("text") or "").strip()
        if text:
            pair = (a.id, b.id)
            cards.append(Card(_card_id(pair, text), text, pair, (q.get("why") or "").strip()))
    return cards


def questions_for_all(llm: LLM, guests: list[Guest], n: int = 3) -> list[Card]:
    """Every compatible pair gets its own cards. Fine for a party; batch later for crowds."""
    cards = []
    for a, b in itertools.combinations(guests, 2):
        cards.extend(questions_for_pair(llm, a, b, n))
    return cards


def questions_for_many(llm: LLM, new: Guest, others: list[Guest], n: int = 2) -> list[Card]:
    """One call: questions pairing a new arrival with each of several guests already here."""
    others = [o for o in others if o.id != new.id and shared_connections(new, o)]
    if not others:
        return []
    labels = {f"P{i}": o for i, o in enumerate(others, 1)}
    people = "\n\n".join(_describe(label, o) for label, o in labels.items())
    user = (f"{_describe('A', new)}\n\nOthers already here:\n\n{people}\n\n"
            f"For each other guest, write {n} questions for A and that guest.\n"
            'Reply as JSON: {"pairs": [{"other": "P1", "questions": [{"text": "...", "why": "..."}]}]}')
    reply = llm.json(SYSTEM, user)
    cards = []
    for entry in reply.get("pairs", []):
        other = labels.get(str(entry.get("other", "")).strip())
        if not other:
            continue
        for q in entry.get("questions", [])[:n]:
            text = (q.get("text") or "").strip()
            if text:
                pair = (new.id, other.id)
                cards.append(Card(_card_id(pair, text), text, pair, (q.get("why") or "").strip()))
    return cards
