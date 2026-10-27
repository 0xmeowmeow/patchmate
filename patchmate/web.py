"""The Patchmate web app. Run locally with `flask --app patchmate.web run`."""

from __future__ import annotations

import io
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from flask import (Flask, abort, g, jsonify, redirect, render_template, request, send_file,
                   url_for)

from .models import Connection
from .party import ensure_quest, knit, welcome
from .patches import Feeling
from .store import Store

DATA = Path(os.environ.get("PATCHMATE_DATA", Path(__file__).resolve().parent.parent / "data"))

CONNECTIONS = [  # (value, label) in the order guests see them
    (Connection.CONVERSATION, "Good conversation"),
    (Connection.FRIENDSHIP, "New friends"),
    (Connection.COLLABORATION, "Making something together"),
    (Connection.EXPLORING, "Someone to explore things with"),
    (Connection.MENTORING, "Mentoring, either way"),
    (Connection.PROFESSIONAL, "Work and professional"),
    (Connection.ROMANCE, "Romance"),
]
RESCUE_AFTER = 20 * 60  # seconds before a guest with no connections shows up for the host


def create_app(llm_factory=None) -> Flask:
    app = Flask(__name__)

    def llm():
        if "llm" not in g:
            if llm_factory:
                g.llm = llm_factory()
            else:
                from .llm import MetaLLM
                g.llm = MetaLLM()
        return g.llm

    def store() -> Store:
        if "store" not in g:
            DATA.mkdir(parents=True, exist_ok=True)
            g.store = Store(DATA / "patchmate.db")
        return g.store

    @app.teardown_appcontext
    def close(_exc):
        if "store" in g:
            g.store.close()

    def event_or_404(code: str):
        ev = store().event(code)
        if not ev:
            abort(404)
        return ev

    def me(code: str):
        token = request.cookies.get(f"pm_{code}")
        row = store().by_token(token) if token else None
        return row if row and row["event"] == code else None

    def me_or_join(code: str):
        row = me(code)
        if not row:
            abort(redirect(url_for("join_form", code=code)))
        return row

    @app.get("/")
    def home():
        return render_template("index.html", via=request.args.get("via", ""))

    @app.get("/tap")
    def tap():
        """The permanent link on the NFC implant. Counts the tap, then goes wherever is current."""
        DATA.mkdir(parents=True, exist_ok=True)
        with open(DATA / "taps.log", "a") as f:
            f.write(datetime.now(timezone.utc).isoformat(timespec="seconds") + "\n")
        if target := os.environ.get("TAP_TARGET"):
            return redirect(target)
        ev = store().current_event()
        if ev:
            return redirect(url_for("join_form", code=ev["code"], via="tap"))
        return redirect("/?via=tap")

    @app.get("/healthz")
    def healthz():
        return "ok"

    # joining

    @app.get("/e/<code>")
    def join_form(code):
        ev = event_or_404(code)
        if me(code):
            return redirect(url_for("me_page", code=code))
        return render_template("join.html", ev=ev, connections=CONNECTIONS,
                               via=request.args.get("via", ""))

    @app.post("/e/<code>/join")
    def join(code):
        event_or_404(code)
        f = request.form
        if not f.get("nickname", "").strip() or not f.get("consent"):
            return redirect(url_for("join_form", code=code))
        open_to = {Connection(v) for v in f.getlist("open_to")
                   if v in {c.value for c in Connection}} or {Connection.CONVERSATION}
        expect = f.get("expect", "")
        gid, token = store().add_guest(
            code, open_to, bool(f.get("share_with_host")),
            int(expect) if expect.isdigit() else None,
            **{k: f.get(k, "") for k in ("nickname", "spot_me", "curious_about",
                                         "excited_about", "find_me_for", "nervous_about")})
        welcome(store(), llm(), code, gid)
        resp = redirect(url_for("me_page", code=code))
        resp.set_cookie(f"pm_{code}", token, max_age=60 * 60 * 24 * 30, httponly=True,
                        samesite="Lax", secure=request.is_secure)
        return resp

    # the guest's page

    @app.get("/e/<code>/me")
    def me_page(code):
        ev = event_or_404(code)
        row = me_or_join(code)
        s = store()
        ensure_quest(s, code, row["id"])
        return render_template(
            "me.html", ev=ev, me=row, deck=s.deck(row["id"]), matches=s.matches(row["id"]),
            quest=s.open_quest(row["id"]),
            found=sum(1 for q in s.quests_by(row["id"]) if q["done"]),
            sought=s.sought(row["id"]), flash=request.args.get("m", ""))

    @app.get("/e/<code>/state")
    def state(code):
        """A small fingerprint the page polls, so it only reloads when something changed."""
        row = me_or_join(code)
        s = store()
        return jsonify(cards=len(s.deck(row["id"])), matches=len(s.matches(row["id"])),
                       sought=len(s.sought(row["id"])), quest=bool(s.open_quest(row["id"])))

    @app.post("/e/<code>/mark/<card>")
    def mark(code, card):
        row = me_or_join(code)
        try:
            store().toggle_mark(row["id"], card)
        except ValueError:
            abort(403)
        return redirect(url_for("me_page", code=code) + f"#c-{card}")

    @app.post("/e/<code>/more")
    def more(code):
        row = me_or_join(code)
        added = knit(store(), llm(), code, row["id"])
        return redirect(url_for("me_page", code=code, m="more" if added else "nomore") + "#deck")

    @app.post("/e/<code>/quest")
    def quest(code):
        row = me_or_join(code)
        ok = store().complete_quest(row["id"], request.form.get("word", ""))
        return redirect(url_for("me_page", code=code, m="found" if ok else "wrong") + "#quest")

    # before you go

    @app.route("/e/<code>/again", methods=["GET", "POST"])
    def again(code):
        ev = event_or_404(code)
        row = me_or_join(code)
        s = store()
        met = s.met(row["id"])
        if request.method == "POST":
            for other in met:
                v = request.form.get(f"f_{other['id']}", "")
                s.set_feeling(row["id"], other["id"], Feeling(v) if v in ("again", "not") else None)
            had = request.form.get("had", "")
            if had.isdigit():
                s.set_had(row["id"], int(had))
            return redirect(url_for("again", code=code, saved=1))
        return render_template("again.html", ev=ev, me=row, met=met,
                               feelings=s.feelings_of(row["id"]),
                               saved=bool(request.args.get("saved")))

    @app.post("/e/<code>/forget")
    def forget(code):
        row = me_or_join(code)
        store().forget(row["id"])
        resp = redirect(url_for("home"))
        resp.delete_cookie(f"pm_{code}")
        return resp

    # the host

    @app.get("/e/<code>/host/<key>")
    def host(code, key):
        ev = event_or_404(code)
        if key != ev["host_key"]:
            abort(404)
        s = store()
        rows = s.db.execute("SELECT * FROM guests WHERE event = ? ORDER BY joined",
                            (code,)).fetchall()
        names = {r["id"]: r["nickname"] for r in rows}
        matches = s.all_matches(code)
        done = s.quests_done(code)
        connected = {m["a"] for m in matches} | {m["b"] for m in matches}
        connected |= {q["seeker"] for q in done} | {q["target"] for q in done}
        now = time.time()
        rescue = []
        for r in rows:
            if r["id"] in connected or now - r["joined"] < RESCUE_AFTER:
                continue
            cards = s.db.execute("SELECT * FROM cards WHERE a = ? OR b = ? ORDER BY created",
                                 (r["id"], r["id"])).fetchall()
            other_of = lambda c: c["b"] if c["a"] == r["id"] else c["a"]  # noqa: E731
            # Introduce them to someone already mingling if we can: they'll carry the moment.
            intro = next((c for c in cards if other_of(c) in connected), cards[0] if cards else None)
            rescue.append({"name": r["nickname"], "minutes": int((now - r["joined"]) / 60),
                           "other": names.get(other_of(intro)) if intro else None,
                           "why": intro["why"] if intro else ""})
        expects = [r["expect"] for r in rows if r["expect"] is not None]
        hads = [r["had"] for r in rows if r["had"] is not None]
        return render_template(
            "host.html", ev=ev, guests=rows, names=names, matches=matches, done=done,
            rescue=rescue, shared=[r for r in rows if r["share_with_host"]],
            expect=sum(expects) / len(expects) if expects else None,
            had=sum(hads) / len(hads) if hads else None, n_had=len(hads),
            join_url=url_for("join_form", code=code, _external=True))

    @app.get("/e/<code>/qr.svg")
    def qr(code):
        event_or_404(code)
        import segno
        buf = io.BytesIO()
        segno.make(url_for("join_form", code=code, _external=True), error="m").save(
            buf, kind="svg", scale=8, border=2, dark="#1d1b18", light="#ffffff")
        buf.seek(0)
        return send_file(buf, mimetype="image/svg+xml")

    return app


app = create_app()
