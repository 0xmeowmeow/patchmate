"""DreamHost Passenger entry. Lives in the domain folder; the code is in ./app."""

import os
import sys

HOME = os.path.join(os.environ["HOME"], "patchmate.meow-meow.io")
INTERP = os.path.join(HOME, "venv", "bin", "python3")
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

sys.path.insert(0, os.path.join(HOME, "app"))
os.environ.setdefault("PATCHMATE_DATA", os.path.join(HOME, "data"))

from patchmate.web import app as application  # noqa: E402
