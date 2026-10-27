# Patchmate

An AI that introduces people through questions, not profiles.

You never see who you might meet. You see questions that you could only answer together with someone else. Mark the ones that excite you. If the other person marks the same one, you're patched through. Nothing is recorded unless everyone in the conversation says yes. The AI's job is to get people talking, then get out of the way.

AI is the knitting needles. People are the threads.

Built in public for the [Meta Global AI Developer Hackathon](https://cerebralvalley.ai/e/meta-ai-developer-hackathon) (27 Oct – 4 Nov 2026), indie track. First field test: a Halloween party in Canberra, 31 October 2026.

## Principles

- **Questions, never profiles.** Matching is double-blind. Nobody can browse or size up other people.
- **Consent defaults to off.** Sharing and recording are opt-in, per person and per interaction.
- **Private stays private.** Some answers (like what someone is nervous about) only help the AI be kind. They're never shown to anyone.
- **The AI steps back.** Success is measured in time people spend with each other, not with the app.

## Status

Day 1. Nothing in this repository existed before the hackathon started; see [PRIOR-WORK.md](PRIOR-WORK.md).

## Running it

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pytest                       # tests use a fake model, no API key needed
export MODEL_API_KEY=...               # Meta Model API key
.venv/bin/python -m patchmate.demo     # generate questions for a few sample guests
```
