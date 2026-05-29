# SPRINT.md — Sprint 2 (May 28 – June 11, 2026)

Current state: Phase 1 (Garmin ingest) ✓ Phase 2 (Telegram food logger) ✓  
Pi is in the case, SSH works. No social media. No sensors wired yet.

Realistic window: ~5 working sessions over two weeks. Not every day.

---

## Session 1 — Finish Pi setup (physical + terminal work)

You're already SSHed in. Do this in one sitting.

**uv + repo:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
git clone git@github.com:codingwithchad/agent-sleepy.git
cd agent-sleepy
uv sync
```

**Environment:**
- Copy your `.env` from the dev machine to the Pi (`scp .env codingwithchad@192.168.1.19:~/agent-sleepy/`)
- Create `data/` directory: `mkdir -p data`

**Smoke test:**
```bash
uv run python -m sleepy.jobs.nightly_ingest --days 7
```
Should pull Garmin data and populate the DB. If it works, the Pi is the real host now.

**Cron:**
```bash
crontab -e
```
Add:
```
0 9 * * * cd /home/codingwithchad/agent-sleepy && uv run python -m sleepy.jobs.nightly_ingest >> /home/codingwithchad/agent-sleepy/data/ingest.log 2>&1
```

**Also start the food logger bot on the Pi** (so it survives closing your laptop):
```bash
# test first
uv run python -m sleepy.jobs.telegram_bot

# then add to cron or run in a tmux session
```

Done when: Pi is pulling Garmin data on its own and the food bot responds from the Pi.

---

## Session 2 — Wire the SHT40 sensor

You have the SHT40 and STEMMA QT cables. The Argon ONE exposes GPIO through the lid.

**Wire it (I2C):**
| SHT40 pin | Pi GPIO pin |
|-----------|-------------|
| VIN       | Pin 1 (3.3V) |
| GND       | Pin 6 (GND) |
| SDA       | Pin 3 (GPIO 2) |
| SCL       | Pin 5 (GPIO 3) |

If using the STEMMA QT cable, check the Adafruit pinout for the SHT40 breakout — the cable colors map directly.

**Enable I2C on the Pi:**
```bash
sudo raspi-config
# Interface Options → I2C → Enable
sudo reboot
```

**Confirm it shows up:**
```bash
sudo apt install -y i2c-tools
i2cdetect -y 1
```
SHT40 should appear at address `0x44`.

**Order the remaining sensors if you want them:**
- BH1750 light sensor (~$6) — tells the agent if your room is too bright at bedtime
- SCD41 CO2 sensor (~$45) — the highest-signal variable; closed bedroom CO2 genuinely wrecks sleep. Worth it.

Done when: `i2cdetect` shows `0x44` and you haven't knocked the Pi off the shelf.

---

## Session 3 — Phase 3 starts: daily context builder (code)

This is the first real Phase 3 work. No LLM yet, just data assembly.

**Build `src/sleepy/analyze/daily_context.py`:**
- `DailyContext` Pydantic model: last night's sleep + yesterday's food logs, packaged for the LLM
- `build_context(date) -> DailyContext` function that queries both tables
- Fields that matter: sleep score, HRV, duration, deep/REM pct, wake count, food logs with timing, any late caffeine or alcohol flags

**Tests:** `tests/analyze/test_daily_context.py` — at minimum, test it runs against your real DB and returns a valid `DailyContext`.

Done when: you can call `build_context(date.today())` and get back a clean object with your actual data in it.

---

## Session 4 — Coach prompt + message generator (code)

**`src/sleepy/coach/prompts.py`:**
- System prompt defining the coach's voice: direct, a little sarcastic, genuinely wants you to improve, references specific numbers
- No fluff. Not a wellness app. This coach will say "your HRV was 38, that's rough, and you had coffee at 3pm — connect the dots"

**`src/sleepy/coach/messages.py`:**
- `CoachMessage` Pydantic model: `headline`, `body`, `tomorrow_suggestion`
- `generate_morning_message(context: DailyContext) -> CoachMessage`
- Uses the Anthropic API with structured output (tool use or `response_format`)
- Model from `config.py`, not hardcoded

Done when: you can call `generate_morning_message(context)` in a script and read something that sounds like a real coach, not a chatbot.

---

## Session 5 — Morning report job + Telegram delivery

**`src/sleepy/jobs/morning_report.py`:**
- Build context for yesterday/last night
- Generate message
- Print to stdout (fallback always works)
- Send to yourself via Telegram (reuse the bot token + your user ID from the food logger)
- Persist the message to a `coach_messages` table in SQLite

**Add to cron on the Pi:**
```
0 8 * * * cd /home/codingwithchad/agent-sleepy && uv run python -m sleepy.jobs.morning_report >> /home/codingwithchad/agent-sleepy/data/coach.log 2>&1
```

Done when: you wake up and your phone has a Telegram message from your own Pi roasting your sleep.

---

## What's explicitly NOT in this sprint

- Sensor ingest code — wire the hardware first, write the code after
- Social media / content — not a priority until the agent is actually doing something worth posting about
- Correlation analysis (Phase 4) — needs more data, comes after Phase 3 is running
- BH1750 or SCD41 ingest — order them this sprint, wire them next sprint

---

## Exit criteria for this sprint

- [ ] Pi is the host for both nightly ingest and the food bot
- [ ] SHT40 is wired and detected on I2C
- [ ] `morning_report.py` runs end-to-end and delivers a Telegram message
- [ ] At least one morning message references real data from your sleep + food logs
