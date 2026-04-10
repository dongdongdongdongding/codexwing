#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
APP_SUPPORT_DIR="${HOME}/Library/Application Support/CodexSwing"
BIN_DIR="${APP_SUPPORT_DIR}/bin"
LOG_DIR="${APP_SUPPORT_DIR}/logs/learning"
ROOT_FILE="${APP_SUPPORT_DIR}/project_root"
LAUNCHER_PATH="${BIN_DIR}/codex_swing_launch.sh"
NIGHTLY_PLIST="${LAUNCH_AGENTS_DIR}/com.codex.swing.learning.nightly.plist"
WEEKLY_PLIST="${LAUNCH_AGENTS_DIR}/com.codex.swing.learning.weekly.plist"

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

cat > "${NIGHTLY_PLIST}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.codex.swing.learning.nightly</string>
  <key>ProgramArguments</key>
  <array>
    <string>${LAUNCHER_PATH}</string>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>python3 multi_agent/tools/run_learning_cycle.py --mode nightly --nightly-min-new-resolved ${AG_LEARNING_NIGHTLY_MIN_NEW_RESOLVED:-20}</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${APP_SUPPORT_DIR}</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>23</integer>
    <key>Minute</key>
    <integer>50</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/nightly_learning.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/nightly_learning.err.log</string>
</dict>
</plist>
EOF

cat > "${WEEKLY_PLIST}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.codex.swing.learning.weekly</string>
  <key>ProgramArguments</key>
  <array>
    <string>${LAUNCHER_PATH}</string>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>python3 multi_agent/tools/run_learning_cycle.py --mode weekly --weekly-min-total-resolved ${AG_LEARNING_WEEKLY_MIN_TOTAL_RESOLVED:-50} --weekly-min-new-resolved ${AG_LEARNING_WEEKLY_MIN_NEW_RESOLVED:-10}</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${APP_SUPPORT_DIR}</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key>
    <integer>7</integer>
    <key>Hour</key>
    <integer>9</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/weekly_learning.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/weekly_learning.err.log</string>
</dict>
</plist>
EOF

launchctl unload "${NIGHTLY_PLIST}" >/dev/null 2>&1 || true
launchctl unload "${WEEKLY_PLIST}" >/dev/null 2>&1 || true
launchctl load "${NIGHTLY_PLIST}"
launchctl load "${WEEKLY_PLIST}"

echo "[OK] Installed nightly learning schedule: ${NIGHTLY_PLIST}"
echo "[OK] Installed weekly learning schedule: ${WEEKLY_PLIST}"
echo "[OK] Project root file: ${ROOT_FILE}"
echo "[OK] Launcher path: ${LAUNCHER_PATH}"
launchctl list | grep "com.codex.swing.learning" || true
