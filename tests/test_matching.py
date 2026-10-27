import pytest

from patchmate.matching import Board
from patchmate.models import Audience, Card, Connection, Guest, may_record


def guests():
    return [
        Guest("a", "Moth", curious_about="why fungi glow", nervous_about="knowing nobody",
              open_to={Connection.CONVERSATION, Connection.ROMANCE}),
        Guest("b", "Lantern", curious_about="bioluminescent paint",
              open_to={Connection.CONVERSATION}),
        Guest("c", "Owl", curious_about="startups", open_to={Connection.PROFESSIONAL}),
    ]


def board():
    b = Board()
    for g in guests():
        b.add_guest(g)
    b.add_card(Card("q1", "What would it take to paint with living light?", ("a", "b"), why="glow"))
    return b


def test_match_needs_both_marks():
    b = board()
    assert b.mark("a", "q1") is None
    assert b.mark("b", "q1").id == "q1"
    assert [c.id for c in b.matches()] == ["q1"]


def test_unmark_undoes_interest():
    b = board()
    b.mark("a", "q1")
    b.unmark("a", "q1")
    assert b.mark("b", "q1") is None


def test_deck_shows_text_only_to_the_pair():
    b = board()
    assert b.deck("a") == ["What would it take to paint with living light?"]
    assert b.deck("c") == []


def test_cannot_mark_someone_elses_card():
    b = board()
    with pytest.raises(ValueError):
        b.mark("c", "q1")


def test_no_card_without_shared_connection_type():
    b = board()
    with pytest.raises(ValueError):
        b.add_card(Card("q2", "?", ("a", "c")))


def test_nervous_is_never_shown_beyond_the_agent():
    a = guests()[0]
    a.share_with_host = True
    assert "nervous_about" in a.visible_to(Audience.AGENT)
    assert "nervous_about" not in a.visible_to(Audience.HOST)
    assert a.visible_to(Audience.GUESTS) == {}


def test_host_sees_nothing_without_consent():
    assert guests()[1].visible_to(Audience.HOST) == {}


def test_recording_needs_everyone():
    a, b, _ = guests()
    a.allow_recording = True
    assert not may_record([a, b])
    b.allow_recording = True
    assert may_record([a, b])
    assert not may_record([])
