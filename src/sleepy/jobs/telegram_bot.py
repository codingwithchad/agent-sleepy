"""Telegram bot for logging food/drink entries and away nights via natural language.

Run this as a long-lived process alongside the nightly ingest cron job.
It polls Telegram for new messages and logs them to the SQLite database.

Usage:
    uv run python -m sleepy.jobs.telegram_bot

Required env vars (in .env):
    TELEGRAM_BOT_TOKEN  — from @BotFather on Telegram
    TELEGRAM_USER_ID    — your numeric Telegram user ID (get it from @userinfobot)
    ANTHROPIC_API_KEY   — for the LLM parser

Commands:
    /away <dates>  — mark nights as away from home, e.g. /away June 14 to 16
    /home <dates>  — clear away status for dates, e.g. /home June 14

Any non-command message is treated as a food/drink log entry.

The bot only responds to the configured TELEGRAM_USER_ID. Messages from any
other sender are silently ignored — no error, no reply.
"""

from __future__ import annotations

import datetime
import logging
import os
import zoneinfo

from dotenv import find_dotenv, load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv(find_dotenv(raise_error_if_not_found=False, usecwd=True))

from sleepy.coach.food_parser import parse_food_message  # noqa: E402
from sleepy.coach.location_parser import parse_away_dates  # noqa: E402
from sleepy.config import LOCAL_TZ  # noqa: E402
from sleepy.models.food import FoodLog  # noqa: E402
from sleepy.models.location import AwayNight  # noqa: E402
from sleepy.store.food import init_food_table, insert_food_log  # noqa: E402
from sleepy.store.location import init_away_table, mark_away, mark_home  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)  # suppress URLs that contain the bot token
logger = logging.getLogger(__name__)

_tz = zoneinfo.ZoneInfo(LOCAL_TZ)


def _to_utc(naive_local: datetime.datetime) -> datetime.datetime:
    """Attach the local timezone to a naive datetime and convert to UTC."""
    return naive_local.replace(tzinfo=_tz).astimezone(datetime.timezone.utc)


def _confirmation(log: FoodLog) -> str:
    """Build a short confirmation message to echo back to the user."""
    local_time = log.occurred_at_utc.astimezone(_tz).strftime("%-I:%M %p")

    if log.entry_type == "caffeine":
        mg = f" ({int(log.caffeine_mg)}mg)" if log.caffeine_mg else ""
        return f"Logged caffeine{mg} at {local_time}."
    elif log.entry_type == "meal":
        detail = f" ({log.notes})" if log.notes else ""
        return f"Logged meal{detail} at {local_time}."
    elif log.entry_type == "alcohol":
        count = log.alcohol_drinks or 0
        plural = "s" if count != 1 else ""
        drinks = f" ({count} drink{plural})" if log.alcohol_drinks else ""
        return f"Logged alcohol{drinks} at {local_time}."
    else:
        return f"Logged entry at {local_time}."


def _is_authorized(update: Update) -> bool:
    authorized_id = int(os.environ["TELEGRAM_USER_ID"])
    return update.effective_user is not None and update.effective_user.id == authorized_id


async def handle_away_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /away <dates> — mark nights as away from home."""
    if not _is_authorized(update):
        return

    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text(
            "Usage: /away <dates>\n"
            "Examples:\n  /away June 14\n  /away June 14 to 16\n  /away June 14, 15, 16"
        )
        return

    today = datetime.datetime.now(_tz).date()
    logger.info("Parsing away dates from: %r", text)

    try:
        dates = parse_away_dates(text, today=today)
    except Exception:
        logger.exception("Failed to parse away dates from: %r", text)
        await update.message.reply_text("Couldn't parse those dates — try /away June 14 to 16")
        return

    if not dates:
        await update.message.reply_text("No dates found — try /away June 14 to 16")
        return

    for d in dates:
        mark_away(AwayNight(date=d))

    date_list = ", ".join(d.strftime("%b %-d") for d in dates)
    n = len(dates)
    night_s = "night" if n == 1 else "nights"
    logger.info("Marked %d %s away: %s", n, night_s, date_list)
    await update.message.reply_text(f"Marked {n} {night_s} away: {date_list}.")


async def handle_home_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /home <dates> — clear away status for nights (undo /away)."""
    if not _is_authorized(update):
        return

    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text("Usage: /home <dates>\nExample: /home June 14")
        return

    today = datetime.datetime.now(_tz).date()
    logger.info("Parsing home dates from: %r", text)

    try:
        dates = parse_away_dates(text, today=today)
    except Exception:
        logger.exception("Failed to parse home dates from: %r", text)
        await update.message.reply_text("Couldn't parse those dates — try /home June 14")
        return

    if not dates:
        await update.message.reply_text("No dates found — try /home June 14")
        return

    for d in dates:
        mark_home(d)

    date_list = ", ".join(d.strftime("%b %-d") for d in dates)
    n = len(dates)
    night_s = "night" if n == 1 else "nights"
    logger.info("Cleared %d %s (marked home): %s", n, night_s, date_list)
    await update.message.reply_text(f"Cleared {n} {night_s} (marked home): {date_list}.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle an incoming text message from Telegram (food/drink log)."""
    if not _is_authorized(update):
        logger.info(
            "Ignored message from unauthorized user id=%s",
            update.effective_user.id if update.effective_user else "unknown",
        )
        return

    text = update.message.text.strip()
    now_local = datetime.datetime.now(_tz).replace(tzinfo=None)  # naive local time

    logger.info("Received message: %r", text)

    try:
        parsed = parse_food_message(message=text, now_local=now_local)
    except Exception:
        logger.exception("Parser failed on message: %r", text)
        await update.message.reply_text(
            "Couldn't parse that one — try again? (e.g. 'coffee at 2pm' or 'dinner at 9')"
        )
        return

    occurred_utc = _to_utc(parsed.occurred_at_local)

    log = FoodLog(
        date=parsed.occurred_at_local.date(),
        entry_type=parsed.entry_type,
        occurred_at_utc=occurred_utc,
        caffeine_mg=parsed.caffeine_mg,
        alcohol_drinks=parsed.alcohol_drinks,
        notes=parsed.notes,
        raw_message=text,
    )

    insert_food_log(log)
    confirmation = _confirmation(log)
    logger.info("Stored food log: %s", confirmation)
    await update.message.reply_text(confirmation)


def main() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    init_food_table()
    init_away_table()

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("away", handle_away_command))
    app.add_handler(CommandHandler("home", handle_home_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Sleepy bot started. Polling for messages...")
    app.run_polling()


if __name__ == "__main__":
    main()
