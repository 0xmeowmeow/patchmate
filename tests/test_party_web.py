"""The party flow end to end, with a fake model."""

import re

import pytest

import patchmate.web as web
from patchmate.store import Store


class Model:
    """Answers clue and knitting calls well enough to drive the flow."""

    def json(self, system, user):
        if "quest clue" in system:
            return {"ok": True, "clue": "Find someone who " + user.split(": ", 1)[1]}
        return {"questions": [{"text": f"Question {hash(user) % 10**6}?", "why": "link"}]}


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(web, "DATA", tmp_path)
    ev = Store(tmp_path / "patchmate.db").create_event("Halloween")
    return web.create_app(llm_factory=Model), ev


def join(app, ev, nickname, **extra):
    c = app.test_client()
    data = {"nickname": nickname, "consent": "1", "expect": "2", "open_to": "conversation", **extra}
    r = c.post(f"/e/{ev['code']}/join", data=data)
    assert r.status_code == 302 and r.headers["Location"].endswith("/me")
    return c


def cards(c, ev):
    html = c.get(f"/e/{ev['code']}/me").get_data(as_text=True)
    return re.findall(r'id="c-([0-9a-f]+)"', html), html


def test_full_party(app):
    app, ev = app
    code = ev["code"]
    moth = join(app, ev, "Moth", spot_me="moth wings", find_me_for="just got back from Japan")
    lantern = join(app, ev, "Lantern", spot_me="paper lantern hat")

    (card,), html = cards(lantern, ev)
    assert "Find someone who just got back from Japan" in html  # Lantern's quest is Moth
    assert "Moth" not in html  # nobody is named before a match

    moth.post(f"/e/{code}/mark/{card}")
    assert "It's a match" not in cards(lantern, ev)[1]
    lantern.post(f"/e/{code}/mark/{card}")
    html = cards(lantern, ev)[1]
    assert "It's a match" in html and "Moth" in html and "moth wings" in html

    word = re.search(r'class="word">(\w+)<', cards(moth, ev)[1]).group(1)
    assert "m=wrong" in lantern.post(f"/e/{code}/quest", data={"word": "nope"}).headers["Location"]
    assert "m=found" in lantern.post(f"/e/{code}/quest", data={"word": word}).headers["Location"]

    page = lantern.get(f"/e/{code}/again").get_data(as_text=True)
    assert "Moth" in page
    store = Store(web.DATA / "patchmate.db")
    moth_id = store.db.execute("SELECT id FROM guests WHERE nickname='Moth'").fetchone()[0]
    lantern.post(f"/e/{code}/again", data={f"f_{moth_id}": "again", "had": "3"})
    lantern_id = store.db.execute("SELECT id FROM guests WHERE nickname='Lantern'").fetchone()[0]
    assert store.feelings_of(lantern_id)[moth_id].value == "again"

    host = app.test_client().get(f"/e/{code}/host/{ev['host_key']}").get_data(as_text=True)
    assert ">2</b>joined" in host and ">1</b>matches" in host and ">1</b>quests found" in host
    assert app.test_client().get(f"/e/{code}/host/wrong").status_code == 404


def test_cannot_mark_someone_elses_card_and_forget_deletes(app):
    app, ev = app
    code = ev["code"]
    join(app, ev, "A")
    b = join(app, ev, "B")
    c = join(app, ev, "C")
    b_cards = set(cards(b, ev)[0])
    c_cards = set(cards(c, ev)[0])
    only_b = (b_cards - c_cards).pop()
    assert c.post(f"/e/{code}/mark/{only_b}").status_code == 403
    c.post(f"/e/{code}/forget")
    assert Store(web.DATA / "patchmate.db").db.execute(
        "SELECT COUNT(*) FROM guests WHERE nickname='C'").fetchone()[0] == 0
    assert c.get(f"/e/{code}/me").status_code == 302


def test_join_needs_consent_and_tap_goes_to_current_event(app):
    app, ev = app
    c = app.test_client()
    r = c.post(f"/e/{ev['code']}/join", data={"nickname": "X"})
    assert r.headers["Location"].endswith(f"/e/{ev['code']}")
    assert c.get("/tap").headers["Location"].endswith(f"/e/{ev['code']}?via=tap")
    assert c.get(f"/e/{ev['code']}/qr.svg").mimetype == "image/svg+xml"
