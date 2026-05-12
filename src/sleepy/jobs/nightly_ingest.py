"""Nightly ingest job: pull recent Garmin sleep data and write to SQLite.

Designed to run on a schedule (cron/systemd). Safe to re-run — INSERT OR
REPLACE means duplicate runs update existing rows rather than creating them.

Usage:
    uv run python -m sleepy.jobs.nightly_ingest            # yesterday only
    uv run python -m sleepy.jobs.nightly_ingest --days 7   # backfill a week

For cron use: set GARMINTOKENS in .env to a writable file path so session
tokens are cached and 2FA is only triggered on first run (or token expiry).
"""

from __future__ import annotations

import argparse
import logging
import sys

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(raise_error_if_not_found=False, usecwd=True))

from sleepy.ingest.garmin import fetch_sleep_nights, garmin_to_sleep_night  # noqa: E402
from sleepy.store.sleep import init_db, upsert_nights  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest Garmin sleep data into SQLite.")
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Number of past nights to fetch (default: 1 for nightly cron).",
    )
    args = parser.parse_args()

    logger.info("Fetching %d night(s) from Garmin...", args.days)
    garmin_nights = fetch_sleep_nights(days=args.days)

    if not garmin_nights:
        logger.info("No sleep data returned — nothing to store.")
        return 0

    canonical = [garmin_to_sleep_night(n) for n in garmin_nights]

    init_db()
    written = upsert_nights(canonical)
    logger.info("Wrote %d record(s) to sleep_nights.", written)

    for night in canonical:
        logger.info(
            "  %s | source=%s | score=%s | duration=%dm | deep=%s rem=%s",
            night.date,
            night.source,
            night.score,
            night.duration_min,
            f"{night.deep_min}m" if night.deep_min is not None else "n/a",
            f"{night.rem_min}m" if night.rem_min is not None else "n/a",
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
