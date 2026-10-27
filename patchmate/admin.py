"""Event admin. On the server:

    cd ~/patchmate.meow-meow.io && PATCHMATE_DATA=data venv/bin/python3 -m patchmate.admin new "Halloween"
"""

from __future__ import annotations

import sys

from .web import DATA
from .store import Store

BASE = "https://patchmate.meow-meow.io"


def main(argv: list[str]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    store = Store(DATA / "patchmate.db")
    if argv[:1] == ["new"] and len(argv) == 2:
        ev = store.create_event(argv[1])
        print(f"event {ev['name']!r} is now current (the /tap link goes here)")
        print(f"  guests: {BASE}/e/{ev['code']}")
        print(f"  host:   {BASE}/e/{ev['code']}/host/{ev['host_key']}")
    elif argv[:1] == ["list"]:
        for ev in store.db.execute("SELECT * FROM events ORDER BY created"):
            n = store.db.execute("SELECT COUNT(*) FROM guests WHERE event = ?",
                                 (ev["code"],)).fetchone()[0]
            mark = "*" if ev["current"] else " "
            print(f"{mark} {ev['code']}  {ev['name']}  ({n} guests)")
    else:
        print(__doc__)
        print("commands: new NAME | list")


if __name__ == "__main__":
    main(sys.argv[1:])
