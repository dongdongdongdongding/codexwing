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

if [[ "${AG_KOSPI_NORMAL_PEAD_SHADOW_ENABLE:-1}" == "1" ]]; then
  # NON-EDGE falsification ledger (2026-06-23/24, Claude+Codex). This is NOT a recommendation and
  # NOT a surviving edge: on clean re-verification the KOSPI-NORMAL price+flow+coarse-PEAD candidate
  # scores ~0 market-excess (CI includes 0) against an internally-consistent panel cap-weighted
  # benchmark; the earlier "+1.5%" was an external-KS11 benchmark artifact. Daily production edge = 0.
  # Kept ON only to forward-observe / falsify -- logs the picks the model would make and resolves
  # their 5D return vs BOTH benchmarks (panel_capw_excess = primary, ks11_excess = reference). Never
  # promote: production stays OFF (AG_KOSPI_NORMAL_PEAD_PRODUCTION=0). See memory/
  # daily_selection_closed_final. Needs KIS live calls for the flow tail.
  echo "[STEP] report_kospi_normal_pead_shadow"
  KIS_ENABLE_LIVE_CALLS=1 run_optional "report_kospi_normal_pead_shadow" \
    python3 multi_agent/tools/report_kospi_normal_pead_shadow.py \
      --universe "${AG_KOSPI_NORMAL_PEAD_UNIVERSE:-300}" --min-liq "${AG_KOSPI_NORMAL_PEAD_MIN_LIQ:-100}" \
      --top-picks "${AG_KOSPI_NORMAL_PEAD_TOP_PICKS:-5}"
fi

# --- Research-cache data refresh (keep the model lanes fresh) ------------------------------------
# These run BEFORE the model producers so swing/intraday train + build their universe on current
# data. Sources live in ~/research_cache (outside the repo). Both are date-incremental/idempotent.
if [[ "${AG_PX_LONG_REFRESH:-1}" == "1" && -f "${HOME}/research_cache/build_px_long.py" ]]; then
  # 일봉 px_long: full rebuild to today (PX_REBUILD writes a .tmp then atomic-swaps, so readers keep
  # the old panel until it finishes). Heavy (~30-60min). Disable with AG_PX_LONG_REFRESH=0.
  echo "[STEP] px_long_refresh (일봉)"
  run_optional "px_long_refresh" \
    env PX_REBUILD=1 PX_END="${DATE_TARGET}" python3 "${HOME}/research_cache/build_px_long.py"
fi
if [[ "${AG_INTRADAY_BACKFILL:-1}" == "1" && -f "${HOME}/research_cache/intraday_backfill.py" ]]; then
  # 분봉 minute bars: incremental KIS backfill of today's full session (post-close). Only fetches
  # days not already cached, so the daily run just adds today. Disable with AG_INTRADAY_BACKFILL=0.
  echo "[STEP] intraday_backfill (분봉)"
  run_optional "intraday_backfill" \
    python3 "${HOME}/research_cache/intraday_backfill.py"
fi

# ohlc_daily 증분 갱신: 패널 y3 라벨 + KOSPI 레인 정책수익(EVREG) 라벨의 원천.
# 6/26 정체가 패널 꼬리 라벨 절단을 유발했음(§6). 비활성: AG_OHLC_DAILY_REFRESH=0.
if [[ "${AG_OHLC_DAILY_REFRESH:-1}" == "1" && -f "multi_agent/tools/update_ohlc_daily.py" ]]; then
  echo "[STEP] update_ohlc_daily"
  run_optional "update_ohlc_daily" \
    python3 multi_agent/tools/update_ohlc_daily.py
fi

# 분봉 3D 패널 재구성: report_kospi_intraday_swing._train()이 매 스캔 읽는 학습 패널을
# 최신 분봉(위 backfill)으로 갱신해 항상 최신 거래일까지 학습. 비활성: AG_INTRADAY_PANEL=0.
if [[ "${AG_INTRADAY_PANEL:-1}" == "1" && -f "multi_agent/tools/build_intraday_3d_panel.py" ]]; then
  echo "[STEP] build_intraday_3d_panel (분봉 학습패널)"
  run_optional "build_intraday_3d_panel" \
    python3 multi_agent/tools/build_intraday_3d_panel.py
fi

# DART 공시 증분 갱신 (dart_update.py = 증분; dart_events_bf.py는 6/19 하드코딩이라 사용금지).
# 공시/이벤트 근거 신선도 유지. 비활성: AG_DART_REFRESH=0.
if [[ "${AG_DART_REFRESH:-1}" == "1" && -f "${HOME}/research_cache/dart_update.py" ]]; then
  echo "[STEP] dart_update (공시 증분)"
  run_optional "dart_update" \
    python3 "${HOME}/research_cache/dart_update.py"
fi

# 신용잔고/대주잔고 증분 갱신 (KIS daily_credit_balance, swing-main-5r7t 기계적 수급 데이터).
# 종목당 1콜로 최근 30일 갭 채움 → ~/research_cache/credit.parquet. 비활성: AG_CREDIT_REFRESH=0.
if [[ "${AG_CREDIT_REFRESH:-1}" == "1" && -f "${HOME}/research_cache/credit_update.py" ]]; then
  echo "[STEP] credit_update (신용/대주 잔고 증분)"
  run_optional "credit_update" \
    python3 "${HOME}/research_cache/credit_update.py"
fi

# B 엔진 (signal_class=B, 시장중립 적응형 앙상블, A와 별개). 일봉주기 매일 top10 픽 + forward-shadow.
# 데이터(px_long 위 + flow)가 신선해야 하므로 위 px_long_refresh 다음에 배치. 비활성: AG_B_ENGINE=0.
if [[ "${AG_B_ENGINE:-1}" == "1" && -d "b_engine" ]]; then
  # flow_update.py = 증분 일일 갱신(flow_bf.py는 6/15 하드코딩·기존종목skip이라 안 돎 → 사용금지).
  if [[ -f "${HOME}/research_cache/flow_update.py" ]]; then
    echo "[STEP] b_engine flow_update (외국인/기관 수급 증분)"
    run_optional "b_flow_update" python3 "${HOME}/research_cache/flow_update.py"
  fi
  echo "[STEP] b_engine retrain (적응형 앙상블)"
  run_optional "b_retrain" python3 -m b_engine.model_engine train
  echo "[STEP] b_engine scan (매일 top10 픽)"
  run_optional "b_scan" python3 -m b_engine.model_scan scan
  echo "[STEP] b_engine settle (forward-shadow 채점)"
  run_optional "b_settle" python3 -m b_engine.model_scan settle
fi

if [[ "${AG_NASDAQ_SWING_MODEL_ENABLE:-1}" == "1" ]]; then
  # NASDAQ SWING model lane (2026-06-29): score_alpha3 daily edge, pred alpha5-net-positive
  # gate >=0.60, primary liq20>=30M top10 plus high-liquidity liq20>=100M top5. This is promoted
  # into operations as a model lane, but remains forward-shadow only: it writes
  # nasdaq_swing_daily_edge_shadow_ledger.jsonl and a latest report, then auto-settles alpha5
  # liquidity-matched excess / net-cost / touch3 / dd3 as the feature panel matures.
  NASDAQ_SWING_ARGS=(
    --panel "${AG_NASDAQ_SWING_PANEL:-latest}"
    --market-session "${AG_NASDAQ_SWING_MARKET_SESSION:-${AG_PRIMARY_SESSION_ID:-manual_eod_latest}}"
    --session-cutoff "${AG_NASDAQ_SWING_SESSION_CUTOFF:-${AG_PRIMARY_SESSION_CUTOFF:-}}"
    --source-price-kind "${AG_NASDAQ_SWING_SOURCE_PRICE_KIND:-daily_eod_close}"
    --min-train-rows "${AG_NASDAQ_SWING_MIN_TRAIN_ROWS:-100000}"
    --max-train-rows "${AG_NASDAQ_SWING_MAX_TRAIN_ROWS:-160000}"
    --lgbm-estimators "${AG_NASDAQ_SWING_LGBM_ESTIMATORS:-110}"
  )
  if [[ "${AG_NASDAQ_SWING_ALLOW_NON_FINAL_SESSION:-0}" == "1" ]]; then
    NASDAQ_SWING_ARGS+=(--allow-non-final-session)
  fi
  if [[ "${AG_NASDAQ_SWING_NO_MODEL_BUNDLE:-0}" == "1" ]]; then
    NASDAQ_SWING_ARGS+=(--no-model-bundle)
  fi
  echo "[STEP] report_nasdaq_daily_edge_shadow"
  run_optional "report_nasdaq_daily_edge_shadow" \
    python3 multi_agent/tools/report_nasdaq_daily_edge_shadow.py "${NASDAQ_SWING_ARGS[@]}"
fi

if [[ "${AG_NASDAQ_SESSION_EDGE_ENABLE:-${AG_NASDAQ_SESSION_EDGE_SHADOW_ENABLE:-1}}" == "1" ]]; then
  # NASDAQ regular-close session edge lane (2026-06-30): promotes the strongest recent
  # regular_close session candidate into the operator-enabled new-web scan lane. It still
  # carries sample-limit trace metadata until multi-year 04:00-20:00 ET plus 20:00-04:00 ET
  # overnight coverage clears the shared NASDAQ gates.
  NASDAQ_SESSION_EDGE_ARGS=(
    --panel "${AG_NASDAQ_SESSION_EDGE_PANEL:-latest}"
    --market-session "${AG_NASDAQ_SESSION_EDGE_MARKET_SESSION:-${AG_PRIMARY_SESSION_ID:-manual_regular_close}}"
    --session-cutoff "${AG_NASDAQ_SESSION_EDGE_SESSION_CUTOFF:-${AG_PRIMARY_SESSION_CUTOFF:-}}"
    --max-symbols "${AG_NASDAQ_SESSION_EDGE_MAX_SYMBOLS:-120}"
    --min-liq20 "${AG_NASDAQ_SESSION_EDGE_MIN_LIQ20:-100000000}"
  )
  if [[ "${AG_NASDAQ_SESSION_EDGE_NO_FETCH:-0}" == "1" ]]; then
    NASDAQ_SESSION_EDGE_ARGS+=(--no-fetch)
  fi
  if [[ "${AG_NASDAQ_SESSION_EDGE_REFRESH_CACHE:-0}" == "1" ]]; then
    NASDAQ_SESSION_EDGE_ARGS+=(--refresh-cache)
  fi
  if [[ "${AG_NASDAQ_SESSION_EDGE_NO_MODEL_BUNDLE:-0}" == "1" ]]; then
    NASDAQ_SESSION_EDGE_ARGS+=(--no-model-bundle)
  fi
  echo "[STEP] report_nasdaq_session_edge_shadow"
  run_optional "report_nasdaq_session_edge_shadow" \
    python3 multi_agent/tools/report_nasdaq_session_edge_shadow.py "${NASDAQ_SESSION_EDGE_ARGS[@]}"
fi

# NASDAQ 세션테이프 shadow (swing-main-f9yw, §12-D): 시간봉 증분 갱신 → rank-1 shadow 픽.
# 검증: 29개월 walk-forward 승률 79.3%(플라시보 +9.4pp/5σ), 진짜엣지 ~+0.5~1.0/트레이드.
# 관측 전용(라우팅 없음) — forward n>=30 전 운용 금지. 비활성: AG_NASDAQ_SESSION_TAPE_ENABLE=0.
if [[ "${AG_NASDAQ_SESSION_TAPE_ENABLE:-1}" == "1" ]]; then
  echo "[STEP] update_us_hourly (시간봉 증분)"
  run_optional "update_us_hourly" \
    python3 multi_agent/tools/update_us_hourly.py
  echo "[STEP] report_nasdaq_session_tape"
  run_optional "report_nasdaq_session_tape" \
    python3 multi_agent/tools/report_nasdaq_session_tape.py
fi

if [[ "${AG_SWING_ENSEMBLE_ENABLE:-1}" == "1" ]]; then
  # LIVE SWING structure-1 (2026-06-24, operator decision): daily price-ML ENSEMBLE
  # (LGBM+XGB+ET) -> ft_5_5 first-touch (+5/-5), KOSPI+KOSDAQ, >=100억, top ~1% confidence,
  # scan_mode=SWING. Validated 8y walk-forward / same-day size-matched: top-1% hits ~66-67%
  # (not the 75% goal; efficient-market ceiling ~70%), shipped LIVE to validate while running.
  # Structure-2 of the 2-structure SWING scan = Exception Leader (unchanged, from the planner).
  # Routes to the live surface when AG_SWING_ENSEMBLE_PRODUCTION=1 (default ON per operator) and
  # records a ledger that auto-resolves realised 5D ft_5_5 hit + first-touch return. Needs FDR.
  echo "[STEP] report_swing_ensemble"
  run_optional "report_swing_ensemble" \
    python3 multi_agent/tools/report_swing_ensemble.py \
      --top-pct "${AG_SWING_ENSEMBLE_TOP_PCT:-1.0}" --min-liq "${AG_SWING_ENSEMBLE_MIN_LIQ:-100}"
fi

if [[ "${AG_KOSPI_INTRADAY_ENABLE:-1}" == "1" ]]; then
  # LIVE KOSPI INTRADAY lane -- Claude lane of the Claude+Codex synthesis.
  # PROMOTED 2026-07-03 (RESEARCH_LOG §7-E): rank-1 selective issuance, PRIMARY tier only routes
  # (p >= trailing-40 q0.2 of rank-1 p, fallback 0.65; CANDIDATE days ledgered, not routed),
  # exit = +5% touch within 5 sessions else 5d close, no stop. Walk-forward 8 OOS mo:
  # win 89.0% / EV +4.80 net CI>0 / 3.2 pick-days-wk / 0-1 neg months incl 2026-06.
  # Replaces top2 + 3d-close-hold (win 45%, EV 1.56 CI incl 0). Guards unchanged
  # (>=100억, close_vwap>=0, idx_vol20>=8). Needs KIS minute bars + FDR daily.
  # decision_bucket=kospi_intraday. Codex runs the KOSDAQ 15:00 lane separately.
  echo "[STEP] report_kospi_intraday_swing"
  KIS_ENABLE_LIVE_CALLS=1 run_optional "report_kospi_intraday_swing" \
    python3 multi_agent/tools/report_kospi_intraday_swing.py \
      --min-liq "${AG_KOSPI_INTRADAY_MIN_LIQ:-100}"
fi

# 코스닥 15:00 번들 일일 재학습 (P1-H2, swing-main-67zc): 정적 번들은 부패(승률 65.5%/EV CI 0포함,
# 미래월 p_cal 0.75+ 희소 → 0픽 사태). 재학습시 승률 71.2%/EV 2.85 CI>0/주3픽 (p_cal>=0.70).
# 이전 번들 .bak 보존. 비활성: AG_KOSDAQ_BUNDLE_RETRAIN_ENABLE=0.
if [[ "${AG_KOSDAQ_BUNDLE_RETRAIN_ENABLE:-1}" == "1" ]]; then
  echo "[STEP] train_kosdaq_1500_bundle (일일 재학습)"
  run_optional "train_kosdaq_1500_bundle" \
    python3 multi_agent/tools/train_kosdaq_1500_bundle.py
fi

if [[ "${AG_KOSDAQ_INTRADAY_ENABLE:-1}" == "1" ]]; then
  # LIVE KOSDAQ INTRADAY lane (2026-06-24, operator) -- Codex lane of the Claude+Codex synthesis.
  # KR_INTRADAY_3D_T5 15:00 VWAP-guard model. Stored artifact:
  # models/kr_intraday_3d_t5/kosdaq_liq30_1500_lgbm_isotonic_vwapguard.pkl.
  # Scores KOSDAQ minute bars at/after 15:00, requires calibrated p>=0.80 and pre_vwap_dist_pct>=0,
  # emits daily top2, records target_touch3d_t5 + 3D close return/MFE/MAE in a separate INTRADAY
  # ledger, and routes live with scan_mode=INTRADAY when AG_KOSDAQ_INTRADAY_PRODUCTION=1 (default ON).
  # Tracks both liquidity lanes: >=30억 main edge and >=100억 tradeability.
  echo "[STEP] report_kosdaq_intraday_vwap_guard"
  KIS_ENABLE_LIVE_CALLS=1 run_optional "report_kosdaq_intraday_vwap_guard" \
    python3 multi_agent/tools/report_kosdaq_intraday_vwap_guard.py \
      --min-liq "${AG_KOSDAQ_INTRADAY_MIN_LIQ:-30}" \
      --tradeability-liq "${AG_KOSDAQ_INTRADAY_TRADEABILITY_LIQ:-100}" \
      --max-symbols "${AG_KOSDAQ_INTRADAY_MAX_SYMBOLS:-0}" \
      --daily-context-source "${AG_KOSDAQ_INTRADAY_DAILY_CONTEXT_SOURCE:-cache}"
fi

if [[ "${AG_KR_SELECTIVE_SHADOW_ENABLE:-1}" == "1" ]]; then
  # Observation-only selective high-conviction view over both intraday lane ledgers
  # (RESEARCH_LOG §7): rank-1 by p per day, PRIMARY/CANDIDATE via trailing-40 q0.2 rule,
  # scored by exit-shadow fields. Runs AFTER the two lane steps above. No routing.
  echo "[STEP] report_kr_selective_shadow"
  run_optional "report_kr_selective_shadow" \
    python3 multi_agent/tools/report_kr_selective_shadow.py
fi

if [[ "${AG_KR_SWING_CANDIDATE_ENABLE:-1}" == "1" ]]; then
  # Observation-only swing CANDIDATE picks (RESEARCH_LOG §7-A/D): 8y ft_5_5 ranker,
  # rolling 2y train on px_long, next-open entry / +5% touch-exit contract, fdr auto-scoring.
  # Honest modest edge (EV ~+0.65/trade, 60-62% touch). Never routed to buy lists.
  echo "[STEP] report_kr_swing_candidate"
  run_optional "report_kr_swing_candidate" \
    python3 multi_agent/tools/report_kr_swing_candidate.py \
      --top-k "${AG_KR_SWING_CANDIDATE_TOPK:-3}"
fi

# 재귀 연구 게이트: 레인별 forward 자동채점 vs 동결 백테스트 기대 → CONFIRM/DEGRADE/EXCEED,
# 판정 변화 시 beads 재연구 티켓 자동 발행. 비활성: AG_RECURSION_GATE_ENABLE=0.
if [[ "${AG_RECURSION_GATE_ENABLE:-1}" == "1" ]]; then
  echo "[STEP] report_research_recursion_gate"
  run_optional "report_research_recursion_gate" \
    python3 multi_agent/tools/report_research_recursion_gate.py
fi

# 픽 부검 수집: 해상된 모든 픽에 모드 태그(WIN_TOUCH/LOSS_TAIL 등)+맥락(레짐상태) 축적 —
# 데이터가 낳는 가설의 기질. 비활성: AG_PICK_AUTOPSY_ENABLE=0.
if [[ "${AG_PICK_AUTOPSY_ENABLE:-1}" == "1" ]]; then
  echo "[STEP] build_pick_autopsy"
  run_optional "build_pick_autopsy" \
    python3 multi_agent/tools/build_pick_autopsy.py
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
