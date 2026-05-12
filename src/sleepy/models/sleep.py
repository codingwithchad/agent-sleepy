"""Pydantic schema for a single night of sleep from Garmin."""

from __future__ import annotations

import datetime

from pydantic import BaseModel, field_validator


class GarminSleepNight(BaseModel):
    """One night of sleep as recorded by Garmin Connect.

    All timestamps are UTC. Durations are in whole minutes.
    Fields that Garmin may not always return (e.g. no HRV on older devices)
    are Optional.
    """

    date: datetime.date
    sleep_start_utc: datetime.datetime
    sleep_end_utc: datetime.datetime
    duration_min: int  # deep + light + rem (excludes awake time)
    score: int | None = None  # overall sleep score 0–100
    deep_min: int | None = None
    light_min: int | None = None
    rem_min: int | None = None
    awake_min: int | None = None
    avg_hrv: float | None = None
    avg_respiration: float | None = None
    restless_moments: int | None = None
    sleep_latency_min: int | None = None  # time from in-bed to first sleep

    @field_validator("sleep_start_utc", "sleep_end_utc", mode="after")
    @classmethod
    def must_be_utc(cls, v: datetime.datetime) -> datetime.datetime:
        if v.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware (UTC)")
        return v
