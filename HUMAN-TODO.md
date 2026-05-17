# HUMAN-TODO.md

Things Claude can't do — requires your hands, your credentials, or your physical device.

---

## Raspberry Pi — Hardware shopping list

Order from Amazon, Adafruit, or PiShop. Links are pointers, not endorsements — search by part name if you want to comparison shop.

**Compute + enclosure**
- [ ] **Raspberry Pi 4 Model B, 2GB** (~$45) — 2GB is plenty; go 4GB if you want headroom for future phases
- [ ] **Argon ONE case for Raspberry Pi 4** (~$25) — aluminum, looks like a tiny Mac Mini, exposes GPIO through the case lid so sensors still connect
- [ ] **Official Raspberry Pi USB-C power supply (5.1V 3A)** (~$12) — don't use a phone charger; under-voltage causes weird crashes
- [ ] **MicroSD card, 32GB+, A1-rated** (~$10) — Samsung Endurance Pro or SanDisk High Endurance; the A1 rating matters for OS reliability
- [ ] **MicroHDMI to HDMI cable or adapter** (~$6) — Pi 4 uses micro-HDMI; only needed for initial setup if SSH isn't working, then set aside

**Bedroom sensors (all I2C)**
- [ ] **Adafruit SHT40 sensor (#4885)** (~$10) — temperature + humidity, accurate, has STEMMA QT connector
- [ ] **GY-302 / BH1750 ambient light sensor module** (~$5–8) — lux readings; any GY-302 breakout works, use jumper wires to GPIO header
- [ ] **Adafruit SCD41 CO2 sensor (#5190)** (~$45) — optional but the highest-signal bedroom variable; closed rooms with high CO2 wreck sleep quality
- [ ] **STEMMA QT / Qwiic JST cables, 50–100mm** (~$5 for a pack) — plug-and-play between Adafruit sensors; skip if you prefer jumper wires

**Total: ~$108 without CO2 sensor, ~$153 with.** The CO2 sensor is worth it.
note: The CO2 sensor ($45 SCD41) is the one I'd buy — closed bedroom CO2 is the variable most people don't know is hurting their sleep
---

## Raspberry Pi — Setup (after parts arrive)

Full step-by-step instructions are in [SETUP.md](SETUP.md). High-level checklist:

- [ ] Flash Raspberry Pi OS Lite (64-bit) using Raspberry Pi Imager — pre-configure WiFi + SSH in the imager before writing the card
- [ ] Boot Pi in the Argon ONE case, SSH in from dev machine (`ssh pi@sleepy.local`)
- [ ] Follow SETUP.md: update OS, install uv, clone repo, configure `.env`
- [ ] Run `uv run python -m sleepy.jobs.nightly_ingest --days 7` to verify Garmin auth and DB init work
- [ ] Set up cron entries per SETUP.md
- [ ] Wire sensors to GPIO header per SETUP.md, run `i2cdetect -y 1` to confirm addresses
- [ ] Run sensor test script (to be added when sensor ingest job is written)

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
