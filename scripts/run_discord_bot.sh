#!/usr/bin/env bash
set -euo pipefail

cd /Users/dongdong/Projects/codex_swing/swing-main
mkdir -p runtime_state/discord_jobs

exec /usr/bin/env python3 -u multi_agent/tools/discord_bot.py
