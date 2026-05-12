# CLAUDE.md

Operating instructions for Claude Code working in this repo. Read this first, every session.

## What this project is

`agent-sleepy` is a personal, proactive sleep-improvement agent. It pulls data from the owner's Garmin (and eventually other sources), correlates upstream behaviors (caffeine, alcohol, late workouts, late meals, stress) with sleep outcomes (score, HRV, latency, wake-ups, deep/REM), and proactively nags, warns, and coaches the owner with attitude. It is *not* a chatbot. It runs in the background and decides on its own when to speak up.

The owner is building this in the open as a learning project and content series, so code should be **readable first, clever second**. Future-me reading the diff six months from now is the primary audience.

## Stack

- **Language:** Python 3.11+
- **Package manager:** `uv` (not pip, not poetry — use `uv add`, `uv run`, `uv sync`)
- **Data validation:** Pydantic v2 for every external data boundary (API responses, LLM outputs, config)
- **Storage:** SQLite via `sqlite3` stdlib for Phase 1. Do not introduce Postgres, DuckDB, or an ORM until there is a concrete reason and it is discussed first.
- **Garmin access:** `garminconnect` (unofficial). Credentials live in `.env`, never committed.
- **LLM:** Anthropic API via `anthropic` SDK. Model: `claude-sonnet-4-5` by default. Do not hardcode model strings in business logic — they live in `config.py`.
- **Agent runtime:** Plain Python + cron / systemd timers for Phase 1. LangGraph or a claw-style runtime is on the roadmap but **do not add it until Phase 3**. Most of the agent is plain code; the LLM is a tool, not the architecture.
- **Tests:** `pytest`. Every Pydantic schema gets a round-trip test. Every tool function gets at least one happy-path test.
- **Lint/format:** `ruff` for both. Run before declaring work done.

## Repo conventions

- `src/sleepy/` — all importable code
- `src/sleepy/ingest/` — pulling data from sources (Garmin, manual logger, etc.)
- `src/sleepy/models/` — Pydantic schemas only. No logic.
- `src/sleepy/store/` — SQLite read/write. Pure data layer.
- `src/sleepy/analyze/` — correlation, pattern detection, plain Python statistics.
- `src/sleepy/coach/` — LLM-facing code. Prompt assembly, message generation.
- `src/sleepy/jobs/` — entrypoints meant to be run by cron (e.g. `morning_report.py`).
- `scripts/` — one-off scripts. Throwaway is fine. Don't import from `src/sleepy/` into other repos.
- `tests/` mirrors `src/sleepy/`.
- `data/` — gitignored. Local SQLite db lives at `data/sleepy.db`.

## Hard rules

1. **Never commit secrets.** Garmin credentials, Anthropic API keys, anything in `.env` — `.gitignore` it before writing it.
2. **Never write to the database from inside an LLM call.** The LLM produces structured output (Pydantic), the calling code decides what to persist. This boundary is non-negotiable.
3. **Pydantic at every boundary.** Garmin returns dicts; immediately parse into a `GarminSleepNight` model. The LLM returns text; parse into a `CoachMessage` model with `response_format` enforcement. Internal code should never be passing raw dicts around.
4. **No mock data in committed code.** If a test needs a fixture, put it in `tests/fixtures/` as a JSON file. Do not inline fake sleep data in source.
5. **Be honest about what works.** If something is half-done, mark it `# TODO` with a short note. Don't pretend incomplete code is finished. The owner is going to write blog posts about this code and lies in comments make for bad posts.
6. **Idempotent jobs.** Any job that runs on a schedule (morning report, nightly ingest) must be safe to run twice. Either dedupe on insert or use `INSERT OR REPLACE` with a natural key.
7. **Time zones.** Store all timestamps as UTC ISO 8601 in the database. Convert to the owner's local time (`America/Los_Angeles`) only at the presentation layer.

## What "done" looks like for a feature

- Code is written, formatted (`ruff format`), and lint-clean (`ruff check`).
- Tests pass (`uv run pytest`).
- If it's user-facing behavior, the owner has actually run it end-to-end against real data, not just unit tests.
- ROADMAP.md is updated if a phase exit criterion was hit.
- A short note exists somewhere (commit message is fine) about *why* the change was made, not just what.

## Things to not do without asking first

- Add a web framework (FastAPI, Flask, etc.). The agent runs on a schedule; it doesn't need a server yet.
- Add a frontend. CLI output and push notifications are the interface for Phase 1–2.
- Introduce LangChain, LlamaIndex, or any agent framework. Phase 3 will pick one deliberately.
- Use vector databases or embeddings. Not needed for what this does.
- Add a second LLM provider. One model, one provider, until there's a reason.
- Refactor across multiple modules in one commit. Small commits, please.

## When you (Claude) are unsure

Ask. The owner would rather answer one clarifying question than review a 400-line PR that solved the wrong problem.