"""LLM-based parser for natural-language food/drink log messages.

parse_food_message is the single seam between user text and structured data.
To swap in a regex-based parser (e.g. to save tokens on weekdays), replace
this function — the signature is stable:

    def parse_food_message(
        message: str,
        now_local: datetime.datetime,
        client: anthropic.Anthropic | None = None,
    ) -> ParsedFoodEntry: ...

This module never calls the database. It returns a ParsedFoodEntry;
the caller (telegram_bot.py) is responsible for persisting it.
"""

from __future__ import annotations

import datetime
import os

import anthropic
from dotenv import find_dotenv, load_dotenv

from sleepy.config import ANTHROPIC_MODEL
from sleepy.models.food import ParsedFoodEntry

load_dotenv(find_dotenv(raise_error_if_not_found=False, usecwd=True))

# Tool schema that forces the LLM to return structured food log data.
_LOG_ENTRY_TOOL: dict = {
    "name": "log_food_entry",
    "description": "Record a food, drink, or caffeine event from the user's message.",
    "input_schema": {
        "type": "object",
        "properties": {
            "entry_type": {
                "type": "string",
                "enum": ["meal", "caffeine", "alcohol", "unknown"],
                "description": "Category of the log entry.",
            },
            "occurred_at_local": {
                "type": "string",
                "description": (
                    "ISO 8601 datetime in the user's local time, e.g. "
                    "'2024-01-15T21:30:00'. Use the date from current_local_time "
                    "unless the user says 'last night' or 'yesterday', in which case "
                    "subtract one day."
                ),
            },
            "caffeine_mg": {
                "type": "number",
                "description": (
                    "Caffeine in milligrams. Estimate if not stated: "
                    "drip coffee ~100mg, espresso/shot ~64mg, tea ~40mg, "
                    "energy drink ~80–160mg. Null if not a caffeine entry."
                ),
            },
            "alcohol_drinks": {
                "type": "number",
                "description": (
                    "Standard drinks (14g alcohol each). Null if not an alcohol entry."
                ),
            },
            "notes": {
                "type": "string",
                "description": (
                    "Brief description of what was consumed, "
                    "e.g. 'big pasta dinner' or 'espresso'. Null if nothing to add."
                ),
            },
        },
        "required": ["entry_type", "occurred_at_local"],
    },
}


def parse_food_message(
    message: str,
    now_local: datetime.datetime,
    client: anthropic.Anthropic | None = None,
) -> ParsedFoodEntry:
    """Parse a natural-language food/drink message into a structured entry.

    Args:
        message:   Raw text from the user, e.g. "coffee at 2, big dinner around 9pm".
        now_local: Current local datetime (naive, America/Los_Angeles). Lets the LLM
                   resolve relative times like "two hours ago".
        client:    Optional Anthropic client — inject in tests to avoid real API calls.

    Returns a ParsedFoodEntry with occurred_at_local as a naive datetime.

    If a message contains multiple items (e.g. "coffee at 2 and dinner at 8"),
    the LLM logs the most sleep-relevant one — caffeine and late meals take priority.
    Have the user send separate messages if both need to be logged.

    Raises anthropic.APIError on network or quota failures — let the caller handle it.
    """
    if client is None:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    system = (
        "You are a food log assistant for a sleep-tracking app. "
        "The user sends short, casual messages about what they ate or drank. "
        "Extract the relevant data and call log_food_entry. "
        "If a message describes multiple items, log only the most sleep-relevant one "
        "— caffeine and late meals take priority over earlier meals or snacks."
    )

    user_content = f"Current local time: {now_local.strftime('%Y-%m-%d %H:%M')}\n\n{message}"

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=256,
        system=system,
        tools=[_LOG_ENTRY_TOOL],
        tool_choice={"type": "tool", "name": "log_food_entry"},
        messages=[{"role": "user", "content": user_content}],
    )

    # tool_choice forces exactly one tool_use block.
    tool_input: dict = {}
    for block in response.content:
        if block.type == "tool_use":
            tool_input = block.input
            break

    occurred_at_local = datetime.datetime.fromisoformat(tool_input["occurred_at_local"])

    return ParsedFoodEntry(
        entry_type=tool_input["entry_type"],
        occurred_at_local=occurred_at_local,
        caffeine_mg=tool_input.get("caffeine_mg"),
        alcohol_drinks=tool_input.get("alcohol_drinks"),
        notes=tool_input.get("notes"),
    )
