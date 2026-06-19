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

echo "[STEP] backfill_scanner_full_returns"
run_optional "backfill_scanner_full_returns" \
  python3 multi_agent/tools/backfill_scanner_full_returns.py --limit-runs "${BACKFILL_RETURN_LIMIT_RUNS:-1000}"

echo "[STEP] export_scan_archive_learning_dataset"
run_optional "export_scan_archive_learning_dataset" \
  python3 multi_agent/tools/export_scan_archive_learning_dataset.py --market ALL --quality-tier "${ARCHIVE_LEARNING_QUALITY_TIER:-ALL}"

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

  if [[ "${MARKET}" == "KOSPI" || "${MARKET}" == "KOSDAQ" ]]; then
    echo "[STEP] build_paper_trade_ledger market=${MARKET}"
    PAPER_LEDGER_ARGS=(--market "${MARKET}" --scan-mode SWING --topn "${PAPER_LEDGER_TOPN:-5}"
      --fee-bps "${PAPER_LEDGER_FEE_BPS:-0}" --slippage-bps "${PAPER_LEDGER_SLIPPAGE_BPS:-0}")
    if [[ "${PAPER_LEDGER_WRITE_DB:-1}" == "1" ]]; then
      PAPER_LEDGER_ARGS+=(--write-db)
    fi
    run_optional "build_paper_trade_ledger:${MARKET}" \
      python3 multi_agent/tools/build_paper_trade_ledger.py "${PAPER_LEDGER_ARGS[@]}"

    echo "[STEP] report_kr_walkforward_release_gate market=${MARKET}"
    run_optional "report_kr_walkforward_release_gate:${MARKET}" \
      python3 multi_agent/tools/report_kr_walkforward_release_gate.py --market "${MARKET}"

    echo "[STEP] report_kr_cohort_release_gate market=${MARKET}"
    run_optional "report_kr_cohort_release_gate:${MARKET}" \
      python3 multi_agent/tools/report_kr_cohort_release_gate.py --market "${MARKET}" \
        --confidence "${AG_KR_COHORT_GATE_CONFIDENCE:-0.95}"
  fi

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

echo "[STEP] report_dynamic_theme_entry_profiles"
run_optional "report_dynamic_theme_entry_profiles" \
  python3 multi_agent/tools/report_dynamic_theme_entry_profiles.py

echo "[STEP] report_scan_cohort_performance"
run_optional "report_scan_cohort_performance" \
  python3 multi_agent/tools/report_scan_cohort_performance.py

if [[ "${AG_OPERATIONAL_ADMISSION_OPTIMIZER_ENABLE:-1}" == "1" ]]; then
  echo "[STEP] operational_admission_optimizer"
  run_optional "operational_admission_optimizer" \
    python3 multi_agent/tools/operational_admission_optimizer.py \
      --input runtime_state/reports/archive/scan_archive_learning_dataset_all.csv \
      --output-dir runtime_state/reports/experimental \
      --stem operational_admission_optimizer_latest
fi

if [[ "${AG_OPERATIONAL_ADMISSION_OPTIMIZER_KOSDAQ_THEME_ENABLE:-1}" == "1" ]]; then
  echo "[STEP] operational_admission_optimizer_kosdaq_theme"
  run_optional "operational_admission_optimizer_kosdaq_theme" \
    python3 multi_agent/tools/operational_admission_optimizer.py \
      --input runtime_state/reports/archive/scan_archive_learning_dataset_all.csv \
      --output-dir runtime_state/reports/experimental \
      --stem operational_admission_optimizer_kosdaq_theme_latest \
      --markets KOSDAQ \
      --include-theme
fi

if [[ "${AG_EXIT_POLICY_WATCH_ENABLE:-1}" == "1" ]]; then
  echo "[STEP] report_exit_policy_watch"
  run_optional "report_exit_policy_watch" \
    python3 multi_agent/tools/report_exit_policy_watch.py
fi

if [[ "${AG_REGIME_SIGNAL_SHADOW_ENABLE:-1}" == "1" ]]; then
  echo "[STEP] report_regime_signal_shadow"
  run_optional "report_regime_signal_shadow" \
    python3 multi_agent/tools/report_regime_signal_shadow.py \
      --top-universe "${AG_REGIME_SIGNAL_TOP_UNIVERSE:-120}" --top-picks "${AG_REGIME_SIGNAL_TOP_PICKS:-10}"
fi

if [[ "${AG_FIRSTTOUCH_DOWN_SHADOW_ENABLE:-0}" == "1" ]]; then
  # DISABLED by default (2026-06-19): the DOWN-market "edge" was shown to be rebound beta, not
  # flow selection (same-day control + market-neutral + liquidity tests all failed). See memory
  # daily_selection_closed_final. Kept behind a flag for reference; do NOT promote to production.
  # Calibrated first-touch DOWN-market emission (models/firsttouch_down_v1.pkl). Observation-only:
  # writes ledger + report; routes picks to live web/Discord only when AG_FIRSTTOUCH_DOWN_PRODUCTION=1.
  echo "[STEP] report_firsttouch_down_shadow"
  run_optional "report_firsttouch_down_shadow" \
    python3 multi_agent/tools/report_firsttouch_down_shadow.py \
      --top-universe "${AG_FIRSTTOUCH_TOP_UNIVERSE:-300}" --top-picks "${AG_FIRSTTOUCH_TOP_PICKS:-5}"
fi

if [[ "${AG_KOSPI_NORMAL_PEAD_SHADOW_ENABLE:-0}" == "1" ]]; then
  # DISABLED by default (2026-06-19): the ONLY daily-selection signal that survived the full
  # gauntlet -- KOSPI NORMAL regime + price+flow+coarse-PEAD ensemble + >=100억 + top-5 -- but it
  # is THIN and single-config (event-type expansion AND PEAD fundamental-surprise refinement both
  # failed to robustify it, Case ③). Forward-tracked ONLY to see if the live market-excess holds;
  # do NOT promote to production until the resolved out-of-sample edge confirms. Observation-only:
  # writes ledger + report; routes to live web/Discord only when AG_KOSPI_NORMAL_PEAD_PRODUCTION=1.
  # See memory/daily_selection_closed_final. Needs KIS live calls for the flow tail.
  echo "[STEP] report_kospi_normal_pead_shadow"
  KIS_ENABLE_LIVE_CALLS=1 run_optional "report_kospi_normal_pead_shadow" \
    python3 multi_agent/tools/report_kospi_normal_pead_shadow.py \
      --universe "${AG_KOSPI_NORMAL_PEAD_UNIVERSE:-300}" --min-liq "${AG_KOSPI_NORMAL_PEAD_MIN_LIQ:-100}" \
      --top-picks "${AG_KOSPI_NORMAL_PEAD_TOP_PICKS:-5}"
fi

if [[ "${AG_DRIFT_ALERT_ENABLE:-1}" == "1" ]]; then
  DRIFT_ARGS=()
  if [[ -n "${AG_DRIFT_ALERT_WEBHOOK_URL:-}" ]]; then
    DRIFT_ARGS+=(--webhook-url "${AG_DRIFT_ALERT_WEBHOOK_URL}")
  fi
  if [[ "${AG_DRIFT_ALERT_DRY_RUN:-0}" == "1" ]]; then
    DRIFT_ARGS+=(--dry-run)
  fi
  echo "[STEP] emit_daily_backtest ${DRIFT_ARGS[*]}"
  run_optional "emit_daily_backtest" \
    python3 multi_agent/tools/emit_daily_backtest.py "${DRIFT_ARGS[@]}"
fi

if [[ "${AG_DAILY_MODEL_FOUNDATION_GATE_ENABLE:-1}" == "1" ]]; then
  echo "[STEP] report_daily_model_foundation_gate"
  run_optional "report_daily_model_foundation_gate" \
    python3 multi_agent/tools/report_daily_model_foundation_gate.py
fi

echo "[DONE] daily_ops completed"
