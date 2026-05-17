# agent-sleepy

A proactive personal sleep-improvement agent. It pulls nightly sleep and activity data from Garmin, correlates it with upstream behaviors (caffeine, alcohol, late workouts, meals, room environment), and runs on a schedule to nag, warn, and coach — with attitude. It is not a chatbot. You don't talk to it; it talks to you.

Built as a learning project and public content series. Code is readable first, clever second.

## Status

See [ROADMAP.md](ROADMAP.md) for the phased plan and current progress.

## Quick start (local dev)

```bash
# Requires Python 3.11+ and uv
uv sync
cp .env.example .env
# Edit .env — fill in GARMIN_EMAIL, GARMIN_PASSWORD, ANTHROPIC_API_KEY
```

Pull last 7 nights of sleep data:
```bash
uv run python -m sleepy.jobs.nightly_ingest --days 7
```

Start the Telegram food logger bot:
```bash
uv run python -m sleepy.jobs.telegram_bot
```

Run tests:
```bash
uv run pytest
```

Lint and format:
```bash
uv run ruff check .
uv run ruff format .
```

## Deploying to a Raspberry Pi (production)

See [SETUP.md](SETUP.md) for the full walkthrough: OS flash, SSH config, uv install, cron setup, and sensor wiring.

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `GARMIN_EMAIL` | Yes | Garmin Connect account email |
| `GARMIN_PASSWORD` | Yes | Garmin Connect account password |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key (food parser + coach) |
| `TELEGRAM_BOT_TOKEN` | Yes | Token from @BotFather |
| `TELEGRAM_USER_ID` | Yes | Your numeric Telegram user ID |

All of these live in `.env`. Never commit that file.

## Project layout

```
src/sleepy/
  ingest/     — pull data from Garmin and sensors
  models/     — Pydantic schemas only, no logic
  store/      — SQLite read/write
  analyze/    — correlation and pattern detection
  coach/      — LLM prompt assembly and message generation
  jobs/       — cron entrypoints (nightly_ingest, telegram_bot, etc.)
scripts/      — one-off and utility scripts
tests/        — mirrors src/sleepy/
data/         — gitignored; SQLite DB lives here
```
