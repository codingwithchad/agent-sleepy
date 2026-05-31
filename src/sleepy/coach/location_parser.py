"""LLM-based parser for away-date specifications in natural language.

parse_away_dates is the seam between the user's /away command text and a list
of calendar dates. Same pattern as food_parser — swap implementations freely
as long as the signature holds:

    def parse_away_dates(
        text: str,
        today: datetime.date,
        client: anthropic.Anthropic | None = None,
    ) -> list[datetime.date]: ...

This module never calls the database.
"""

from __future__ import annotations

import datetime
import os

import anthropic
from dotenv import find_dotenv, load_dotenv

from sleepy.config import ANTHROPIC_MODEL

load_dotenv(find_dotenv(raise_error_if_not_found=False, usecwd=True))

_PARSE_DATES_TOOL: dict = {
    "name": "record_away_dates",
    "description": "Record the list of calendar dates when the user will be away from home.",
    "input_schema": {
        "type": "object",
        "properties": {
            "dates": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "List of ISO 8601 dates (YYYY-MM-DD) when the user is away. "
                    "Expand ranges into individual dates (e.g. 'June 14 to 16' → "
                    "['2026-06-14', '2026-06-15', '2026-06-16']). "
                    "If no year is given, use today's year; roll to next year only "
                    "if the date has already passed."
                ),
            }
        },
        "required": ["dates"],
    },
}


def parse_away_dates(
    text: str,
    today: datetime.date,
    client: anthropic.Anthropic | None = None,
) -> list[datetime.date]:
    """Parse natural-language away-date text into a sorted list of calendar dates.

    Args:
        text:   Text after the /away or /home command, e.g. "June 14 to 16" or
                "June 14, 15, and 16" or "this weekend".
        today:  Today's local date — needed to resolve relative references and
                fill in missing years.
        client: Optional Anthropic client — inject in tests to avoid real API calls.

    Returns a sorted list of datetime.date objects. Returns an empty list if
    the LLM couldn't extract any dates (caller should handle gracefully).

    Raises anthropic.APIError on network or quota failures.
    """
    if client is None:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=256,
        system=(
            "You extract calendar dates from text for a sleep-tracking app. "
            "The user is telling you which nights they will sleep away from home. "
            "Call record_away_dates with the expanded list of individual dates."
        ),
        tools=[_PARSE_DATES_TOOL],
        tool_choice={"type": "tool", "name": "record_away_dates"},
        messages=[
            {
                "role": "user",
                "content": f"Today is {today.isoformat()}.\n\n{text}",
            }
        ],
    )

    tool_input: dict = {}
    for block in response.content:
        if block.type == "tool_use":
            tool_input = block.input
            break

    raw_dates: list[str] = tool_input.get("dates", [])
    parsed = [datetime.date.fromisoformat(d) for d in raw_dates]
    return sorted(parsed)
