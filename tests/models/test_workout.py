"""Round-trip tests for workout Pydantic models."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sleepy.models.workout import GarminActivity, Workout

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load_garmin_activity() -> dict:
    return json.loads((FIXTURES / "garmin_activity.json").read_text())


def test_garmin_activity_round_trip():
    raw = _load_garmin_activity()
    start_utc = datetime(2026, 5, 11, 3, 15, 0, tzinfo=timezone.utc)
    end_utc = datetime(2026, 5, 11, 3, 15, 0, tzinfo=timezone.utc)

    activity = GarminActivity(
        activity_id=raw["activityId"],
        date=start_utc.date(),
        name=raw["activityName"],
        activity_type=raw["activityType"]["typeKey"],
        start_time_utc=start_utc,
        end_time_utc=end_utc,
        duration_min=int(raw["duration"]) // 60,
        avg_hr=raw["averageHR"],
        max_hr=raw["maxHR"],
        calories=raw["calories"],
        aerobic_te=raw["aerobicTrainingEffect"],
        anaerobic_te=raw["anaerobicTrainingEffect"],
    )

    assert activity.activity_id == 17000000001
    assert activity.activity_type == "running"
    assert activity.duration_min == 45
    assert activity.avg_hr == 148
    assert activity.aerobic_te == pytest.approx(3.5)


def test_garmin_activity_requires_utc_timestamps():
    with pytest.raises(ValueError, match="timezone-aware"):
        GarminActivity(
            activity_id=1,
            date="2026-05-11",
            activity_type="running",
            start_time_utc=datetime(2026, 5, 11, 20, 0),  # naive — no tzinfo
            end_time_utc=datetime(2026, 5, 11, 20, 45, tzinfo=timezone.utc),
            duration_min=45,
        )


def test_garmin_activity_optional_fields_default_none():
    start_utc = datetime(2026, 5, 11, 20, 0, tzinfo=timezone.utc)
    activity = GarminActivity(
        activity_id=2,
        date=start_utc.date(),
        activity_type="strength_training",
        start_time_utc=start_utc,
        end_time_utc=start_utc,
        duration_min=60,
    )
    assert activity.name is None
    assert activity.avg_hr is None
    assert activity.aerobic_te is None


def test_workout_round_trip_via_model_dump():
    start_utc = datetime(2026, 5, 11, 3, 15, 0, tzinfo=timezone.utc)
    end_utc = datetime(2026, 5, 11, 4, 0, 0, tzinfo=timezone.utc)

    workout = Workout(
        activity_id=17000000001,
        source="garmin",
        date=start_utc.date(),
        name="Evening Run",
        activity_type="running",
        start_time_utc=start_utc,
        end_time_utc=end_utc,
        duration_min=45,
        avg_hr=148,
        max_hr=172,
        calories=380,
        aerobic_te=3.5,
        anaerobic_te=1.2,
    )

    dumped = workout.model_dump(mode="json")
    restored = Workout(**dumped)

    assert restored.activity_id == workout.activity_id
    assert restored.source == "garmin"
    assert restored.activity_type == "running"
    assert restored.start_time_utc == start_utc
    assert restored.aerobic_te == pytest.approx(3.5)
