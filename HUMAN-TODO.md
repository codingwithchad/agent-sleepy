# HUMAN-TODO.md

Things Claude can't do — requires your hands, your credentials, or your physical device.

---

## Right now — Telegram food logger setup

- [ ] **Add your Anthropic API key to `.env`:**
  ```
  ANTHROPIC_API_KEY=sk-ant-...
  ```
  Get it from [console.anthropic.com](https://console.anthropic.com). The food parser uses it to understand natural-language messages.

- [ ] **Create a Telegram bot via @BotFather:**
  1. Open Telegram → search `@BotFather`
  2. Send `/newbot`
  3. Give it a name (e.g. "Sleepy Logger") and a username (e.g. `sleepylogger_bot`)
  4. Copy the API token it gives you

- [ ] **Get your Telegram user ID via @userinfobot:**
  1. Search `@userinfobot` on Telegram
  2. Start a chat — it replies with your numeric user ID
  3. Copy it

- [ ] **Add both to `.env`:**
  ```
  TELEGRAM_BOT_TOKEN=<token from BotFather>
  TELEGRAM_USER_ID=<your numeric ID>
  ```

- [ ] **Start the bot on your computer:**
  ```bash
  uv run python -m sleepy.jobs.telegram_bot
  ```
  You should see: `Sleepy food logger bot started. Polling for messages...`

- [ ] **Test it from your phone.** Open Telegram, find your bot, send a few messages:
  - `coffee at 2pm`
  - `big dinner around 9`
  - `two beers at 7`
  - `herbal tea at 10`

  Each one should get a quick confirmation reply. If it does, you're done.

- [ ] **Spot-check the data landed in SQLite:**
  ```bash
  uv run python -c "
  import sqlite3
  con = sqlite3.connect('data/sleepy.db')
  rows = con.execute('select date, entry_type, occurred_at_utc, caffeine_mg, notes from food_logs order by occurred_at_utc desc limit 10').fetchall()
  for r in rows: print(r)
  con.close()
  "
  ```

---

## Phase 1 — Ongoing

- [ ] **Wear your watch every night.** The analysis needs data. Gaps from unworn nights just mean more days to reach the exit criteria.

- [ ] **Run the nightly ingest (or set up cron).** If you haven't automated it yet:
  ```bash
  uv run python -m sleepy.jobs.nightly_ingest --days 7
  ```
  Cron entry for 9am daily:
  ```
  0 9 * * * cd /path/to/agent-sleepy && uv run python -m sleepy.jobs.nightly_ingest
  ```

- [ ] **Verify Phase 1 exit criteria:**
  ```bash
  uv run python -c "
  import sqlite3
  con = sqlite3.connect('data/sleepy.db')
  print('sleep nights:', con.execute('select count(*) from sleep_nights').fetchone()[0])
  print('duplicates:', con.execute('select date, source, count(*) from sleep_nights group by date, source having count(*) > 1').fetchall())
  con.close()
  "
  ```
  Should show 7+ nights, zero duplicates.

---

## Standing rules

- Credentials or network errors: yours to debug — Claude can't log into Garmin or Telegram for you.
- Python tracebacks: paste them to Claude.
- Keep this file updated as you go. Claude reads it at the start of every session.
