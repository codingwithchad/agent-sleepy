"""Tests for store/location.py — away_nights table round-trips."""

from __future__ import annotations

import datetime
import tempfile
from pathlib import Path

import pytest

from sleepy.models.location import AwayNight
from sleepy.store.location import init_away_table, is_away, mark_away, mark_home


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    """Temporary SQLite DB with the away_nights table created."""
    p = tmp_path / "test.db"
    init_away_table(db_path=p)
    return p


def test_mark_away_and_is_away(db: Path) -> None:
    d = datetime.date(2026, 6, 14)
    assert not is_away(d, db_path=db)
    mark_away(AwayNight(date=d, note="camping"), db_path=db)
    assert is_away(d, db_path=db)


def test_mark_away_is_idempotent(db: Path) -> None:
    d = datetime.date(2026, 6, 14)
    mark_away(AwayNight(date=d), db_path=db)
    mark_away(AwayNight(date=d, note="updated note"), db_path=db)  # should not raise
    assert is_away(d, db_path=db)


def test_mark_home_clears_away(db: Path) -> None:
    d = datetime.date(2026, 6, 14)
    mark_away(AwayNight(date=d), db_path=db)
    mark_home(d, db_path=db)
    assert not is_away(d, db_path=db)


def test_mark_home_noop_when_not_away(db: Path) -> None:
    d = datetime.date(2026, 6, 14)
    mark_home(d, db_path=db)  # should not raise
    assert not is_away(d, db_path=db)


def test_away_does_not_bleed_to_adjacent_dates(db: Path) -> None:
    d = datetime.date(2026, 6, 14)
    mark_away(AwayNight(date=d), db_path=db)
    assert not is_away(datetime.date(2026, 6, 13), db_path=db)
    assert not is_away(datetime.date(2026, 6, 15), db_path=db)
