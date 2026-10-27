from patchmate.llm import FakeLLM
from patchmate.models import Guest
from patchmate.plans import SUPPORT, Plan, lifts_for, nudge, suggest_plans


def patch():
    return [
        Guest("a", "Moth", curious_about="glowing fungi", has_done="lots of bushwalks",
              nervous_about="crowds", area="Belconnen"),
        Guest("b", "Lantern", excited_about="night photography", area="belconnen",
              offers_lifts=True),
        Guest("c", "Owl", curious_about="bats", area="Tuggeranong", offers_lifts=True),
    ]


PLAN = Plan("Night walk at the Botanic Gardens", "glow + night", "What glows and why?", "free")


def test_plans_come_back_and_names_and_private_notes_stay_out():
    llm = FakeLLM({"plans": [{"activity": "Night walk", "why": "w", "hook": "h", "cost": "free"},
                             {"activity": ""}]})
    [plan] = suggest_plans(llm, patch())
    assert plan.activity == "Night walk" and plan.cost == "free"
    _, user = llm.calls[0]
    assert "lots of bushwalks" in user
    assert "crowds" not in user and "Moth" not in user


def test_lifts_only_from_same_area_and_not_self():
    a, b, c = patch()
    assert lifts_for(a, patch()) == [b]
    assert lifts_for(b, patch()) == []


def test_nudge_offers_a_real_lift():
    llm = FakeLLM({"obstacle": "transport", "suggestion": "Ask Lantern for a lift",
                   "message": "Anyone driving from Belconnen?", "ask": "b"})
    n = nudge(llm, patch()[0], "can't afford a cab home", patch(), PLAN)
    assert (n.obstacle, n.ask) == ("transport", "b")
    _, user = llm.calls[0]
    assert "Lantern (id b)" in user and "Owl" not in user


def test_nudge_drops_a_made_up_lift():
    llm = FakeLLM({"obstacle": "transport", "suggestion": "Ask Owl", "ask": "c"})
    assert nudge(llm, patch()[0], "no way home", patch(), PLAN).ask == ""


def test_crisis_gets_a_signpost_not_a_nudge():
    llm = FakeLLM({"support": True, "suggestion": "come anyway"})
    n = nudge(llm, patch()[0], "...", patch(), PLAN)
    assert n.obstacle == "support" and n.suggestion == SUPPORT
