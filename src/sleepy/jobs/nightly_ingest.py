"""Nightly ingest job: pull recent Garmin sleep and workout data, write to SQLite.

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

from sleepy.ingest.garmin import (  # noqa: E402
    fetch_activities,
    fetch_sleep_nights,
    garmin_to_sleep_night,
    garmin_to_workout,
)
from sleepy.store.sleep import init_db as init_sleep_db  # noqa: E402
from sleepy.store.sleep import upsert_nights  # noqa: E402
from sleepy.store.workout import init_db as init_workout_db  # noqa: E402
from sleepy.store.workout import upsert_workouts  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest Garmin sleep and workout data into SQLite."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Number of past days to fetch (default: 1 for nightly cron).",
    )
    args = parser.parse_args()

    init_sleep_db()
    init_workout_db()

    # --- Sleep ---
    logger.info("Fetching %d night(s) of sleep from Garmin...", args.days)
    garmin_nights = fetch_sleep_nights(days=args.days)

    if not garmin_nights:
        logger.info("No sleep data returned.")
    else:
        canonical_nights = [garmin_to_sleep_night(n) for n in garmin_nights]
        written = upsert_nights(canonical_nights)
        logger.info("Wrote %d sleep record(s) to sleep_nights.", written)

        for night in canonical_nights:
            logger.info(
                "  %s | source=%s | score=%s | duration=%dm | deep=%s rem=%s",
                night.date,
                night.source,
                night.score,
                night.duration_min,
                f"{night.deep_min}m" if night.deep_min is not None else "n/a",
                f"{night.rem_min}m" if night.rem_min is not None else "n/a",
            )

    # --- Workouts ---
    logger.info("Fetching %d day(s) of activities from Garmin...", args.days)
    garmin_activities = fetch_activities(days=args.days)

    if not garmin_activities:
        logger.info("No activity data returned.")
    else:
        canonical_workouts = [garmin_to_workout(a) for a in garmin_activities]
        written = upsert_workouts(canonical_workouts)
        logger.info("Wrote %d workout record(s) to workouts.", written)

        for workout in canonical_workouts:
            logger.info(
                "  %s | %s | %s | %dm | avg_hr=%s | aerobic_te=%s",
                workout.start_time_utc.strftime("%Y-%m-%d %H:%M UTC"),
                workout.source,
                workout.activity_type,
                workout.duration_min,
                workout.avg_hr or "n/a",
                workout.aerobic_te or "n/a",
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
