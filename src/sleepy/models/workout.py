"""Pydantic schemas for workout/activity data.

GarminActivity — raw device model, Garmin-specific field names.
Workout        — canonical store model, device-agnostic. One row per activity
                 per source in the database.
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, field_validator


class GarminActivity(BaseModel):
    """One activity as recorded by Garmin Connect.

    All timestamps are UTC. Duration is in whole minutes.
    Fields that Garmin may not always return are Optional.
    """

    activity_id: int  # Garmin's stable numeric ID
    date: datetime.date  # UTC calendar date of activity start
    name: str | None = None  # user-assigned activity name
    activity_type: str  # e.g. "running", "cycling", "strength_training"
    start_time_utc: datetime.datetime
    end_time_utc: datetime.datetime
    duration_min: int  # total activity duration
    avg_hr: int | None = None
    max_hr: int | None = None
    calories: int | None = None
    aerobic_te: float | None = None  # aerobic training effect 1.0–5.0
    anaerobic_te: float | None = None  # anaerobic training effect 1.0–5.0
    hr_zone_1_min: int | None = None  # very light (< ~60% max HR)
    hr_zone_2_min: int | None = None  # light (aerobic base)
    hr_zone_3_min: int | None = None  # moderate (aerobic)
    hr_zone_4_min: int | None = None  # hard (threshold)
    hr_zone_5_min: int | None = None  # max (anaerobic)

    @field_validator("start_time_utc", "end_time_utc", mode="after")
    @classmethod
    def must_be_utc(cls, v: datetime.datetime) -> datetime.datetime:
        if v.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware (UTC)")
        return v


class Workout(BaseModel):
    """Canonical, device-agnostic workout record stored in the database.

    All timestamps are UTC. Duration is in whole minutes.
    For late-night correlation, use start_time_utc directly — the date field
    is the UTC calendar date, which may differ from local date for evening
    workouts near midnight.
    """

    activity_id: int  # source's stable ID — natural dedup key
    source: str  # "garmin" | future sources
    date: datetime.date  # UTC calendar date of activity start
    name: str | None = None
    activity_type: str
    start_time_utc: datetime.datetime
    end_time_utc: datetime.datetime
    duration_min: int
    avg_hr: int | None = None
    max_hr: int | None = None
    calories: int | None = None
    aerobic_te: float | None = None
    anaerobic_te: float | None = None
    hr_zone_1_min: int | None = None
    hr_zone_2_min: int | None = None
    hr_zone_3_min: int | None = None
    hr_zone_4_min: int | None = None
    hr_zone_5_min: int | None = None

    @field_validator("start_time_utc", "end_time_utc", mode="after")
    @classmethod
    def must_be_utc(cls, v: datetime.datetime) -> datetime.datetime:
        if v.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware (UTC)")
        return v
