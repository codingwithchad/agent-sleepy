# ROADMAP.md

A phased plan for `agent-sleepy`. Phases are not dated — they're done when their exit criteria are met. The point is to ship a working thing at the end of every phase, not to build the whole vision before showing anything.

---

## Phase 0 — Repo skeleton

Goal: clean, boring foundation. No agent yet. No data yet.

- [ ] `uv init` project, Python 3.11+
- [ ] Directory structure per CLAUDE.md
- [ ] `.gitignore` covers `.env`, `data/`, `__pycache__`, `.venv`, `*.db`
- [ ] `pyproject.toml` with deps: `garminconnect`, `pydantic`, `python-dotenv`, `anthropic` (placeholder, not used yet), `pytest`, `ruff`
- [ ] `README.md` with one paragraph of what this is and how to run it
- [ ] `.env.example` with `GARMIN_EMAIL`, `GARMIN_PASSWORD`, `ANTHROPIC_API_KEY` placeholders
- [ ] First commit pushed

**Exit:** `uv run python -c "import sleepy"` succeeds. Empty test suite passes.

---

## Phase 1 — Garmin ingestion

Goal: reliably pull last night's sleep into a local database. Just data. No analysis, no LLM.

- [ ] `GarminSleepNight` Pydantic model with fields: date, sleep_start_utc, sleep_end_utc, duration_min, score, deep_min, light_min, rem_min, awake_min, avg_hrv, avg_respiration, restless_moments, sleep_latency_min
- [ ] `ingest/garmin.py` — authenticates via `garminconnect`, pulls last N nights, returns `list[GarminSleepNight]`
- [ ] `store/db.py` — opens SQLite at `data/sleepy.db`, creates `sleep_nights` table with `UNIQUE(date)` constraint
- [ ] `store/sleep.py` — `upsert_night()` and `get_nights(since=...)` functions
- [ ] `jobs/ingest_sleep.py` — entrypoint: pull last 7 nights, upsert into db, print summary
- [ ] Tests for the Pydantic model (round-trip from a real Garmin response fixture) and for upsert idempotency
- [ ] Cron entry or systemd timer documented in README (`0 9 * * * uv run python -m sleepy.jobs.ingest_sleep`)
- [ ] Run it daily for at least 7 days against real data

**Exit:** `select count(*) from sleep_nights` shows 7+ rows after a week, all populated, no duplicates. You can show someone a SQL query and the answer is your sleep.

**Blog post:** "Here's what a week of my Garmin sleep data actually looks like." Include a chart.

---

## Phase 2 — Manual behavior logger

Goal: capture the upstream variables Garmin doesn't know about. This is the input side of "why was sleep bad."

- [ ] `BehaviorEvent` Pydantic model: timestamp_utc, kind (enum: caffeine, alcohol, last_meal, workout_end, magnesium, stretching, screen_off, in_bed, stress_event), value (optional float, e.g. mg of caffeine), note (optional str)
- [ ] `store/behavior.py` — `log_event()`, `get_events(date=...)`
- [ ] `scripts/log.py` — a dead-simple CLI: `uv run log caffeine 200`, `uv run log alcohol 1`, `uv run log workout_end`, `uv run log in_bed`. Timestamps default to now.
- [ ] Optionally: a Shortcuts entry on phone that POSTs to a tiny local endpoint, or a Telegram bot. Defer unless CLI proves annoying.
- [ ] Log religiously for two weeks. The agent is worthless without this data.

**Exit:** You have at least 14 days of paired sleep + behavior data. You can run a SQL query joining them.

**Blog post:** "The eight buttons that capture 90% of what wrecks my sleep."

---

## Phase 3 — First coach message (LLM enters)

Goal: a single, scheduled morning message that ties last night's sleep to yesterday's behavior, with personality.

- [ ] `analyze/daily_context.py` — given a date, return a `DailyContext` Pydantic object with last night's sleep + yesterday's behavior events, ready to feed an LLM
- [ ] `coach/prompts.py` — system prompt that defines the coach's voice (the "no-bullshit but wants you to succeed" tone from the vision doc). Keep it in code, version-controlled, iterable.
- [ ] `coach/messages.py` — `generate_morning_message(context: DailyContext) -> CoachMessage`. Uses Anthropic API. Output is a Pydantic model with `headline`, `body`, `tomorrow_suggestion`.
- [ ] `jobs/morning_report.py` — entrypoint: build context for today, generate message, print to stdout (Phase 3) or push notification (Phase 3.5)
- [ ] Notification delivery: start with email via a simple SMTP send, or Pushover, or `ntfy.sh`. Pick the one that takes 20 minutes.
- [ ] Persist every generated message to a `coach_messages` table so you can review them and iterate the prompt

**Exit:** For 7 consecutive mornings, you get a message that references specific facts from your data ("score 71, you had coffee at 3:42pm, classic"). At least one of them made you laugh or annoyed you enough to change behavior. Save those.

**Blog post:** "Week one of being roasted by my own code." Show real messages.

---

## Phase 4 — Correlation, not just narration

Goal: stop relying on the LLM to "notice" patterns. Compute them in plain code, hand the LLM the conclusions.

- [ ] `analyze/correlations.py` — for each behavior kind, compute the average sleep score delta on days with/without it. Simple group-by, no ML.
- [ ] Special case: "caffeine after time T" — sweep T from noon to 5pm and find the cutoff where impact becomes significant. This is the kind of result that's blog-worthy.
- [ ] Surface top three personal correlations in the morning message context. The coach now says "your sleep is 14 points lower on days you have caffeine after 2pm" with real numbers from *your* data.
- [ ] Weekly Sunday-evening reflection job: longer message summarizing the week, top patterns, what to try next week.

**Exit:** The agent knows something about you that you didn't already know. You can name the thing.

**Blog post:** "What 30 days of logging taught me (and the agent) about my sleep."

---

## Phase 5 — Proactive, not just reactive

Goal: the agent intervenes *before* the bad behavior, not after. This is where it becomes a claw.

- [ ] Afternoon caffeine watch: scheduled 2pm job, checks calendar for late meetings (Phase 6 will integrate calendar; for now, just the time of day). If correlations show late caffeine hurts your sleep, pre-emptively send "heads up, don't reach for the Celsius at 3."
- [ ] Evening wind-down nag: 30 min before your typical bedtime. If magnesium/stretching not logged, nag.
- [ ] Post-late-workout note: if workout logged after 7pm, push a message about tomorrow's expected HRV hit.
- [ ] Anti-spam: dedupe so the same nag doesn't fire twice in a day. Track delivered messages in db.

**Exit:** The agent has caught you in the act and stopped you from doing something dumb at least three times. Each one is a blog moment.

**Blog post:** "The day my agent stopped me from drinking a Celsius."

---

## Phase 6 — Calendar context

Goal: the agent knows your schedule and uses it.

- [ ] Google Calendar ingestion (or whatever you use)
- [ ] Stress proxy: count meetings, flag back-to-back blocks, identify "after this meeting you'll want caffeine"
- [ ] Bedtime target adjusts to next day's first commitment
- [ ] Workout reschedule suggestion based on calendar + recovery

**Exit:** Agent has rescheduled or suggested rescheduling something based on real data.

---

## Phase 7 — Pick an agent framework, deliberately

Goal: the architecture has outgrown plain cron + scripts.

Only enter this phase when you've actually felt the pain. Candidates: LangGraph, an OpenClaw-style runtime, or rolling your own state machine. Decision criteria documented in a `decisions/` ADR.

Defer this until at least Phase 5 is shipped and you've felt the limits of cron jobs.

---

## Beyond

- Vision-based logging (snap a photo of a drink, agent infers caffeine load)
- Pantry/fridge awareness
- Workout swap automation (actually book the stretching class)
- Migrate from Garmin to Oura for nighttime comfort + better API
- Multi-goal support (add weight loss, add running training)

These are explicitly out of scope until earlier phases are real.

---

## Anti-goals

Things this project is **not** trying to be:

- A product. No users but you. No auth, no signup, no billing.
- A research project. Statistics are simple group-bys, not LLM-driven causal inference.
- A general health platform. It's a sleep agent first. Scope creep is the enemy.
- Beautiful. The CLI can be ugly. The push notification can be plain text. Functionality before polish.