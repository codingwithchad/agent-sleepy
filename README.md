# agent-sleepy

A proactive personal sleep-improvement agent. It pulls nightly sleep data from Garmin, correlates it with upstream behaviors (caffeine, alcohol, late workouts, meals), and runs on a schedule to nag, warn, and coach — with attitude. It is not a chatbot. You don't talk to it; it talks to you.

## Install

```bash
uv sync
cp .env.example .env
# fill in GARMIN_EMAIL and GARMIN_PASSWORD
```

## Run tests

```bash
uv run pytest
```

## Lint and format

```bash
uv run ruff check .
uv run ruff format .
```
