# ROADMAP.md

A phased plan for `agent-sleepy`. Phases are not dated — they're done when their exit criteria are met. The point is to ship a working thing at the end of every phase, not to build the whole vision before showing anything.

---

## Phase 0 — Repo skeleton ✓

Goal: clean, boring foundation. No agent yet. No data yet.

- [x] `uv init` project, Python 3.11+
- [x] Directory structure per CLAUDE.md
- [x] `.gitignore` covers `.env`, `data/`, `__pycache__`, `.venv`, `*.db`
- [x] `pyproject.toml` with deps: `garminconnect`, `pydantic`, `python-dotenv`, `anthropic`, `pytest`, `ruff`
- [x] `README.md` with one paragraph of what this is and how to run it
- [x] `.env.example` with `GARMIN_EMAIL`, `GARMIN_PASSWORD`, `ANTHROPIC_API_KEY` placeholders
- [x] First commit pushed

**Exit:** `uv run python -c "import sleepy"` succeeds. Empty test suite passes. ✓

---

## Phase 1 — Garmin ingestion ✓

Goal: reliably pull last night's sleep into a local database. Just data. No analysis, no LLM.

- [x] `GarminSleepNight` + `SleepNight` Pydantic models (device-specific and canonical split)
- [x] `ingest/garmin.py` — authenticates, pulls last N nights of sleep, returns `list[GarminSleepNight]`
- [x] `store/sleep.py` — opens SQLite at `data/sleepy.db`, `sleep_nights` table with `PRIMARY KEY (date, source)` (supports future multi-device)
- [x] `store/sleep.py` — `upsert_nights()` and `get_nights()` with idempotent `INSERT OR REPLACE`
- [x] `jobs/nightly_ingest.py` — entrypoint: pull last N nights of sleep + activities, upsert both, print summary
- [x] Workout/activity ingestion added in Phase 1: `GarminActivity` + `Workout` models, `store/workout.py`, HR zone breakdown
- [x] Tests for models (round-trip) and store (upsert idempotency)
- [x] `config.py` — model names and timezone constants

- [ ] Cron entry set up and running daily (see HUMAN-TODO)
- [ ] 7+ nights confirmed in database with no duplicates

**Exit:** `select count(*) from sleep_nights` shows 7+ rows after a week, all populated, no duplicates. You can show someone a SQL query and the answer is your sleep.

**Blog post:** "Here's what a week of my Garmin sleep data actually looks like." Include a chart.

---

## Phase 2 — Behavior logger (in progress)

Goal: capture the upstream variables Garmin doesn't know about. This is the input side of "why was sleep bad."

The original plan was a CLI logger. We skipped straight to a Telegram bot + LLM parser because the computer is in a different room from the kitchen.

- [x] `FoodLog` Pydantic model: date, entry_type (meal/caffeine/alcohol/unknown), occurred_at_utc, caffeine_mg, alcohol_drinks, notes, raw_message
- [x] `store/food.py` — `insert_food_log()`, `get_food_logs_for_date()`
- [x] `coach/food_parser.py` — LLM-based natural language parser using Anthropic tool-use. Swappable function signature so it can be replaced with regex if tokens are scarce.
- [x] `jobs/telegram_bot.py` — Telegram bot: receive casual message → parse with LLM → store → confirm. Only responds to your user ID.
- [x] Herbal tea, alcohol, last meal, and caffeine all handled by the single `entry_type` field + notes

**Not yet covered** (add later if needed):
- [ ] Stretching / magnesium / screen-off / stress events — can be added to `entry_type` when the analysis shows they matter
- [ ] Log religiously for two weeks. The agent is worthless without this data.

**Planned expansion (not now):** See "Beyond" for food-detail logging — when you want to say "spaghetti with red sauce at 8pm" and have the agent correlate specific foods with outcomes like heartburn-related wakeups.

**Exit:** 14 days of paired sleep + behavior data. You can run a SQL query joining them.

**Blog post:** "The eight buttons that capture 90% of what wrecks my sleep." (Except ours is a Telegram bot and the buttons are just typing.)

---

## Phase 3 — First coach message (LLM enters)

Goal: a single, scheduled morning message that ties last night's sleep to yesterday's behavior, with personality.

- [ ] `analyze/daily_context.py` — given a date, return a `DailyContext` Pydantic object with last night's sleep + yesterday's food/behavior logs, ready to feed an LLM
- [ ] `coach/prompts.py` — system prompt that defines the coach's voice (no-bullshit but wants you to succeed). Version-controlled and iterable.
- [ ] `coach/messages.py` — `generate_morning_message(context: DailyContext) -> CoachMessage`. Uses Anthropic API. Output is a Pydantic model with `headline`, `body`, `tomorrow_suggestion`.
- [ ] `jobs/morning_report.py` — entrypoint: build context, generate message, print to stdout (Phase 3) or push (Phase 3.5)
- [ ] Notification delivery: start with Telegram (we already have the bot) — send the morning report to yourself via the same bot
- [ ] Persist every generated message to a `coach_messages` table for prompt iteration

**Exit:** For 7 consecutive mornings, you get a message that references specific facts from your data ("score 71, you had coffee at 3:42pm, classic"). At least one made you laugh or annoyed you enough to change behavior.

**Blog post:** "Week one of being roasted by my own code." Show real messages.

---

## Phase 4 — Correlation, not just narration

Goal: stop relying on the LLM to "notice" patterns. Compute them in plain code, hand the LLM the conclusions.

- [ ] `analyze/correlations.py` — for each behavior type, compute average sleep score delta on days with/without it. Simple group-by, no ML.
- [ ] Caffeine cutoff sweep: test time thresholds from noon to 5pm, find where impact becomes significant. Blog-worthy result.
- [ ] Surface top three personal correlations in the morning message context.
- [ ] Weekly Sunday-evening reflection job: longer message summarizing the week, top patterns, what to try next week.

**Exit:** The agent knows something about you that you didn't already know. You can name the thing.

**Blog post:** "What 30 days of logging taught me (and the agent) about my sleep."

---

## Phase 5 — Proactive, not just reactive

Goal: the agent intervenes *before* the bad behavior, not after.

- [ ] Afternoon caffeine watch: 2pm scheduled job. If correlations show late caffeine hurts your sleep, pre-emptively send a warning via Telegram.
- [ ] Evening wind-down nag: 30 min before typical bedtime. If no meal/herbal-tea logged, check in.
- [ ] Post-late-workout note: if workout ends after 7pm, push a message about expected HRV hit.
- [ ] Anti-spam: dedupe so the same nag doesn't fire twice. Track delivered messages in db.

**Exit:** The agent caught you in the act and stopped you from doing something dumb at least three times.

**Blog post:** "The day my agent stopped me from drinking a Celsius."

---

## Phase 6 — Calendar context

Goal: the agent knows your schedule and uses it.

- [ ] Google Calendar ingestion
- [ ] Stress proxy: count meetings, flag back-to-back blocks
- [ ] Bedtime target adjusts to next day's first commitment
- [ ] Workout reschedule suggestion based on calendar + recovery

**Exit:** Agent has rescheduled or suggested rescheduling something based on real data.

---

## Phase 7 — Pick an agent framework, deliberately

Goal: the architecture has outgrown plain cron + scripts.

Only enter this phase when you've actually felt the pain. Candidates: LangGraph, or rolling your own state machine. Decision criteria documented in a `decisions/` ADR.

Defer until Phase 5 is shipped and you've felt the limits of cron jobs.

---

## Beyond

- **Food detail logging:** Right now the food logger captures what category of thing you had and when. A future expansion would log specific foods (e.g. "spaghetti with red sauce at 8pm") and correlate them with specific outcomes (heartburn wakeups, digestion issues, HRV dips). The `notes` field and `FoodLog` schema are already set up for this — it's a parser prompt change + analysis expansion when ready.
- Vision-based logging (snap a photo of a meal, agent infers content)
- Herbal tea / hydration tracking already in Phase 2 via the food logger
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
