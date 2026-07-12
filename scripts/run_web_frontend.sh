#!/usr/bin/env bash
# 신웹 프론트 로컬 서버 (vite dev, 5173) — launchd KeepAlive 용 foreground 실행.
# 수동 npm run dev는 터미널 종료/재부팅 시 죽는 부채 → 백엔드와 동일하게 launchd 관리 (2026-07-10).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/../web/frontend"
export PATH="/usr/local/bin:/opt/homebrew/bin:${PATH}"
exec npm run dev -- --host 127.0.0.1 --port "${WEB_FRONTEND_PORT:-5173}"
