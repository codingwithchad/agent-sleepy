"""SQLite persistence for the canonical SleepNight records.

Table: sleep_nights
Primary key: (date, source) — one row per night per device.
All writes use INSERT OR REPLACE so jobs are safe to re-run.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from sleepy.models.sleep import SleepNight


def _db_path(override: Path | None) -> Path:
    """Resolve the database path: explicit arg > SLEEPY_DB env var > default."""
    if override is not None:
        return override
    return Path(os.getenv("SLEEPY_DB", "data/sleepy.db"))


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


_CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS sleep_nights (
        date                TEXT NOT NULL,
        source              TEXT NOT NULL,
        sleep_start_utc     TEXT NOT NULL,
        sleep_end_utc       TEXT NOT NULL,
        duration_min        INTEGER NOT NULL,
        score               INTEGER,
        deep_min            INTEGER,
        light_min           INTEGER,
        rem_min             INTEGER,
        awake_min           INTEGER,
        avg_hrv             REAL,
        avg_respiration     REAL,
        restless_moments    INTEGER,
        sleep_latency_min   INTEGER,
        PRIMARY KEY (date, source)
    )
"""


def init_db(db_path: Path | None = None) -> None:
    """Create the sleep_nights table if it doesn't exist."""
    with _connect(_db_path(db_path)) as conn:
        conn.execute(_CREATE_TABLE)


def upsert_nights(nights: list[SleepNight], db_path: Path | None = None) -> int:
    """Insert or replace sleep records. Returns the number of rows written."""
    rows = [
        {
            "date": n.date.isoformat(),
            "source": n.source,
            "sleep_start_utc": n.sleep_start_utc.isoformat(),
            "sleep_end_utc": n.sleep_end_utc.isoformat(),
            "duration_min": n.duration_min,
            "score": n.score,
            "deep_min": n.deep_min,
            "light_min": n.light_min,
            "rem_min": n.rem_min,
            "awake_min": n.awake_min,
            "avg_hrv": n.avg_hrv,
            "avg_respiration": n.avg_respiration,
            "restless_moments": n.restless_moments,
            "sleep_latency_min": n.sleep_latency_min,
        }
        for n in nights
    ]
    with _connect(_db_path(db_path)) as conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO sleep_nights (
                date, source, sleep_start_utc, sleep_end_utc, duration_min,
                score, deep_min, light_min, rem_min, awake_min,
                avg_hrv, avg_respiration, restless_moments, sleep_latency_min
            ) VALUES (
                :date, :source, :sleep_start_utc, :sleep_end_utc, :duration_min,
                :score, :deep_min, :light_min, :rem_min, :awake_min,
                :avg_hrv, :avg_respiration, :restless_moments, :sleep_latency_min
            )
            """,
            rows,
        )
    return len(rows)


def get_nights(
    source: str | None = None,
    limit: int = 30,
    db_path: Path | None = None,
) -> list[SleepNight]:
    """Fetch recent sleep records, newest first.

    Args:
        source: Filter to a specific device ("garmin", "oura", etc.).
                Pass None to return all sources.
        limit:  Maximum number of rows to return.
    """
    with _connect(_db_path(db_path)) as conn:
        if source is not None:
            rows = conn.execute(
                "SELECT * FROM sleep_nights WHERE source = ? ORDER BY date DESC LIMIT ?",
                (source, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM sleep_nights ORDER BY date DESC LIMIT ?",
                (limit,),
            ).fetchall()

    return [
        SleepNight(
            date=row["date"],
            source=row["source"],
            sleep_start_utc=row["sleep_start_utc"],
            sleep_end_utc=row["sleep_end_utc"],
            duration_min=row["duration_min"],
            score=row["score"],
            deep_min=row["deep_min"],
            light_min=row["light_min"],
            rem_min=row["rem_min"],
            awake_min=row["awake_min"],
            avg_hrv=row["avg_hrv"],
            avg_respiration=row["avg_respiration"],
            restless_moments=row["restless_moments"],
            sleep_latency_min=row["sleep_latency_min"],
        )
        for row in rows
    ]
