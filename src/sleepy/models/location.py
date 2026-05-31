"""Pydantic schema for away-night tracking.

AwayNight represents a single night the user slept away from home.
Sensor data (temperature, humidity, CO2, light) is not meaningful on these
nights and should be excluded from environment analysis.
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel


class AwayNight(BaseModel):
    """One night when the user slept away from home."""

    date: datetime.date
    note: str | None = None  # optional freetext, e.g. "camping" or "airbnb Seattle"
