#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

mkdir -p runtime_state/discord_jobs /tmp/matplotlib

export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/matplotlib}"
export DISCORD_DRY_RUN="${DISCORD_DRY_RUN:-0}"
export DISCORD_ENABLE_SCAN_EXECUTION="${DISCORD_ENABLE_SCAN_EXECUTION:-1}"
export AG_TOP_DEEP_N="${AG_TOP_DEEP_N:-10}"
export AG_TOP_DEEP_WRITE_DB="${AG_TOP_DEEP_WRITE_DB:-1}"
export AG_KR_DAILY_PHASE="${AG_KR_DAILY_PHASE:-confirmed}"

exec /usr/bin/env python3 -u multi_agent/tools/run_kr_daily_auto_scans.py --phase "${AG_KR_DAILY_PHASE}"
