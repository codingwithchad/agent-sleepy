"""Round-trip tests for food Pydantic models."""

import datetime

import pytest

from sleepy.models.food import FoodLog, ParsedFoodEntry


def test_parsed_food_entry_caffeine_round_trip():
    entry = ParsedFoodEntry(
        entry_type="caffeine",
        occurred_at_local=datetime.datetime(2024, 1, 15, 14, 0),
        caffeine_mg=100.0,
        notes="drip coffee",
    )
    assert ParsedFoodEntry.model_validate(entry.model_dump()) == entry


def test_parsed_food_entry_meal_round_trip():
    entry = ParsedFoodEntry(
        entry_type="meal",
        occurred_at_local=datetime.datetime(2024, 1, 15, 21, 30),
        notes="big pasta dinner",
    )
    assert ParsedFoodEntry.model_validate(entry.model_dump()) == entry


def test_parsed_food_entry_rejects_aware_datetime():
    with pytest.raises(Exception):
        ParsedFoodEntry(
            entry_type="meal",
            occurred_at_local=datetime.datetime(2024, 1, 15, 21, 30, tzinfo=datetime.timezone.utc),
        )


def test_food_log_round_trip():
    log = FoodLog(
        date=datetime.date(2024, 1, 15),
        entry_type="meal",
        occurred_at_utc=datetime.datetime(2024, 1, 16, 5, 30, tzinfo=datetime.timezone.utc),
        notes="big pasta dinner",
        raw_message="dinner at 9:30",
    )
    assert FoodLog.model_validate(log.model_dump()) == log


def test_food_log_caffeine_round_trip():
    log = FoodLog(
        date=datetime.date(2024, 1, 15),
        entry_type="caffeine",
        occurred_at_utc=datetime.datetime(2024, 1, 15, 22, 0, tzinfo=datetime.timezone.utc),
        caffeine_mg=100.0,
        raw_message="coffee at 2pm",
    )
    assert FoodLog.model_validate(log.model_dump()) == log


def test_food_log_rejects_naive_utc():
    with pytest.raises(Exception):
        FoodLog(
            date=datetime.date(2024, 1, 15),
            entry_type="meal",
            occurred_at_utc=datetime.datetime(2024, 1, 16, 5, 30),  # naive — should fail
            raw_message="dinner",
        )
