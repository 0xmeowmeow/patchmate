"""SQLite storage for one or more events. CGI starts a fresh process per request,
so everything the party needs lives here, not in memory.
"""

from __future__ import annotations

import json
import secrets
import sqlite3
import time
from pathlib import Path

from .models import Card, Connection, Guest
from .patches import Feeling, Marks

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  code TEXT PRIMARY KEY, name TEXT NOT NULL, host_key TEXT NOT NULL,
  current INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS guests (
  id TEXT PRIMARY KEY, event TEXT NOT NULL, token TEXT UNIQUE NOT NULL,
  nickname TEXT NOT NULL, spot_me TEXT, curious_about TEXT, excited_about TEXT,
  find_me_for TEXT, nervous_about TEXT, open_to TEXT, share_with_host INTEGER,
  expect INTEGER, had INTEGER, joined REAL NOT NULL);
CREATE TABLE IF NOT EXISTS cards (
  id TEXT PRIMARY KEY, event TEXT NOT NULL, a TEXT NOT NULL, b TEXT NOT NULL,
  text TEXT NOT NULL, why TEXT, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS marks (card TEXT NOT NULL, guest TEXT NOT NULL,
  PRIMARY KEY (card, guest));
CREATE TABLE IF NOT EXISTS clues (guest TEXT PRIMARY KEY, clue TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS quests (
  id TEXT PRIMARY KEY, event TEXT NOT NULL, seeker TEXT NOT NULL, target TEXT NOT NULL,
  clue TEXT NOT NULL, word TEXT NOT NULL, done REAL);
CREATE TABLE IF NOT EXISTS feelings (src TEXT NOT NULL, about TEXT NOT NULL,
  feeling TEXT NOT NULL, PRIMARY KEY (src, about));
"""

GUEST_FIELDS = ("nickname", "spot_me", "curious_about", "excited_about", "find_me_for",
                "nervous_about")


class Store:
    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(path, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)

    def close(self) -> None:
        self.db.close()

    # events

    def create_event(self, name: str, current: bool = True) -> sqlite3.Row:
        code, key = secrets.token_hex(3), secrets.token_urlsafe(12)
        with self.db:
            if current:
                self.db.execute("UPDATE events SET current = 0")
            self.db.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?)",
                            (code, name, key, int(current), time.time()))
        return self.event(code)

    def event(self, code: str) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM events WHERE code = ?", (code,)).fetchone()

    def current_event(self) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM events WHERE current = 1").fetchone()

    # guests

    def add_guest(self, event: str, open_to: set[Connection], share_with_host: bool,
                  expect: int | None, **fields: str) -> tuple[str, str]:
        gid, token = secrets.token_hex(4), secrets.token_urlsafe(24)
        values = [fields.get(f, "").strip()[:300] for f in GUEST_FIELDS]
        with self.db:
            self.db.execute(
                "INSERT INTO guests (id, event, token, nickname, spot_me, curious_about,"
                " excited_about, find_me_for, nervous_about, open_to, share_with_host,"
                " expect, joined) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (gid, event, token, *values, json.dumps(sorted(c.value for c in open_to)),
                 int(share_with_host), expect, time.time()))
        return gid, token

    def row(self, gid: str) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM guests WHERE id = ?", (gid,)).fetchone()

    def by_token(self, token: str) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM guests WHERE token = ?", (token,)).fetchone()

    def guests(self, event: str) -> list[Guest]:
        rows = self.db.execute("SELECT * FROM guests WHERE event = ? ORDER BY joined", (event,))
        return [to_guest(r) for r in rows]

    def set_had(self, gid: str, had: int) -> None:
        with self.db:
            self.db.execute("UPDATE guests SET had = ? WHERE id = ?", (had, gid))

    def forget(self, gid: str) -> None:
        """Delete a guest and everything that mentions them."""
        with self.db:
            cards = [r[0] for r in self.db.execute(
                "SELECT id FROM cards WHERE a = ? OR b = ?", (gid, gid))]
            self.db.executemany("DELETE FROM marks WHERE card = ?", [(c,) for c in cards])
            self.db.execute("DELETE FROM marks WHERE guest = ?", (gid,))
            self.db.execute("DELETE FROM cards WHERE a = ? OR b = ?", (gid, gid))
            self.db.execute("DELETE FROM clues WHERE guest = ?", (gid,))
            self.db.execute("DELETE FROM quests WHERE seeker = ? OR target = ?", (gid, gid))
            self.db.execute("DELETE FROM feelings WHERE src = ? OR about = ?", (gid, gid))
            self.db.execute("DELETE FROM guests WHERE id = ?", (gid,))

    # question cards

    def add_cards(self, event: str, cards: list[Card]) -> None:
        with self.db:
            self.db.executemany(
                "INSERT OR IGNORE INTO cards VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(c.id, event, *c.pair, c.text, c.why, time.time()) for c in cards])

    def partners(self, gid: str) -> set[str]:
        """Guests who already share cards with this one."""
        rows = self.db.execute("SELECT a, b FROM cards WHERE a = ? OR b = ?", (gid, gid))
        return {r["b"] if r["a"] == gid else r["a"] for r in rows}

    def card_counts(self, event: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self.db.execute("SELECT a, b FROM cards WHERE event = ?", (event,)):
            for g in (r["a"], r["b"]):
                counts[g] = counts.get(g, 0) + 1
        return counts

    def deck(self, gid: str) -> list[sqlite3.Row]:
        """This guest's cards with whether they marked them. No hint of who the other is."""
        return self.db.execute(
            "SELECT c.id, c.text, EXISTS(SELECT 1 FROM marks m WHERE m.card = c.id"
            " AND m.guest = ?) AS marked FROM cards c WHERE c.a = ? OR c.b = ?"
            " ORDER BY c.created, c.id", (gid, gid, gid)).fetchall()

    def toggle_mark(self, gid: str, card_id: str) -> None:
        card = self.db.execute("SELECT a, b FROM cards WHERE id = ?", (card_id,)).fetchone()
        if not card or gid not in (card["a"], card["b"]):
            raise ValueError("not your card")
        with self.db:
            if self.db.execute("DELETE FROM marks WHERE card = ? AND guest = ?",
                               (card_id, gid)).rowcount == 0:
                self.db.execute("INSERT INTO marks VALUES (?, ?)", (card_id, gid))

    def matches(self, gid: str) -> list[sqlite3.Row]:
        """Cards both people marked, with the other person's nickname and how to spot them."""
        return self.db.execute(
            "SELECT c.id, c.text, o.id AS other, o.nickname, o.spot_me FROM cards c"
            " JOIN guests o ON o.id = CASE WHEN c.a = ? THEN c.b ELSE c.a END"
            " WHERE (c.a = ? OR c.b = ?)"
            " AND (SELECT COUNT(*) FROM marks m WHERE m.card = c.id) = 2",
            (gid, gid, gid)).fetchall()

    def all_matches(self, event: str) -> list[sqlite3.Row]:
        return self.db.execute(
            "SELECT c.* FROM cards c WHERE c.event = ?"
            " AND (SELECT COUNT(*) FROM marks m WHERE m.card = c.id) = 2", (event,)).fetchall()

    # quests

    def set_clue(self, gid: str, clue: str) -> None:
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO clues VALUES (?, ?)", (gid, clue))

    def clues(self, event: str) -> dict[str, str]:
        rows = self.db.execute("SELECT c.guest, c.clue FROM clues c JOIN guests g"
                               " ON g.id = c.guest WHERE g.event = ?", (event,))
        return {r["guest"]: r["clue"] for r in rows}

    def quests_by(self, gid: str) -> list[sqlite3.Row]:
        return self.db.execute("SELECT * FROM quests WHERE seeker = ? ORDER BY rowid",
                               (gid,)).fetchall()

    def open_quest(self, gid: str) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM quests WHERE seeker = ? AND done IS NULL",
                               (gid,)).fetchone()

    def sought(self, gid: str) -> list[sqlite3.Row]:
        return self.db.execute("SELECT * FROM quests WHERE target = ? AND done IS NULL",
                               (gid,)).fetchall()

    def sought_counts(self, event: str) -> dict[str, int]:
        rows = self.db.execute("SELECT target, COUNT(*) n FROM quests WHERE event = ?"
                               " GROUP BY target", (event,))
        return {r["target"]: r["n"] for r in rows}

    def add_quest(self, event: str, seeker: str, target: str, clue: str, word: str) -> None:
        with self.db:
            self.db.execute("INSERT INTO quests VALUES (?, ?, ?, ?, ?, ?, NULL)",
                            (secrets.token_hex(5), event, seeker, target, clue, word))

    def complete_quest(self, gid: str, word: str) -> bool:
        q = self.open_quest(gid)
        if not q or word.strip().lower() != q["word"]:
            return False
        with self.db:
            self.db.execute("UPDATE quests SET done = ? WHERE id = ?", (time.time(), q["id"]))
        return True

    def quests_done(self, event: str) -> list[sqlite3.Row]:
        return self.db.execute("SELECT * FROM quests WHERE event = ? AND done IS NOT NULL",
                               (event,)).fetchall()

    # after the party

    def met(self, gid: str) -> list[sqlite3.Row]:
        """Everyone this guest matched with or found (or was found by) on a quest."""
        ids = {m["other"] for m in self.matches(gid)}
        for r in self.db.execute("SELECT seeker, target FROM quests WHERE done IS NOT NULL"
                                 " AND (seeker = ? OR target = ?)", (gid, gid)):
            ids.add(r["target"] if r["seeker"] == gid else r["seeker"])
        ids.discard(gid)
        return [r for r in (self.row(i) for i in sorted(ids)) if r]

    def set_feeling(self, src: str, about: str, feeling: Feeling | None) -> None:
        with self.db:
            if feeling is None:
                self.db.execute("DELETE FROM feelings WHERE src = ? AND about = ?", (src, about))
            else:
                self.db.execute("INSERT OR REPLACE INTO feelings VALUES (?, ?, ?)",
                                (src, about, feeling.value))

    def feelings_of(self, src: str) -> dict[str, Feeling]:
        rows = self.db.execute("SELECT about, feeling FROM feelings WHERE src = ?", (src,))
        return {r["about"]: Feeling(r["feeling"]) for r in rows}

    def marks(self, event: str) -> Marks:
        rows = self.db.execute("SELECT f.* FROM feelings f JOIN guests g ON g.id = f.src"
                               " WHERE g.event = ?", (event,))
        return {(r["src"], r["about"]): Feeling(r["feeling"]) for r in rows}


def to_guest(r: sqlite3.Row) -> Guest:
    return Guest(
        r["id"], r["nickname"], curious_about=r["curious_about"] or "",
        excited_about=r["excited_about"] or "", nervous_about=r["nervous_about"] or "",
        find_me_for=r["find_me_for"] or "", spot_me=r["spot_me"] or "",
        open_to={Connection(c) for c in json.loads(r["open_to"] or "[]")} or {Connection.CONVERSATION},
        share_with_host=bool(r["share_with_host"]),
    )
