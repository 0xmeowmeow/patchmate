"""What happens at the party: joining, knitting question cards, and handing out quests."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from .llm import LLM
from .models import Guest, shared_connections
from .questions import questions_for_pair
from .quests import next_target, pick_word, write_clue
from .store import Store, to_guest

log = logging.getLogger(__name__)

PARTNERS = 3  # new people to pair with per knit; each is its own call, run in parallel


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
    with ThreadPoolExecutor(max_workers=PARTNERS) as pool:  # model calls only; sqlite stays here
        batches = list(pool.map(lambda o: _safe_pair(llm, me, o), others[:PARTNERS]))
    cards = [c for batch in batches for c in batch]
    store.add_cards(event, cards)
    return len(cards)


def _safe_pair(llm: LLM, a: Guest, b: Guest) -> list:
    try:
        return questions_for_pair(llm, a, b, n=2)
    except Exception:  # the party carries on without these cards
        log.exception("knitting failed")
        return []


def welcome(store: Store, llm: LLM, event: str, gid: str) -> None:
    """A new guest's clue and first cards, written at the same time so joining is quick."""
    guest = to_guest(store.row(gid))
    with ThreadPoolExecutor(max_workers=1) as pool:
        clue = pool.submit(_safe_clue, llm, guest)  # the model call only; sqlite stays on this thread
        knit(store, llm, event, gid)
        if text := clue.result():
            store.set_clue(gid, text)


def _safe_clue(llm: LLM, guest: Guest) -> str | None:
    try:
        return write_clue(llm, guest)
    except Exception:
        log.exception("clue failed")
        return None


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
