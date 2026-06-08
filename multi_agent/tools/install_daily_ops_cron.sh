#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/runtime_state/long_term/ops"
mkdir -p "${LOG_DIR}"

TMP_CRON="$(mktemp)"
EXISTING="$(mktemp)"
trap 'rm -f "${TMP_CRON}" "${EXISTING}"' EXIT

crontab -l 2>/dev/null > "${EXISTING}" || true
grep -v 'codex_swing_daily_ops_' "${EXISTING}" > "${TMP_CRON}" || true

cat >> "${TMP_CRON}" <<EOF
*/5 * * * * cd ${PROJECT_ROOT} && PRIMARY_OPS_MARKETS=KOSPI,KOSDAQ,NASDAQ DAILY_OPS_DRY_RUN=0 AG_STALE_FALLBACK_ALERT_DRY_RUN=0 python3 multi_agent/tools/run_primary_market_session_ops.py --run-due --continue-on-error >> ${LOG_DIR}/cron_primary_market_session_ops.log 2>&1 # codex_swing_daily_ops_due
EOF

crontab "${TMP_CRON}"
echo "[OK] Installed primary market session ops cron schedule:"
crontab -l | grep 'codex_swing_daily_ops_' || true
