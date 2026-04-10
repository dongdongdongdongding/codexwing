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
30 18 * * * cd ${PROJECT_ROOT} && DAILY_OPS_MARKETS=KOSPI,KOSDAQ,NASDAQ DAILY_OPS_DRY_RUN=0 AG_STALE_FALLBACK_ALERT_DRY_RUN=0 /bin/bash multi_agent/tools/run_daily_ops.sh >> ${LOG_DIR}/cron_daily_ops_1830.log 2>&1 # codex_swing_daily_ops_1830
30 23 * * * cd ${PROJECT_ROOT} && DAILY_OPS_MARKETS=KOSPI,KOSDAQ,NASDAQ DAILY_OPS_DRY_RUN=0 AG_STALE_FALLBACK_ALERT_DRY_RUN=0 /bin/bash multi_agent/tools/run_daily_ops.sh >> ${LOG_DIR}/cron_daily_ops_2330.log 2>&1 # codex_swing_daily_ops_2330
EOF

crontab "${TMP_CRON}"
echo "[OK] Installed daily ops cron schedule:"
crontab -l | grep 'codex_swing_daily_ops_' || true
