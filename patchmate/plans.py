"""After the party: plans for a patch, and a practical nudge when someone wants to bail.

The nudge is not therapy. It names the practical obstacle and solves it with
facts we hand the model (who offers lifts nearby, the plan's cost), never
with advice about feelings.
"""

from __future__ import annotations

from dataclasses import dataclass

from .llm import LLM
from .models import Audience, Guest

PLAN_SYSTEM = """You plan the next meetup for a small group who got on well at a party.

You get what each person is curious and excited about, and what they've already \
done a lot. Suggest activities that:
- sit where their interests overlap, so everyone has a reason to come;
- are new to all of them, so they discover it together instead of one person \
leading;
- happen somewhere public, cost little or nothing, and take one to three hours;
- give them something to do side by side, with time to talk.

Never reveal anything one person said to the others, and never mention private notes.
For each, write a short "hook": the shared open question they can chase while \
they're there.

Reply as JSON: {"plans": [{"activity": "...", "why": "...", "hook": "...", \
"cost": "free|low|some"}]}"""

NUDGE_SYSTEM = """Someone in a small friendly group is thinking of skipping a meetup. \
They told you what's stopping them. You are a practical helper, not a therapist.

- Name the practical obstacle: transport, cost, weather, energy, time, nerves, or other.
- Offer one concrete fix, using only the facts you're given (lifts on offer, the \
plan, the group). Never invent people, places or prices.
- Low-effort options are good: come for 30 minutes, ask for a lift, swap to an \
indoor spot, bring a friend.
- If it fits, draft a short, casual message they could send to the group.
- No advice about feelings, health or life. No guilt. Saying no is fine.
- If they mention self-harm, crisis or being unsafe, set "support": true and \
write nothing else.

Reply as JSON: {"obstacle": "...", "suggestion": "...", "message": "... or empty", \
"ask": "id of the person to ask, or empty", "support": false}"""

SUPPORT = ("That sounds like more than a missed meetup. Patchmate can't help with "
           "that, but Lifeline can, any time: call 13 11 14 or text 0477 13 11 14.")


@dataclass
class Plan:
    activity: str
    why: str
    hook: str
    cost: str


@dataclass
class Nudge:
    obstacle: str
    suggestion: str
    message: str = ""
    ask: str = ""  # guest id to ask, only ever someone from the lift list


def suggest_plans(llm: LLM, members: list[Guest], n: int = 3) -> list[Plan]:
    people = []
    for i, g in enumerate(members, 1):
        seen = g.visible_to(Audience.AGENT)
        people.append(
            f"Person {i}\n  curious about: {seen['curious_about'] or '(not said)'}\n"
            f"  excited about: {seen['excited_about'] or '(not said)'}\n"
            f"  already done a lot: {g.has_done or '(not said)'}"
        )
    reply = llm.json(PLAN_SYSTEM, "\n\n".join(people) + f"\n\nSuggest {n} plans.")
    return [
        Plan(p.get("activity", "").strip(), p.get("why", "").strip(),
             p.get("hook", "").strip(), p.get("cost", "").strip())
        for p in reply.get("plans", [])[:n] if p.get("activity")
    ]


def lifts_for(who: Guest, members: list[Guest]) -> list[Guest]:
    """Others in the patch who offer lifts from the same rough area."""
    return [m for m in members if m.id != who.id and m.offers_lifts
            and m.area and m.area.lower() == who.area.lower()]


def nudge(llm: LLM, who: Guest, objection: str, members: list[Guest], plan: Plan) -> Nudge:
    lifts = lifts_for(who, members)
    facts = [
        f"The plan: {plan.activity} (cost: {plan.cost or 'unknown'})",
        f"Group size: {len(members)}",
        "Lifts on offer from their area: "
        + (", ".join(f"{m.nickname} (id {m.id})" for m in lifts) or "none"),
        f"What's stopping them: {objection}",
    ]
    reply = llm.json(NUDGE_SYSTEM, "\n".join(facts))
    if reply.get("support"):
        return Nudge("support", SUPPORT)
    ask = (reply.get("ask") or "").strip()
    return Nudge(
        (reply.get("obstacle") or "other").strip(),
        (reply.get("suggestion") or "").strip(),
        (reply.get("message") or "").strip(),
        ask if ask in {m.id for m in lifts} else "",
    )
