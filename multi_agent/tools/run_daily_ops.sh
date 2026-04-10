#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${PROJECT_ROOT}"

DATE_TARGET="${DATE_TARGET:-$(date +%F)}"
MARKETS_CSV="${DAILY_OPS_MARKETS:-${DAILY_OPS_MARKET:-KOSDAQ}}"
LIMIT_RUNS="${DAILY_OPS_LIMIT_RUNS:-200}"
DRY_RUN="${DAILY_OPS_DRY_RUN:-0}"
RESOLVE_ALL="${DAILY_OPS_RESOLVE_ALL:-0}"
REFRESH_SIGNAL_PERF="${DAILY_OPS_REFRESH_SIGNAL_PERFORMANCE:-0}"

run_optional() {
  local label="$1"
  shift
  if "$@"; then
    echo "[OK] ${label}"
  else
    echo "[WARN] ${label} failed (continuing)"
  fi
}

trim() {
  local x="$1"
  x="${x#"${x%%[![:space:]]*}"}"
  x="${x%"${x##*[![:space:]]}"}"
  printf "%s" "${x}"
}

IFS=',' read -r -a RAW_MARKETS <<< "${MARKETS_CSV}"
MARKETS=()
for raw in "${RAW_MARKETS[@]}"; do
  val="$(trim "${raw}")"
  if [[ -n "${val}" ]]; then
    MARKETS+=("${val}")
  fi
done
if [[ "${#MARKETS[@]}" -eq 0 ]]; then
  MARKETS=("KOSDAQ")
fi

echo "[INFO] daily_ops start date=${DATE_TARGET} markets=${MARKETS[*]} limit_runs=${LIMIT_RUNS}"

UPDATER_ARGS=(--limit-runs "${LIMIT_RUNS}")
if [[ "${DRY_RUN}" == "1" ]]; then
  UPDATER_ARGS+=(--dry-run)
fi
if [[ "${RESOLVE_ALL}" == "1" ]]; then
  UPDATER_ARGS+=(--resolve-all)
fi
if [[ "${REFRESH_SIGNAL_PERF}" == "1" ]]; then
  UPDATER_ARGS+=(--refresh-signal-performance)
fi
if [[ "${AG_ALLOW_EXPIRE_WITHOUT_DB:-0}" == "1" ]]; then
  UPDATER_ARGS+=(--allow-expire-without-db)
fi

echo "[STEP] update_realized_outcomes ${UPDATER_ARGS[*]}"
python3 multi_agent/tools/update_realized_outcomes.py "${UPDATER_ARGS[@]}"

echo "[STEP] update_outcome_return_metrics"
run_optional "update_outcome_return_metrics" \
  python3 multi_agent/tools/update_outcome_return_metrics.py --limit-runs "${LIMIT_RUNS}"

echo "[STEP] report_outcome_conversion"
run_optional "report_outcome_conversion" \
  python3 multi_agent/tools/report_outcome_conversion.py --limit-runs "${LIMIT_RUNS}"

echo "[STEP] tag_contaminated_runs"
run_optional "tag_contaminated_runs" \
  python3 multi_agent/tools/tag_contaminated_runs.py --limit-runs "${LIMIT_RUNS}"

for MARKET in "${MARKETS[@]}"; do
  echo "[STEP] build_daily_agent_summary market=${MARKET}"
  run_optional "build_daily_agent_summary:${MARKET}" \
    python3 multi_agent/tools/build_daily_agent_summary.py --date "${DATE_TARGET}" --market "${MARKET}" --limit-runs "${LIMIT_RUNS}"

  echo "[STEP] report_outcome_health_db market=${MARKET}"
  run_optional "report_outcome_health_db:${MARKET}" \
    python3 multi_agent/tools/report_outcome_health_db.py --limit "${LIMIT_RUNS}" --market "${MARKET}"

  echo "[STEP] report_fallback_outcome_health_db market=${MARKET}"
  run_optional "report_fallback_outcome_health_db:${MARKET}" \
    python3 multi_agent/tools/report_fallback_outcome_health_db.py --limit-runs "${LIMIT_RUNS}" --market "${MARKET}"

  echo "[STEP] report_prediction_validation market=${MARKET}"
  run_optional "report_prediction_validation:${MARKET}" \
    python3 multi_agent/tools/report_prediction_validation.py --limit-runs "${LIMIT_RUNS}" --market "${MARKET}"

  if [[ "${AG_STALE_FALLBACK_ALERT_ENABLE:-1}" == "1" ]]; then
    ALERT_ARGS=(
      --market "${MARKET}"
      --threshold "${AG_STALE_FALLBACK_ALERT_MIN:-3}"
      --limit-runs "${AG_STALE_FALLBACK_ALERT_LIMIT_RUNS:-200}"
    )
    if [[ -n "${AG_STALE_FALLBACK_ALERT_WEBHOOK_URL:-}" ]]; then
      ALERT_ARGS+=(--webhook-url "${AG_STALE_FALLBACK_ALERT_WEBHOOK_URL}")
    fi
    if [[ "${AG_STALE_FALLBACK_ALERT_DRY_RUN:-0}" == "1" ]]; then
      ALERT_ARGS+=(--dry-run)
    fi
    echo "[STEP] check_stale_fallback_alert ${ALERT_ARGS[*]}"
    run_optional "check_stale_fallback_alert:${MARKET}" \
      python3 multi_agent/tools/check_stale_fallback_alert.py "${ALERT_ARGS[@]}"
  fi
done

echo "[DONE] daily_ops completed"
