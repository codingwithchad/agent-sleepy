"""Tests for the food log LLM parser.

The Anthropic client is mocked so these run without API keys or network access.
The tests verify that parse_food_message correctly maps tool_use response blocks
to ParsedFoodEntry fields.
"""

import datetime
from unittest.mock import MagicMock

from sleepy.coach.food_parser import parse_food_message


def _mock_client(
    entry_type: str,
    occurred_at_local: str,
    caffeine_mg: float | None = None,
    alcohol_drinks: float | None = None,
    notes: str | None = None,
) -> MagicMock:
    """Build a mock Anthropic client that returns a single tool_use block."""
    tool_input = {
        "entry_type": entry_type,
        "occurred_at_local": occurred_at_local,
    }
    if caffeine_mg is not None:
        tool_input["caffeine_mg"] = caffeine_mg
    if alcohol_drinks is not None:
        tool_input["alcohol_drinks"] = alcohol_drinks
    if notes is not None:
        tool_input["notes"] = notes

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.input = tool_input

    response = MagicMock()
    response.content = [tool_block]

    client = MagicMock()
    client.messages.create.return_value = response
    return client


def test_parse_caffeine_message():
    client = _mock_client(
        entry_type="caffeine",
        occurred_at_local="2024-01-15T14:00:00",
        caffeine_mg=100.0,
        notes="drip coffee",
    )
    result = parse_food_message(
        message="coffee at 2pm",
        now_local=datetime.datetime(2024, 1, 15, 15, 30),
        client=client,
    )

    assert result.entry_type == "caffeine"
    assert result.occurred_at_local == datetime.datetime(2024, 1, 15, 14, 0)
    assert result.caffeine_mg == 100.0
    assert result.notes == "drip coffee"


def test_parse_meal_message():
    client = _mock_client(
        entry_type="meal",
        occurred_at_local="2024-01-15T21:30:00",
        notes="big pasta dinner",
    )
    result = parse_food_message(
        message="big dinner at 9:30",
        now_local=datetime.datetime(2024, 1, 15, 22, 0),
        client=client,
    )

    assert result.entry_type == "meal"
    assert result.occurred_at_local == datetime.datetime(2024, 1, 15, 21, 30)
    assert result.caffeine_mg is None
    assert result.notes == "big pasta dinner"


def test_parse_alcohol_message():
    client = _mock_client(
        entry_type="alcohol",
        occurred_at_local="2024-01-15T19:00:00",
        alcohol_drinks=2.0,
        notes="two glasses of wine at dinner",
    )
    result = parse_food_message(
        message="two glasses of wine at dinner around 7",
        now_local=datetime.datetime(2024, 1, 15, 22, 0),
        client=client,
    )

    assert result.entry_type == "alcohol"
    assert result.occurred_at_local == datetime.datetime(2024, 1, 15, 19, 0)
    assert result.alcohol_drinks == 2.0


def test_now_local_passed_to_api():
    """Verify that now_local is included in the message sent to the API."""
    client = _mock_client(
        entry_type="caffeine",
        occurred_at_local="2024-01-15T13:00:00",
        caffeine_mg=64.0,
    )
    now_local = datetime.datetime(2024, 1, 15, 15, 0)
    parse_food_message(message="espresso a couple hours ago", now_local=now_local, client=client)

    call_args = client.messages.create.call_args
    messages = call_args.kwargs["messages"]
    assert "2024-01-15 15:00" in messages[0]["content"]
