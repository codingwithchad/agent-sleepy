"""Tests for the workout SQLite store."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from sleepy.models.workout import Workout
from sleepy.store.workout import get_workouts, init_db, upsert_workouts


def _make_workout(
    activity_id: int = 1,
    activity_type: str = "running",
    start_hour: int = 20,
) -> Workout:
    start_utc = datetime(2026, 5, 11, start_hour, 0, 0, tzinfo=timezone.utc)
    end_utc = datetime(2026, 5, 11, start_hour, 45, 0, tzinfo=timezone.utc)
    return Workout(
        activity_id=activity_id,
        source="garmin",
        date=start_utc.date(),
        name="Test Workout",
        activity_type=activity_type,
        start_time_utc=start_utc,
        end_time_utc=end_utc,
        duration_min=45,
        avg_hr=148,
        max_hr=172,
        calories=380,
        aerobic_te=3.5,
        anaerobic_te=1.2,
    )


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / "test.db"
    init_db(db_path)
    return db_path


def test_upsert_and_get(db: Path):
    workout = _make_workout()
    written = upsert_workouts([workout], db_path=db)

    assert written == 1
    results = get_workouts(db_path=db)
    assert len(results) == 1
    assert results[0].activity_id == workout.activity_id
    assert results[0].activity_type == "running"
    assert results[0].avg_hr == 148
    assert results[0].aerobic_te == pytest.approx(3.5)


def test_upsert_is_idempotent(db: Path):
    workout = _make_workout()
    upsert_workouts([workout], db_path=db)
    upsert_workouts([workout], db_path=db)  # re-run — should not duplicate

    results = get_workouts(db_path=db)
    assert len(results) == 1


def test_upsert_updates_existing_row(db: Path):
    workout = _make_workout()
    upsert_workouts([workout], db_path=db)

    updated = workout.model_copy(update={"avg_hr": 155})
    upsert_workouts([updated], db_path=db)

    results = get_workouts(db_path=db)
    assert len(results) == 1
    assert results[0].avg_hr == 155


def test_multiple_workouts_same_day(db: Path):
    morning = _make_workout(activity_id=1, start_hour=7)
    evening = _make_workout(activity_id=2, start_hour=20)
    upsert_workouts([morning, evening], db_path=db)

    results = get_workouts(db_path=db)
    assert len(results) == 2


def test_filter_by_source(db: Path):
    workout = _make_workout()
    upsert_workouts([workout], db_path=db)

    assert len(get_workouts(source="garmin", db_path=db)) == 1
    assert len(get_workouts(source="oura", db_path=db)) == 0


def test_optional_fields_stored_as_none(db: Path):
    start_utc = datetime(2026, 5, 11, 20, 0, 0, tzinfo=timezone.utc)
    workout = Workout(
        activity_id=99,
        source="garmin",
        date=start_utc.date(),
        activity_type="yoga",
        start_time_utc=start_utc,
        end_time_utc=start_utc,
        duration_min=60,
    )
    upsert_workouts([workout], db_path=db)

    results = get_workouts(db_path=db)
    assert results[0].avg_hr is None
    assert results[0].aerobic_te is None
    assert results[0].name is None
