#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"
mkdir -p runtime_state/discord_jobs

# 슬래시 명령어 자동 등록(코드 변경분 반영). guild scope면 즉시. 실패해도 봇은 기동.
echo "[STEP] discord slash-command 등록"
python3 -c "from modules.discord_integration.config import load_discord_config; from modules.discord_integration.register import register_application_commands; r=register_application_commands(load_discord_config(), dry_run=False); print('[OK] registered', r.get('commands'))" \
  || echo "[WARN] command register failed (봇은 계속 기동)"

exec /usr/bin/env python3 -u multi_agent/tools/discord_bot.py
