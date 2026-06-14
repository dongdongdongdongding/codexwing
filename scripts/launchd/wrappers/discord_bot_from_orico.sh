#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/Volumes/ORICO/quant_pj1"
cd "${PROJECT_ROOT}"
mkdir -p runtime_state/discord_jobs

exec /usr/bin/env python3 -u multi_agent/tools/discord_bot.py
