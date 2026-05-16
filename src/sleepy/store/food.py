"""SQLite persistence for food/drink log entries.

Table: food_logs
Primary key: id (autoincrement)
No natural dedup key — each Telegram message creates one row. If the user
re-sends a correction, they get two rows; that's acceptable for now.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import date
from pathlib import Path

from sleepy.models.food import FoodLog


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
    CREATE TABLE IF NOT EXISTS food_logs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        date            TEXT NOT NULL,
        entry_type      TEXT NOT NULL,
        occurred_at_utc TEXT NOT NULL,
        caffeine_mg     REAL,
        alcohol_drinks  REAL,
        notes           TEXT,
        raw_message     TEXT NOT NULL
    )
"""


def init_food_table(db_path: Path | None = None) -> None:
    """Create the food_logs table if it doesn't exist."""
    with _connect(_db_path(db_path)) as conn:
        conn.execute(_CREATE_TABLE)


def insert_food_log(log: FoodLog, db_path: Path | None = None) -> int:
    """Insert a food log entry. Returns the new row's id."""
    with _connect(_db_path(db_path)) as conn:
        cursor = conn.execute(
            """
            INSERT INTO food_logs (
                date, entry_type, occurred_at_utc,
                caffeine_mg, alcohol_drinks, notes, raw_message
            ) VALUES (
                :date, :entry_type, :occurred_at_utc,
                :caffeine_mg, :alcohol_drinks, :notes, :raw_message
            )
            """,
            {
                "date": log.date.isoformat(),
                "entry_type": log.entry_type,
                "occurred_at_utc": log.occurred_at_utc.isoformat(),
                "caffeine_mg": log.caffeine_mg,
                "alcohol_drinks": log.alcohol_drinks,
                "notes": log.notes,
                "raw_message": log.raw_message,
            },
        )
        return cursor.lastrowid


def get_food_logs_for_date(target: date, db_path: Path | None = None) -> list[FoodLog]:
    """Fetch all food log entries for a given local calendar date, oldest first."""
    with _connect(_db_path(db_path)) as conn:
        rows = conn.execute(
            "SELECT * FROM food_logs WHERE date = ? ORDER BY occurred_at_utc ASC",
            (target.isoformat(),),
        ).fetchall()

    return [
        FoodLog(
            id=row["id"],
            date=row["date"],
            entry_type=row["entry_type"],
            occurred_at_utc=row["occurred_at_utc"],
            caffeine_mg=row["caffeine_mg"],
            alcohol_drinks=row["alcohol_drinks"],
            notes=row["notes"],
            raw_message=row["raw_message"],
        )
        for row in rows
    ]
