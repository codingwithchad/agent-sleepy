"""Pydantic schemas for sleep data.

GarminSleepNight — raw device model, Garmin-specific field names.
SleepNight       — canonical store model, device-agnostic. One row per night
                   per source in the database. Future devices (Oura, Whoop)
                   map into this same shape via their own ingest mappers.
"""

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


class SleepNight(BaseModel):
    """Canonical, device-agnostic sleep record stored in the database.

    All timestamps are UTC. Durations are in whole minutes.
    Score is normalized to 0–100 regardless of source device.
    Optional fields may be absent depending on device capabilities.
    """

    date: datetime.date
    source: str  # "garmin" | "oura" | "whoop" | etc.
    sleep_start_utc: datetime.datetime
    sleep_end_utc: datetime.datetime
    duration_min: int  # total sleep time (excludes awake periods)
    score: int | None = None
    deep_min: int | None = None
    light_min: int | None = None
    rem_min: int | None = None
    awake_min: int | None = None
    avg_hrv: float | None = None
    avg_respiration: float | None = None
    restless_moments: int | None = None
    sleep_latency_min: int | None = None

    @field_validator("sleep_start_utc", "sleep_end_utc", mode="after")
    @classmethod
    def must_be_utc(cls, v: datetime.datetime) -> datetime.datetime:
        if v.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware (UTC)")
        return v
