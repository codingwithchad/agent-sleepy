"""SQLite persistence for away-night tracking.

Table: away_nights
Primary key: date (TEXT, ISO 8601)

All writes are idempotent — mark_away uses INSERT OR REPLACE, mark_home
is a no-op if the date isn't in the table.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import date
from pathlib import Path

from sleepy.models.location import AwayNight


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
    CREATE TABLE IF NOT EXISTS away_nights (
        date  TEXT PRIMARY KEY,
        note  TEXT
    )
"""


def init_away_table(db_path: Path | None = None) -> None:
    """Create the away_nights table if it doesn't exist."""
    with _connect(_db_path(db_path)) as conn:
        conn.execute(_CREATE_TABLE)


def mark_away(night: AwayNight, db_path: Path | None = None) -> None:
    """Mark a date as away from home. Idempotent — safe to call multiple times."""
    with _connect(_db_path(db_path)) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO away_nights (date, note) VALUES (?, ?)",
            (night.date.isoformat(), night.note),
        )


def mark_home(d: date, db_path: Path | None = None) -> None:
    """Remove an away record for a date. No-op if the date is not marked away."""
    with _connect(_db_path(db_path)) as conn:
        conn.execute("DELETE FROM away_nights WHERE date = ?", (d.isoformat(),))


def is_away(d: date, db_path: Path | None = None) -> bool:
    """Return True if the given date is marked as away from home."""
    with _connect(_db_path(db_path)) as conn:
        row = conn.execute("SELECT 1 FROM away_nights WHERE date = ?", (d.isoformat(),)).fetchone()
    return row is not None
