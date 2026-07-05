#!/usr/bin/env bash
# 신웹 FastAPI 백엔드 (launchd KeepAlive 용 — foreground 실행).
# 이전엔 수동 nohup 기동이라 재부팅 시 죽는 운영 부채가 있었음 (2026-07-05 정비).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"
mkdir -p runtime_state/local_short_term

exec python3 -m uvicorn web.backend.main:app --host 127.0.0.1 --port "${WEB_BACKEND_PORT:-8800}"
