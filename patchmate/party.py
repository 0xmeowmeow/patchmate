"""What happens at the party: joining, knitting question cards, and handing out quests."""

from __future__ import annotations

import logging

from .llm import LLM
from .models import Guest, shared_connections
from .questions import questions_for_many
from .quests import next_target, pick_word, write_clue
from .store import Store

log = logging.getLogger(__name__)

PARTNERS_PER_CALL = 4  # how many people one knitting call pairs a guest with


def knit(store: Store, llm: LLM, event: str, gid: str) -> int:
    """Write question cards between this guest and a few people they don't have cards with.

    The people with the fewest cards come first, so early arrivals and quiet
    guests keep getting new questions as the party fills up. Returns cards added.
    """
    guests = store.guests(event)
    me = next((g for g in guests if g.id == gid), None)
    if me is None:
        return 0
    have = store.partners(gid)
    counts = store.card_counts(event)
    others = [g for g in guests if g.id != gid and g.id not in have and shared_connections(me, g)]
    others.sort(key=lambda g: counts.get(g.id, 0))
    if not others:
        return 0
    try:
        cards = questions_for_many(llm, me, others[:PARTNERS_PER_CALL])
    except Exception:  # the party carries on without new cards
        log.exception("knitting failed")
        return 0
    store.add_cards(event, cards)
    return len(cards)


def add_clue(store: Store, llm: LLM, guest: Guest) -> None:
    try:
        clue = write_clue(llm, guest)
    except Exception:
        log.exception("clue failed")
        return
    if clue:
        store.set_clue(guest.id, clue)


def ensure_quest(store: Store, event: str, gid: str) -> None:
    """Give this guest a quest if they have none open and someone is findable."""
    if store.open_quest(gid):
        return
    guests = store.guests(event)
    me = next((g for g in guests if g.id == gid), None)
    if me is None:
        return
    done = {q["target"] for q in store.quests_by(gid)}
    clues = store.clues(event)
    target = next_target(me, guests, clues, store.sought_counts(event), avoid=done)
    if target:
        store.add_quest(event, gid, target, clues[target], pick_word(guests))
