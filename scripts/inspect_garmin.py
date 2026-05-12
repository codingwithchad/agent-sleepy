"""One-off script to inspect raw Garmin sleep data. Not for production use."""

import logging

logging.basicConfig(level=logging.INFO)

from sleepy.ingest.garmin import fetch_sleep_nights  # noqa: E402

nights = fetch_sleep_nights(days=3)

if not nights:
    print("No nights returned — check credentials or device sync.")
else:
    for n in nights:
        print(n.model_dump_json(indent=2))
