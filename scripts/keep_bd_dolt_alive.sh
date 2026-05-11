#!/usr/bin/env bash
set -u

REPO_DIR="/Users/dongdong/Projects/codex_swing/swing-main"
LOG_DIR="${REPO_DIR}/.beads"
LOG_FILE="${LOG_DIR}/bd-dolt-keepalive.log"
export PATH="/Users/dongdong/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

mkdir -p "${LOG_DIR}"
cd "${REPO_DIR}" || exit 1

ts() {
  date '+%Y-%m-%d %H:%M:%S'
}

if bd dolt test >/dev/null 2>&1; then
  printf '%s OK bd dolt connection\n' "$(ts)" >> "${LOG_FILE}"
  exit 0
fi

printf '%s WARN bd dolt connection failed; starting server\n' "$(ts)" >> "${LOG_FILE}"
bd dolt start >> "${LOG_FILE}" 2>&1
sleep 2

if bd dolt test >/dev/null 2>&1; then
  printf '%s OK bd dolt recovered\n' "$(ts)" >> "${LOG_FILE}"
  exit 0
fi

printf '%s ERROR bd dolt still unavailable after restart\n' "$(ts)" >> "${LOG_FILE}"
exit 1
