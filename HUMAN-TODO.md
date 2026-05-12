# HUMAN-TODO.md

Things Claude can't do — requires your hands, your credentials, or your physical device.
Structured like ROADMAP.md: do these in order, check them off as you go.

---

## Phase 0 — Environment setup

- [x] **Install `uv` permanently.**

- [ ] **Create your `.env` file one level above the repo** (so it can never be accidentally committed, even with `git add .`):
  ```bash
  cp .env.example ../.env
  # then edit ../.env
  ```
  The file should live at `~/code/.env` (one directory above this repo). The code uses `find_dotenv()` which walks up parent directories to find it automatically.

  Fill in when ready:
  ```
  GARMIN_EMAIL=you@example.com
  GARMIN_PASSWORD=yourpassword
  GARMINTOKENS=~/.garmin_tokens
  ANTHROPIC_API_KEY=          # leave blank until Phase 3
  ```

---

## Phase 1 — Garmin account setup

- [ ] **Create a Garmin Connect account** if you don't have one: [connect.garmin.com](https://connect.garmin.com). Use the same email you'll put in `.env`.

- [ ] **Pair your Garmin device** with the Garmin Connect app on your phone. Sleep tracking must be enabled on the device (it usually is by default). Wear it for at least one full night before the next step so there's data to pull.

- [ ] **Check whether your account has 2FA enabled.** In Garmin Connect (web or app): Account → Security. If 2FA is on, tell Claude before running anything — a `prompt_mfa` handler needs to be added to the ingest code first.

- [ ] **Run the inspection command** once you have credentials and at least one night of data:
  ```bash
  PYTHONPATH=src uv run python -c "
  import logging, json
  logging.basicConfig(level=logging.INFO)
  from sleepy.ingest.garmin import fetch_sleep_nights
  nights = fetch_sleep_nights(7)
  print(json.dumps([n.model_dump(mode='json') for n in nights], indent=2, default=str))
  "
  ```
  Expected: a JSON array of nights. If you see `[]`, check the log output for errors.

- [ ] **Paste the output to Claude.** Claude will confirm the field names match, flag anything extra worth adding, and give the go-ahead for the storage layer.

- [ ] **Wear your watch every night.** Phase 1 exit needs 7+ rows in the database. Gaps from unworn nights just mean more calendar days to reach 7.

---

## Phase 1 — After Claude signs off on the schema

- [ ] Run the ingest job daily (Claude will build this next):
  ```bash
  uv run python -m sleepy.jobs.ingest_sleep
  ```
  Or add the cron entry Claude will provide.

- [ ] Verify exit criteria:
  ```bash
  uv run python -c "
  import sqlite3
  con = sqlite3.connect('data/sleepy.db')
  print(con.execute('select count(*) from sleep_nights').fetchone())
  con.close()
  "
  ```
  Should print `(7,)` or higher with no duplicates.

---

## Standing rules

- If a step fails with a credentials or network error, that's yours to debug — Claude can't log into Garmin for you.
- If a step fails with a Python traceback, paste it to Claude.
- Keep this file updated as you complete steps. Claude reads it too.
