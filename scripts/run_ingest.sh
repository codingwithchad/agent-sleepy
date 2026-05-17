#!/bin/bash
# Runs the nightly Garmin ingest and appends output to data/ingest.log.
# Derives project root from script location — safe to call from cron on any machine.
set -e
export PATH="$HOME/.local/bin:$PATH"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
mkdir -p data
uv run python -m sleepy.jobs.nightly_ingest >> data/ingest.log 2>&1
