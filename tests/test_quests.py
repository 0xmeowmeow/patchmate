import pytest

from patchmate.llm import FakeLLM
from patchmate.matching import Board
from patchmate.models import Connection, Guest, Quest
from patchmate.quests import assign, quests_for_all, write_clue


def guests():
    return [
        Guest("a", "Moth", find_me_for="just got back from Japan", nervous_about="crowds"),
        Guest("b", "Lantern", find_me_for="I keep bees"),
        Guest("c", "Owl"),
        Guest("d", "Fox", find_me_for="ask me about startups", open_to={Connection.PROFESSIONAL}),
    ]


def test_clue_uses_only_the_offer():
    llm = FakeLLM({"ok": True, "clue": "Find someone fresh back from Japan"})
    assert write_clue(llm, guests()[0]) == "Find someone fresh back from Japan"
    _, user = llm.calls[0]
    assert "Japan" in user
    assert "crowds" not in user and "Moth" not in user


def test_no_offer_means_no_call_and_no_quest():
    llm = FakeLLM()
    assert write_clue(llm, guests()[2]) is None
    assert llm.calls == []


def test_model_can_refuse_an_offer():
    assert write_clue(FakeLLM({"ok": False, "clue": "x"}), guests()[1]) is None


def test_assign_spreads_and_respects_connection_types():
    gs = guests()
    quests = assign(gs, {"a": "Find Japan", "b": "Find bees", "d": "Find startups"})
    by_seeker = {q.seeker: q for q in quests}
    assert by_seeker["a"].target == "b" and by_seeker["b"].target == "a"
    assert by_seeker["c"].target in {"a", "b"}
    assert all(q.target != "d" and q.seeker != "d" for q in quests)
    assert all(q.seeker != q.target for q in quests)


def test_quests_for_all():
    llm = FakeLLM({"ok": True, "clue": "Japan"}, {"ok": True, "clue": "bees"},
                  {"ok": True, "clue": "startups"})
    assert len(quests_for_all(llm, guests())) == 3


def board():
    b = Board()
    for g in guests():
        b.add_guest(g)
    b.add_quest(Quest("q1", "Find someone fresh back from Japan", "c", "a", "comet"))
    return b


def test_seeker_sees_clue_target_sees_word():
    b = board()
    assert b.quests_for("c") == ["Find someone fresh back from Japan"]
    assert b.sought("a") == [("Find someone fresh back from Japan", "comet")]
    assert b.quests_for("a") == [] and b.sought("c") == []


def test_complete_needs_the_word():
    b = board()
    assert not b.complete("c", "q1", "moth")
    assert b.complete("c", "q1", " Comet ")
    assert b.quests_for("c") == [] and b.sought("a") == []


def test_only_the_seeker_completes():
    with pytest.raises(ValueError):
        board().complete("a", "q1", "comet")


def test_no_quest_without_shared_connection():
    with pytest.raises(ValueError):
        board().add_quest(Quest("q2", "Find startups", "c", "d", "fern"))


def test_words_never_match_a_nickname():
    gs = [Guest(w, w.title(), find_me_for="x") for w in ["moth", "lantern", "comet"]]
    for _ in range(50):
        for q in assign(gs, {g.id: "clue" for g in gs}):
            assert q.word not in {"moth", "lantern", "comet"}
