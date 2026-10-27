import pytest

from patchmate.llm import FakeLLM
from patchmate.models import Guest
from patchmate.topics import add_openers, decide, find_audience, join, leave, post_topic

SLOTS = ["Sat arvo", "Sun morning"]


def pool():
    return [
        Guest("p", "Moth", curious_about="tardigrades"),
        Guest("a", "Lantern", curious_about="life on Mars"),
        Guest("b", "Owl", excited_about="microscopes", nervous_about="groups"),
        Guest("c", "Fox", curious_about="football"),
    ]


def topic():
    llm = FakeLLM({"ok": True, "invite": "Could tardigrades survive on Mars?", "place": "library"})
    return post_topic(llm, pool()[0], "tardigrades in space", "Civic", SLOTS)


def test_post_tidies_the_invite_and_counts_the_poster_in():
    t = topic()
    assert t.invite == "Could tardigrades survive on Mars?" and t.place == "library"
    assert t.interested == {"p": set(SLOTS)}


def test_unsafe_or_dating_posts_are_refused():
    llm = FakeLLM({"ok": False, "invite": "x"})
    assert post_topic(llm, pool()[0], "looking for a girlfriend", "Civic", SLOTS) is None


def test_audience_is_known_ids_only_and_names_stay_out():
    t = topic()
    llm = FakeLLM({"ids": ["a", "b", "zz", "p", "a"]})
    assert find_audience(llm, t, pool()) == ["a", "b"]
    _, user = llm.calls[0]
    assert "Lantern" not in user and "groups" not in user


def test_meetup_needs_three_and_picks_the_best_slot():
    t = topic()
    find_audience(FakeLLM({"ids": ["a", "b", "c"]}), t, pool())
    join(t, "a", ["Sun morning"])
    assert decide(t) is None
    join(t, "b", ["Sun morning", "Sat arvo"])
    m = decide(t)
    assert m.slot == "Sun morning" and m.people == ["p", "a", "b"]
    leave(t, "a")
    assert decide(t) is None


def test_uninvited_and_bad_times_are_rejected():
    t = topic()
    with pytest.raises(ValueError):
        join(t, "c", ["Sat arvo"])
    find_audience(FakeLLM({"ids": ["c"]}), t, pool())
    with pytest.raises(ValueError):
        join(t, "c", ["Tuesday 3am"])


def test_openers():
    t = topic()
    find_audience(FakeLLM({"ids": ["a", "b"]}), t, pool())
    join(t, "a", SLOTS)
    join(t, "b", SLOTS)
    m = add_openers(FakeLLM({"openers": ["What would you bring to Mars?", ""]}), t, decide(t))
    assert m.openers == ["What would you bring to Mars?"]
