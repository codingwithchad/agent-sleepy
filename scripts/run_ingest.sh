#!/bin/bash
# Wrapper called by Windows Task Scheduler via wsl.exe.
# Runs the nightly Garmin ingest and appends output to data/ingest.log.
set -e
export PATH="$HOME/.local/bin:$PATH"
cd /home/codingwithchad/code/agent-sleepy
mkdir -p data
uv run python -m sleepy.jobs.nightly_ingest >> data/ingest.log 2>&1
