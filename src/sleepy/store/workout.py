"""SQLite persistence for workout/activity records.

Table: workouts
Primary key: (activity_id, source) — one row per activity per device.
All writes use INSERT OR REPLACE so jobs are safe to re-run.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from sleepy.models.workout import Workout


def _db_path(override: Path | None) -> Path:
    if override is not None:
        return override
    return Path(os.getenv("SLEEPY_DB", "data/sleepy.db"))


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


_CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS workouts (
        activity_id     INTEGER NOT NULL,
        source          TEXT NOT NULL,
        date            TEXT NOT NULL,
        name            TEXT,
        activity_type   TEXT NOT NULL,
        start_time_utc  TEXT NOT NULL,
        end_time_utc    TEXT NOT NULL,
        duration_min    INTEGER NOT NULL,
        avg_hr          INTEGER,
        max_hr          INTEGER,
        calories        INTEGER,
        aerobic_te      REAL,
        anaerobic_te    REAL,
        PRIMARY KEY (activity_id, source)
    )
"""


def init_db(db_path: Path | None = None) -> None:
    """Create the workouts table if it doesn't exist."""
    with _connect(_db_path(db_path)) as conn:
        conn.execute(_CREATE_TABLE)


def upsert_workouts(workouts: list[Workout], db_path: Path | None = None) -> int:
    """Insert or replace workout records. Returns the number of rows written."""
    rows = [
        {
            "activity_id": w.activity_id,
            "source": w.source,
            "date": w.date.isoformat(),
            "name": w.name,
            "activity_type": w.activity_type,
            "start_time_utc": w.start_time_utc.isoformat(),
            "end_time_utc": w.end_time_utc.isoformat(),
            "duration_min": w.duration_min,
            "avg_hr": w.avg_hr,
            "max_hr": w.max_hr,
            "calories": w.calories,
            "aerobic_te": w.aerobic_te,
            "anaerobic_te": w.anaerobic_te,
        }
        for w in workouts
    ]
    with _connect(_db_path(db_path)) as conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO workouts (
                activity_id, source, date, name, activity_type,
                start_time_utc, end_time_utc, duration_min,
                avg_hr, max_hr, calories, aerobic_te, anaerobic_te
            ) VALUES (
                :activity_id, :source, :date, :name, :activity_type,
                :start_time_utc, :end_time_utc, :duration_min,
                :avg_hr, :max_hr, :calories, :aerobic_te, :anaerobic_te
            )
            """,
            rows,
        )
    return len(rows)


def get_workouts(
    source: str | None = None,
    limit: int = 60,
    db_path: Path | None = None,
) -> list[Workout]:
    """Fetch recent workout records, newest first.

    Args:
        source: Filter to a specific device ("garmin", etc.).
                Pass None to return all sources.
        limit:  Maximum number of rows to return (default 60 — ~2 months
                of daily workouts).
    """
    with _connect(_db_path(db_path)) as conn:
        if source is not None:
            rows = conn.execute(
                "SELECT * FROM workouts WHERE source = ? ORDER BY start_time_utc DESC LIMIT ?",
                (source, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM workouts ORDER BY start_time_utc DESC LIMIT ?",
                (limit,),
            ).fetchall()

    return [
        Workout(
            activity_id=row["activity_id"],
            source=row["source"],
            date=row["date"],
            name=row["name"],
            activity_type=row["activity_type"],
            start_time_utc=row["start_time_utc"],
            end_time_utc=row["end_time_utc"],
            duration_min=row["duration_min"],
            avg_hr=row["avg_hr"],
            max_hr=row["max_hr"],
            calories=row["calories"],
            aerobic_te=row["aerobic_te"],
            anaerobic_te=row["anaerobic_te"],
        )
        for row in rows
    ]
