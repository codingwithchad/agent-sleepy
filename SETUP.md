# SETUP.md

Full setup instructions for agent-sleepy — both local dev and production deployment on a Raspberry Pi.

---

## Local development (any machine)

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`

### Install

```bash
git clone https://github.com/codingwithchad/agent-sleepy.git
cd agent-sleepy
uv sync
cp .env.example .env
```

Edit `.env` and fill in all required values (see Environment variables below).

### Verify

```bash
uv run python -c "import sleepy; print('ok')"
uv run pytest
```

---

## Production deployment on Raspberry Pi

This project runs 24/7 on a Raspberry Pi 4 in an Argon ONE case. The Pi handles scheduled ingest jobs, the Telegram food logger bot, and bedroom environment sensor polling. No GUI needed — everything is SSH and cron.

### 1. Flash the OS

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Choose **Raspberry Pi OS Lite (64-bit)** — no desktop needed
3. Before writing, open the **Advanced options** (gear icon):
   - Set hostname (e.g. `sleepy`)
   - Enable SSH, add your public key (preferred) or set a password
   - Configure your WiFi SSID and password
4. Flash to MicroSD, insert into Pi, power on

The Pi will be reachable at `sleepy.local` or its IP within a minute or two.

### 2. SSH in and update

```bash
ssh pi@sleepy.local
sudo apt update && sudo apt upgrade -y
sudo reboot
```

### 3. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # or open a new shell
uv --version     # verify
```

### 4. Clone the repo

```bash
git clone https://github.com/codingwithchad/agent-sleepy.git
cd agent-sleepy
uv sync
```

### 5. Configure environment

```bash
cp .env.example .env
nano .env
```

Fill in all values. The `.env` file never leaves the Pi — it is gitignored.

### 6. Initialize the database

```bash
mkdir -p data
uv run python -m sleepy.jobs.nightly_ingest --days 7
```

This creates `data/sleepy.db` and pulls your last 7 nights of Garmin data. If it works, the DB is live.

### 7. Set up cron jobs

```bash
crontab -e
```

Add these lines (adjust times to taste — these are in Pi local time):

```cron
# Nightly Garmin ingest — runs at 6am daily
0 6 * * * /home/pi/agent-sleepy/scripts/run_ingest.sh

# Start Telegram bot on reboot (bot handles its own polling loop)
@reboot cd /home/pi/agent-sleepy && /home/pi/.local/bin/uv run python -m sleepy.jobs.telegram_bot >> data/telegram.log 2>&1
```

Verify the ingest script is executable:
```bash
chmod +x scripts/run_ingest.sh
```

### 8. Verify cron is running

After the next scheduled run, check the log:
```bash
tail -f ~/agent-sleepy/data/ingest.log
```

### Updating the code

To pull new changes from GitHub and restart:

```bash
cd ~/agent-sleepy
git pull
uv sync  # in case dependencies changed
# If the Telegram bot is running via @reboot cron, kill and let cron restart it on next boot,
# or restart it manually:
pkill -f telegram_bot
uv run python -m sleepy.jobs.telegram_bot >> data/telegram.log 2>&1 &
```

---

## Bedroom sensor wiring (Raspberry Pi)

The Pi collects environmental data from sensors wired to its GPIO header. All sensors use I2C.

### Enable I2C on the Pi

```bash
sudo raspi-config
# Interface Options → I2C → Enable
sudo reboot
```

Verify I2C is working after reboot:
```bash
sudo apt install -y i2c-tools
i2cdetect -y 1
```

### Sensor wiring (GPIO header)

All three sensors share the same I2C bus (SDA + SCL) and power pins.

| Pi pin | GPIO | Connects to |
|--------|------|-------------|
| Pin 1  | 3.3V | VCC on all sensors |
| Pin 3  | GPIO2 (SDA) | SDA on all sensors |
| Pin 5  | GPIO3 (SCL) | SCL on all sensors |
| Pin 6  | GND  | GND on all sensors |

Expected I2C addresses (verify with `i2cdetect -y 1`):

| Sensor | Address |
|--------|---------|
| SHT40 (temp/humidity) | `0x44` |
| BH1750 (light) | `0x23` |
| SCD41 (CO2) | `0x62` |

If using Adafruit STEMMA QT sensors and cables, the wiring is plug-and-play between sensors. For bare breakout modules, use female-to-female jumper wires to the header pins above.

### Install sensor dependencies

```bash
uv add adafruit-circuitpython-sht4x adafruit-circuitpython-bh1750 adafruit-circuitpython-scd4x
```

The ingest job for bedroom sensors will be added in a future phase — see ROADMAP.md.

---

## Environment variables reference

| Variable | Required | Description |
|---|---|---|
| `GARMIN_EMAIL` | Yes | Garmin Connect login email |
| `GARMIN_PASSWORD` | Yes | Garmin Connect login password |
| `ANTHROPIC_API_KEY` | Yes | From [console.anthropic.com](https://console.anthropic.com) |
| `TELEGRAM_BOT_TOKEN` | Yes | Token from @BotFather |
| `TELEGRAM_USER_ID` | Yes | Your numeric Telegram user ID (from @userinfobot) |
