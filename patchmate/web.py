"""The Patchmate web app. Run locally with `flask --app patchmate.web run`."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, redirect, render_template, request

DATA = Path(os.environ.get("PATCHMATE_DATA", Path(__file__).resolve().parent.parent / "data"))


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def home():
        return render_template("index.html", via=request.args.get("via", ""))

    @app.get("/tap")
    def tap():
        """The permanent link on the NFC implant. Counts the tap, then goes wherever is current."""
        DATA.mkdir(parents=True, exist_ok=True)
        with open(DATA / "taps.log", "a") as f:
            f.write(datetime.now(timezone.utc).isoformat(timespec="seconds") + "\n")
        return redirect(os.environ.get("TAP_TARGET", "/?via=tap"))

    @app.get("/healthz")
    def healthz():
        return "ok"

    return app


app = create_app()
