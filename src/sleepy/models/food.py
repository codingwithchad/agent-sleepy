"""Pydantic schemas for food/drink log entries.

ParsedFoodEntry — structured output from the LLM parser. One entry per message.
FoodLog        — canonical store model. One row per logged event in the database.
"""

from __future__ import annotations

import datetime
from typing import Literal

from pydantic import BaseModel, field_validator


class ParsedFoodEntry(BaseModel):
    """Structured food/drink entry extracted from a natural-language message.

    Returned by the LLM parser in coach/food_parser.py. Not persisted directly —
    the calling code converts this to a FoodLog before writing to the database.

    occurred_at_local is naive (no tzinfo) — it's the user's local time as stated
    in the message. The caller is responsible for UTC conversion.
    """

    entry_type: Literal["meal", "caffeine", "alcohol", "unknown"]
    occurred_at_local: datetime.datetime  # naive, America/Los_Angeles
    caffeine_mg: float | None = None
    alcohol_drinks: float | None = None  # standard drinks (14g alcohol each)
    notes: str | None = None

    @field_validator("occurred_at_local", mode="after")
    @classmethod
    def must_be_naive(cls, v: datetime.datetime) -> datetime.datetime:
        if v.tzinfo is not None:
            raise ValueError("occurred_at_local must be a naive datetime (no tzinfo)")
        return v


class FoodLog(BaseModel):
    """One food/drink event stored in the database.

    All timestamps are UTC. entry_type drives which optional fields are
    meaningful — caffeine_mg for caffeine, alcohol_drinks for alcohol,
    notes for meals. date is the local calendar date (America/Los_Angeles).
    """

    id: int | None = None  # None until persisted; DB assigns autoincrement
    date: datetime.date  # local calendar date of the event
    entry_type: Literal["meal", "caffeine", "alcohol", "unknown"]
    occurred_at_utc: datetime.datetime
    caffeine_mg: float | None = None
    alcohol_drinks: float | None = None
    notes: str | None = None
    raw_message: str  # original Telegram text — useful for debugging bad parses

    @field_validator("occurred_at_utc", mode="after")
    @classmethod
    def must_be_utc(cls, v: datetime.datetime) -> datetime.datetime:
        if v.tzinfo is None:
            raise ValueError("occurred_at_utc must be timezone-aware (UTC)")
        return v
