"""Topics: "I'd love to talk about X" becomes a small meetup, with no organiser needed.

The agent does the parts that stop people organising things: finding who
else cares, picking a time that suits, choosing a public place, and calling
it off kindly if not enough people can come. Invitees see the topic, never
who posted it, until the meetup is confirmed.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass, field

from .llm import LLM
from .models import Audience, Guest

POST_SYSTEM = """Someone wants to meet a few people to talk about a topic. Turn their words \
into a short, warm invitation that makes others want to come.

- Keep their topic; make it specific and inviting, one or two sentences.
- Say nothing about the person who posted it.
- Suggest a kind of public place that suits it (cafe, library, park, pub, museum...).
- Reply ok=false for anything hateful, selling something, seeking a date, or \
unsafe to meet strangers about.

Reply as JSON: {"ok": true, "invite": "...", "place": "..."}"""

AUDIENCE_SYSTEM = """Pick people likely to enjoy a meetup about a topic, from what they \
are curious and excited about. Prefer real overlap over vague fit. Return only ids \
from the list, best first.

Reply as JSON: {"ids": ["..."]}"""

OPENERS_SYSTEM = """A small group of strangers is meeting to talk about a topic. Write \
opening questions that each person could answer from their own angle, that build \
on each other, and that get the group talking to each other, not to a leader.

Reply as JSON: {"openers": ["...", "..."]}"""


@dataclass
class Topic:
    id: str
    poster: str
    invite: str
    place: str
    area: str
    slots: list[str]                # times on offer, e.g. "Sat 2 Nov, afternoon"
    min_people: int = 3             # strangers never meet one to one
    max_people: int = 6
    interested: dict[str, set[str]] = field(default_factory=dict)  # guest -> slots they can do
    invited: list[str] = field(default_factory=list)


@dataclass
class Meetup:
    topic_id: str
    slot: str
    people: list[str]
    openers: list[str] = field(default_factory=list)


def post_topic(llm: LLM, poster: Guest, text: str, area: str, slots: list[str]) -> Topic | None:
    reply = llm.json(POST_SYSTEM, f"Their topic: {text}")
    invite = (reply.get("invite") or "").strip()
    if not reply.get("ok") or not invite or not slots:
        return None
    tid = hashlib.sha1(f"{poster.id}|{text}".encode()).hexdigest()[:10]
    topic = Topic(tid, poster.id, invite, (reply.get("place") or "cafe").strip(), area, slots)
    topic.interested[poster.id] = set(slots)
    return topic


def find_audience(llm: LLM, topic: Topic, pool: list[Guest], n: int = 12) -> list[str]:
    """Who to show the invitation to. Names never reach the model."""
    others = [g for g in pool if g.id != topic.poster]
    lines = []
    for g in others:
        seen = g.visible_to(Audience.AGENT)
        lines.append(f"id {g.id}: curious about {seen['curious_about'] or '-'}; "
                     f"excited about {seen['excited_about'] or '-'}")
    reply = llm.json(AUDIENCE_SYSTEM, f"Topic: {topic.invite}\n\nPeople:\n" + "\n".join(lines))
    known = {g.id for g in others}
    picked = [i for i in dict.fromkeys(str(i) for i in reply.get("ids", [])) if i in known][:n]
    topic.invited = picked
    return picked


def join(topic: Topic, guest_id: str, slots: list[str]) -> None:
    if guest_id != topic.poster and guest_id not in topic.invited:
        raise ValueError("only invited guests can join")
    ok = set(slots) & set(topic.slots)
    if not ok:
        raise ValueError("pick at least one of the offered times")
    topic.interested[guest_id] = ok


def leave(topic: Topic, guest_id: str) -> None:
    topic.interested.pop(guest_id, None)


def decide(topic: Topic) -> Meetup | None:
    """The best-attended slot, if enough people can make it. Earlier joiners keep their place."""
    counts = Counter(s for slots in topic.interested.values() for s in slots)
    best = [s for s in topic.slots if counts[s] >= topic.min_people]
    if not best:
        return None
    slot = max(best, key=lambda s: counts[s])
    people = [g for g, slots in topic.interested.items() if slot in slots][:topic.max_people]
    return Meetup(topic.id, slot, people)


def add_openers(llm: LLM, topic: Topic, meetup: Meetup, n: int = 3) -> Meetup:
    reply = llm.json(OPENERS_SYSTEM, f"Topic: {topic.invite}\nGroup size: {len(meetup.people)}\n"
                                     f"Write {n} openers.")
    meetup.openers = [o.strip() for o in reply.get("openers", [])[:n] if o and o.strip()]
    return meetup
