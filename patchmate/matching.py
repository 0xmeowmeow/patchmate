"""Double-blind matching: guests mark questions, never people."""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import Card, Guest, shared_connections


@dataclass
class Board:
    guests: dict[str, Guest] = field(default_factory=dict)
    cards: dict[str, Card] = field(default_factory=dict)
    marks: dict[str, set[str]] = field(default_factory=dict)  # card id -> guest ids

    def add_guest(self, guest: Guest) -> None:
        self.guests[guest.id] = guest

    def add_card(self, card: Card) -> None:
        a, b = (self.guests[i] for i in card.pair)
        if not shared_connections(a, b):
            raise ValueError(f"guests {card.pair} share no connection type")
        self.cards[card.id] = card

    def deck(self, guest_id: str) -> list[str]:
        """Question texts a guest is shown. No names, no hint of who else holds them."""
        return [c.text for c in self.cards.values() if guest_id in c.pair]

    def deck_cards(self, guest_id: str) -> list[Card]:
        return [c for c in self.cards.values() if guest_id in c.pair]

    def mark(self, guest_id: str, card_id: str) -> Card | None:
        """Record that a guest is excited by a card. Returns the card if it's now a match."""
        card = self.cards[card_id]
        if guest_id not in card.pair:
            raise ValueError("guests can only mark cards from their own deck")
        marked = self.marks.setdefault(card_id, set())
        marked.add(guest_id)
        return card if marked >= set(card.pair) else None

    def unmark(self, guest_id: str, card_id: str) -> None:
        self.marks.get(card_id, set()).discard(guest_id)

    def matches(self) -> list[Card]:
        return [self.cards[cid] for cid, who in self.marks.items() if who >= set(self.cards[cid].pair)]
