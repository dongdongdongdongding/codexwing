#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
APP_SUPPORT_DIR="${HOME}/Library/Application Support/CodexSwing"
BIN_DIR="${APP_SUPPORT_DIR}/bin"
LOG_DIR="${APP_SUPPORT_DIR}/logs/ops"
ROOT_FILE="${APP_SUPPORT_DIR}/project_root"
LAUNCHER_PATH="${BIN_DIR}/codex_swing_launch.sh"
PLIST_PATH="${LAUNCH_AGENTS_DIR}/com.codex.swing.dailyops.plist"
mkdir -p "${LAUNCH_AGENTS_DIR}" "${LOG_DIR}" "${BIN_DIR}"

cat > "${ROOT_FILE}" <<EOF
${PROJECT_ROOT}
EOF

cat > "${LAUNCHER_PATH}" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

APP_SUPPORT_DIR="${HOME}/Library/Application Support/CodexSwing"
ROOT_FILE="${APP_SUPPORT_DIR}/project_root"

resolve_root() {
  if [[ -n "${CODEX_SWING_PROJECT_ROOT:-}" && -f "${CODEX_SWING_PROJECT_ROOT}/AGENTS.md" && -f "${CODEX_SWING_PROJECT_ROOT}/app.py" ]]; then
    printf "%s" "${CODEX_SWING_PROJECT_ROOT}"
    return 0
  fi

  if [[ -f "${ROOT_FILE}" ]]; then
    local saved_root
    saved_root="$(tr -d '\r' < "${ROOT_FILE}")"
    if [[ -f "${saved_root}/AGENTS.md" && -f "${saved_root}/app.py" ]]; then
      printf "%s" "${saved_root}"
      return 0
    fi
  fi

  local candidates=(
    "${HOME}/Projects/codex_swing/swing-main"
    "${HOME}/Desktop/codex_swing/swing-main"
    "${HOME}/codex_swing/swing-main"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -f "${candidate}/AGENTS.md" && -f "${candidate}/app.py" ]]; then
      printf "%s" "${candidate}"
      return 0
    fi
  done

  return 1
}

PROJECT_ROOT="$(resolve_root)" || {
  echo "[ERROR] CodexSwing project root not found" >&2
  exit 1
}

cd "${PROJECT_ROOT}"
exec "$@"
EOF

chmod +x "${LAUNCHER_PATH}"

cat > "${PLIST_PATH}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.codex.swing.dailyops</string>
  <key>ProgramArguments</key>
  <array>
    <string>${LAUNCHER_PATH}</string>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>DAILY_OPS_MARKETS=KOSPI,KOSDAQ,NASDAQ,AMEX DAILY_OPS_DRY_RUN=0 AG_STALE_FALLBACK_ALERT_DRY_RUN=0 /bin/bash multi_agent/tools/run_daily_ops.sh</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${APP_SUPPORT_DIR}</string>
  <key>RunAtLoad</key>
  <true/>
  <key>StartCalendarInterval</key>
  <array>
    <dict>
      <key>Hour</key>
      <integer>18</integer>
      <key>Minute</key>
      <integer>30</integer>
    </dict>
    <dict>
      <key>Hour</key>
      <integer>23</integer>
      <key>Minute</key>
      <integer>30</integer>
    </dict>
  </array>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/launchd_daily_ops.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/launchd_daily_ops.err.log</string>
</dict>
</plist>
EOF

launchctl unload "${PLIST_PATH}" >/dev/null 2>&1 || true
launchctl load "${PLIST_PATH}"

echo "[OK] Installed launchd schedule: ${PLIST_PATH}"
echo "[OK] Project root file: ${ROOT_FILE}"
echo "[OK] Launcher path: ${LAUNCHER_PATH}"
launchctl list | grep "com.codex.swing.dailyops" || true
