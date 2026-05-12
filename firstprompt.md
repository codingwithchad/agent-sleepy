# First-session prompt for Claude Code

Paste this into Claude Code after it has read CLAUDE.md and ROADMAP.md. It tells Claude exactly what to do for the first work session — no more, no less.

---

## Prompt

Read `CLAUDE.md` and `ROADMAP.md` first. Confirm you understand the stack and the Phase 0 / Phase 1 exit criteria before writing any code.

Today's goal is **finish Phase 0 and start Phase 1**. Specifically:

**Phase 0 — repo skeleton:**

1. Initialize the project with `uv init` (Python 3.11+). Use `src/sleepy/` layout as described in CLAUDE.md.
2. Create the directory structure: `src/sleepy/{ingest,models,store,analyze,coach,jobs}/`, each with an empty `__init__.py`. Also create `tests/` mirroring it, and `scripts/` and `data/` at the repo root.
3. Add a `.gitignore` covering: `.env`, `data/`, `__pycache__/`, `.venv/`, `*.db`, `.pytest_cache/`, `.ruff_cache/`.
4. Add dependencies via `uv add`: `garminconnect`, `pydantic`, `python-dotenv`. Add dev deps via `uv add --dev`: `pytest`, `ruff`.
5. Create `.env.example` with placeholder lines for `GARMIN_EMAIL`, `GARMIN_PASSWORD`, `ANTHROPIC_API_KEY` (commented note that the last one isn't used until Phase 3).
6. Write a one-paragraph `README.md`: what this is, how to install (`uv sync`), how to copy `.env.example` to `.env` and fill it in.
7. Verify `uv run python -c "import sleepy"` succeeds and `uv run pytest` passes (zero tests is fine).

**Phase 1 — start the Garmin ingestion (just the data path, no LLM):**

8. Create `src/sleepy/models/sleep.py` with a `GarminSleepNight` Pydantic v2 model matching the fields in ROADMAP Phase 1. Make `date` a `datetime.date`, make timestamps `datetime` in UTC, durations `int` (minutes). Optional fields where Garmin might not always return them.
9. Create `src/sleepy/ingest/garmin.py` with a `fetch_sleep_nights(days: int = 7) -> list[GarminSleepNight]` function. Read credentials from `.env` via `python-dotenv`. Authenticate with `garminconnect`, fetch sleep data, parse each night into the Pydantic model. Handle the case where a night is missing (didn't wear it) by skipping, not raising.
10. **Stop there.** Do not write the storage layer or the cron job yet. I want to run `fetch_sleep_nights()` interactively and look at the data before committing to a schema.

**Rules for this session:**

- Make small commits. One commit for the skeleton, one for the model, one for the ingest function.
- After step 9, print a `uv run python -c "from sleepy.ingest.garmin import fetch_sleep_nights; import json; print(json.dumps([n.model_dump(mode='json') for n in fetch_sleep_nights(7)], indent=2, default=str))"` example I can run to inspect real data.
- If `garminconnect` has changed its API and the examples in its README don't match what's installed, stop and ask me — don't guess at method names.
- If the Garmin response has fields I haven't accounted for in `GarminSleepNight`, list them at the end of your response so I can decide whether to add them.

Before you start: list the steps you're about to take in order, flag anything ambiguous, and wait for me to say go.