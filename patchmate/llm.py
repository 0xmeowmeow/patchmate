"""Thin client for the Meta Model API (OpenAI-compatible), plus a fake for tests."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Protocol

BASE_URL = "https://api.meta.ai/v1"
SPARK = "muse-spark-1.3"


def load_env(path: Path = Path(__file__).resolve().parent.parent / ".env") -> None:
    """Read KEY=value lines from the repo's .env (git-ignored) without overriding the shell."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


class LLM(Protocol):
    def json(self, system: str, user: str) -> dict: ...


class MetaLLM:
    def __init__(self, model: str = SPARK, api_key: str | None = None):
        from openai import OpenAI

        load_env()
        self.model = model
        self.client = OpenAI(base_url=BASE_URL, api_key=api_key or os.environ["MODEL_API_KEY"])

    def json(self, system: str, user: str) -> dict:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
        )
        return parse_json(resp.choices[0].message.content or "")


class FakeLLM:
    """Returns canned replies in order, and records what it was asked."""

    def __init__(self, *replies: dict):
        self.replies = list(replies)
        self.calls: list[tuple[str, str]] = []

    def json(self, system: str, user: str) -> dict:
        self.calls.append((system, user))
        return self.replies.pop(0)


def parse_json(text: str) -> dict:
    """Parse a JSON object, tolerating code fences or prose around it."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise
        return json.loads(match.group(0))
