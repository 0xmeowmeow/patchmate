from patchmate.llm import FakeLLM, parse_json
from patchmate.models import Connection, Guest
from patchmate.questions import questions_for_all, questions_for_pair


def pair():
    return (
        Guest("a", "Moth", curious_about="why some fungi glow", nervous_about="knowing nobody"),
        Guest("b", "Lantern", excited_about="painting with light"),
    )


def test_cards_come_from_the_reply_and_keep_the_hidden_link():
    llm = FakeLLM({"questions": [{"text": "Could you paint with a fungus?", "why": "glow + paint"}]})
    [card] = questions_for_pair(llm, *pair())
    assert card.text == "Could you paint with a fungus?"
    assert card.why == "glow + paint"
    assert card.pair == ("a", "b")


def test_prompt_marks_the_private_note_and_hides_names():
    llm = FakeLLM({"questions": []})
    questions_for_pair(llm, *pair())
    _, user = llm.calls[0]
    assert "private note (never mention): knowing nobody" in user
    assert "Moth" not in user and "Lantern" not in user


def test_incompatible_pairs_are_never_sent_to_the_model():
    a, _ = pair()
    c = Guest("c", "Owl", open_to={Connection.PROFESSIONAL})
    llm = FakeLLM()
    assert questions_for_pair(llm, a, c) == []
    assert llm.calls == []


def test_all_pairs():
    a, b = pair()
    c = Guest("c", "Owl", curious_about="tides")
    llm = FakeLLM(*({"questions": [{"text": f"q{i}", "why": ""}]} for i in range(3)))
    assert len(questions_for_all(llm, [a, b, c])) == 3


def test_parse_json_tolerates_fences():
    assert parse_json('```json\n{"x": 1}\n```') == {"x": 1}
