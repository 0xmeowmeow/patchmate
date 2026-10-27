#!/usr/bin/env python3
"""CGI entry for DreamHost while Passenger is off. Every request goes through Flask."""

import os
import sys

HOME = os.path.join(os.environ.get("HOME") or os.path.expanduser("~"), "patchmate.meow-meow.io")
INTERP = os.path.join(HOME, "venv", "bin", "python3")
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

sys.path.insert(0, os.path.join(HOME, "app"))
os.environ.setdefault("PATCHMATE_DATA", os.path.join(HOME, "data"))
os.environ.setdefault("PATCHMATE_ENV", os.path.expanduser("~/.config/patchmate/env"))
os.environ["SCRIPT_NAME"] = ""  # URLs are /tap, not /app.cgi/tap

from wsgiref.handlers import CGIHandler  # noqa: E402

from patchmate.web import app  # noqa: E402

CGIHandler().run(app)
