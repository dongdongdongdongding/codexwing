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
# 경량 증분 업데이터 (수급/신용/공시) — 2026-07-08: 분봉 백필이 KIS 스로틀링으로 5h+ 걸리며
# 뒤 스텝들을 며칠씩 굶기던 문제(수급 7/6, 신용 7/3 정지) → 무거운 백필 "앞"으로 이동.
if [[ "${AG_FLOW_REFRESH:-1}" == "1" && -f "${HOME}/research_cache/flow_update.py" ]]; then
  echo "[STEP] flow_update (외국인/기관 수급 증분)"
  run_optional "flow_update" python3 "${HOME}/research_cache/flow_update.py"
fi
if [[ "${AG_CREDIT_REFRESH:-1}" == "1" && -f "${HOME}/research_cache/credit_update.py" ]]; then
  echo "[STEP] credit_update (신용/대주 잔고 증분)"
  run_optional "credit_update" python3 "${HOME}/research_cache/credit_update.py"
fi

# PKG-D ② (§40, 2026-08-04): KOFIA 스트레스 축 — 예탁금/미수금·반대매매/신용융자 일별 증분.
# 크래시 레짐 게이트 후보 데이터(관측 수집만, 피처 주장은 사전등록 필수). 비활성: AG_KOFIA_STRESS=0.
if [[ "${AG_KOFIA_STRESS:-1}" == "1" && -f "${HOME}/research_cache/kofia_stress_update.py" ]]; then
  echo "[STEP] kofia_stress_update (예탁금/반대매매/신용융자)"
  run_optional "kofia_stress_update" python3 "${HOME}/research_cache/kofia_stress_update.py"
fi
if [[ "${AG_DART_REFRESH:-1}" == "1" && -f "${HOME}/research_cache/dart_update.py" ]]; then
  echo "[STEP] dart_update (공시 증분)"
  run_optional "dart_update" python3 "${HOME}/research_cache/dart_update.py"
fi

# sentinel 판정기 (OD-37/38, 2026-08-17).
#   expectations.yaml 에 기준·재계산법·에스컬레이션 대상이 다 적혀 있는데 **그걸 돌리는 것이
#   없었다.** §40 킬 기준이 산문으로만 적혀 두 달 뒤 우연히 발견된 것과 같은 형태다.
#   새 launchd 잡을 만들지 않고 dailyops 스텝으로 붙인다(OD-38).
#   OD-41: 맨 뒤가 아니라 2시간짜리 intraday_backfill **앞**에 둔다. 판정기는 원장·마커·
#   산출물만 읽어 그날 백필에 의존하지 않는데, 뒤에 두면 매 실행 4.5시간 뒤에야 판정이 나오고
#   기한·발화율처럼 시각이 중요한 항목이 그만큼 늦게 드러난다.
#   판정: OD-34 발화 자격 · OD-35 정지 기한 · OD-39 마커 없는 정지 · 자격 전이 WARN ·
#         내용 기준 신선도 · OD-19 킬 기준 대조.
if [[ "${AG_SENTINEL_CHECK:-1}" == "1" ]]; then
  echo "[STEP] report_sentinel_expectations"
  # run_optional 을 그대로 쓰지 않는 이유는 앞의 두 스텝과 같다 — 에스컬레이션이 있으면
  # 종료코드 1 인데 [WARN] 한 줄로 삼켜지면 무엇이 걸렸는지가 남지 않는다.
  if SENTINEL_OUT="$(python3 multi_agent/tools/report_sentinel_expectations.py --json-only)"; then
    SENTINEL_RC=0
  else
    SENTINEL_RC=$?
  fi
  echo "[DATA] sentinel rc=${SENTINEL_RC} ${SENTINEL_OUT}"
  if [[ "${SENTINEL_RC}" == "0" ]]; then
    echo "[OK] report_sentinel_expectations"
  else
    echo "[WARN] sentinel 에스컬레이션 발생 — runtime_state/reports/validation/sentinel_escalations.md 확인"
  fi
else
  echo "[SKIP] report_sentinel_expectations — AG_SENTINEL_CHECK=0 (재개: =1)"
fi

# --- OD-43 (2026-08-17): 아래 두 생산자를 2시간 intraday_backfill **앞**으로 옮겼다. ---
#   실측: 둘 다 그날 백필 산출(~/research_cache/intraday/)을 읽지 않는다.
#     43 코스닥 — px_long.parquet 만 읽는다(_load_px_cache:116). 41 에서 가져오는 것은
#        market_drawdown_state 하나뿐이고 그 함수도 px_long 만 읽는다(:66).
#     45 스윙   — px_long.parquet + 자기 원장만 읽는다. score_today 는 41 것이 아니라
#        자기 파일의 동명 함수다(:54).
#   px_long_refresh 는 백필보다 앞(스텝 213)이라 앞으로 옮겨도 신선도가 유지된다.
#   41 코스피는 옮기지 않았다 — _train() 이 intraday_3d_panel.parquet 을 읽고(:179)
#   그 패널은 백필 산출로 build_intraday_3d_panel 이 만든다.
#   근거: 웹 /api/picks 가 이 두 레인의 dailyops 산출을 유일한 소스로 읽는다(OD-43).
if [[ "${AG_KR_SWING_CANDIDATE_ENABLE:-1}" == "1" ]]; then
  # Observation-only swing CANDIDATE picks (RESEARCH_LOG §7-A/D): 8y ft_5_5 ranker,
  # rolling 2y train on px_long, next-open entry / +5% touch-exit contract, fdr auto-scoring.
  # Honest modest edge (EV ~+0.65/trade, 60-62% touch). Never routed to buy lists.
  echo "[STEP] report_kr_swing_candidate"
  run_optional "report_kr_swing_candidate" \
    python3 multi_agent/tools/report_kr_swing_candidate.py \
      --top-k "${AG_KR_SWING_CANDIDATE_TOPK:-3}"
fi
if [[ "${AG_INTRADAY_BACKFILL:-1}" == "1" && -f "${HOME}/research_cache/intraday_backfill.py" ]]; then
  # 분봉 minute bars: incremental KIS backfill of today's full session (post-close). Only fetches
  # days not already cached, so the daily run just adds today. Disable with AG_INTRADAY_BACKFILL=0.
  echo "[STEP] intraday_backfill (분봉)"
  run_optional "intraday_backfill" \
    python3 "${HOME}/research_cache/intraday_backfill.py"
fi

# 벤치 데이터 수집 (2026-07-07, swing-main-h3cu 후속): 미래 엣지 재료 축적 — 표본이 익으면
# research_reopen_queue가 자동으로 연구 티켓을 발행한다. 비활성: AG_BENCH_DATA=0.
if [[ "${AG_BENCH_DATA:-1}" == "1" ]]; then
  if [[ -f "${HOME}/research_cache/short_update.py" ]]; then
    echo "[STEP] short_update (공매도 일별, KIS 우회)"
    run_optional "short_update" python3 "${HOME}/research_cache/short_update.py"
  fi
  if [[ -f "${HOME}/research_cache/intraday_ext_update.py" ]]; then
    echo "[STEP] intraday_ext_update (확장세션 08:00-20:00)"
    run_optional "intraday_ext_update" python3 "${HOME}/research_cache/intraday_ext_update.py"
  fi
  if [[ -f "${HOME}/research_cache/ohlc_full_backfill.py" ]]; then
    echo "[STEP] ohlc_full_incremental (8y 경로 증분)"
    run_optional "ohlc_full_incremental" python3 "${HOME}/research_cache/ohlc_full_backfill.py"
  fi
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
# B 엔진 (signal_class=B, 시장중립 적응형 앙상블, A와 별개). 일봉주기 매일 top10 픽 + forward-shadow.
# 데이터(px_long 위 + flow)가 신선해야 하므로 위 px_long_refresh 다음에 배치. 비활성: AG_B_ENGINE=0.
if [[ "${AG_B_ENGINE:-1}" == "1" && -d "b_engine" ]]; then
  # 2026-08-03 PKG-A(운영자 승인, §40): b_all_top10 forward n=315 EV -2.65 CI[-4.14,-1.16]
  # 전체 음수(시스템 사상 최강 음성 확정) — 재학습/신규 픽 발행 중지. settle은 잔여 open 픽
  # (~65건) 정산 완료를 위해 유지(forward 원장 무결성). 재개: AG_B_ENGINE_SCAN=1.
  if [[ "${AG_B_ENGINE_SCAN:-0}" == "1" ]]; then
    echo "[STEP] b_engine retrain (적응형 앙상블)"
    run_optional "b_retrain" python3 -m b_engine.model_engine train
    echo "[STEP] b_engine scan (매일 top10 픽)"
    run_optional "b_scan" python3 -m b_engine.model_scan scan
  else
    echo "[SKIP] b_engine retrain/scan — PKG-A 중지 (§40 CI<0 확정, AG_B_ENGINE_SCAN=1로 재개)"
  fi
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
  # --- NASDAQ 일봉 피처 패널 갱신 (2026-08-16, audit-ledger-rewrite-pattern.md §2.2) ---
  # nasdaq_swing_daily_edge 원장이 승격(06-30) 이래 0행이었다. 세션 차단도 오류도 아니고,
  # 원천 패널(~/research_cache/us_daily/NASDAQ/daily_features_*.parquet)이 2026-06-29 에
  # 동결됐는데 **재생성 스텝이 아예 없었다.** 매일 돌면서 0을 쓰고 파일만 다시 만들었다.
  # 소비자(아래 report_nasdaq_daily_edge_shadow)가 --panel latest 로 그 캐시를 glob 하므로
  # 갱신은 반드시 **소비자보다 앞**이어야 그날 갱신분이 반영된다.
  # 선례: 세션테이프 레인(update_us_hourly → report_nasdaq_session_tape)과 같은 순서다.
  # 생산자 계약: orca/reports/impl-nasdaq-daily-panel-seaslug.md
  #   - 이미 최신이면 즉시 반환(멱등) — primary_daily_ops 가 하루 3회 돌기 때문에 필수다
  #   - stdout 에 JSON 한 줄, 종료코드 0 = already_current|refreshed
  #   - AG_US_DAILY_PANEL_MAX_AGE_DAYS(4) / _RAW_MAX_AGE_DAYS(5) / _KEEP_PANELS(3)
  if [[ "${AG_US_DAILY_PANEL_REFRESH_ENABLE:-1}" == "1" ]]; then
    US_DAILY_PANEL_ARGS=(--daily-refresh --market NASDAQ)
    if [[ "${AG_US_DAILY_PANEL_FORCE_REFRESH:-0}" == "1" ]]; then
      US_DAILY_PANEL_ARGS+=(--force-refresh)
    fi
    echo "[STEP] backfill_us_daily_features (NASDAQ 일봉패널)"
    # run_optional 을 그대로 쓰지 않는 이유: 실패가 "[WARN] … (continuing)" 한 줄로 삼켜진다.
    # 이 리포의 사고들(원장 0행 7주, 플래그 무효 100회, 데일리옵스 153/153)이 전부 그 삼킴
    # 계열이라, 생산자가 stdout 에 내는 status JSON 을 라벨 붙여 남긴다. 실패해도 dailyops
    # 전체는 계속한다(생산자 권고) — 대신 조용히 지나가지는 않는다.
    if US_DAILY_PANEL_OUT="$(python3 multi_agent/tools/backfill_us_daily_features.py "${US_DAILY_PANEL_ARGS[@]}")"; then
      US_DAILY_PANEL_RC=0
    else
      US_DAILY_PANEL_RC=$?
    fi
    echo "[DATA] us_daily_panel rc=${US_DAILY_PANEL_RC} ${US_DAILY_PANEL_OUT}"
    if [[ "${US_DAILY_PANEL_RC}" == "0" ]]; then
      echo "[OK] backfill_us_daily_features"
    else
      echo "[WARN] backfill_us_daily_features failed rc=${US_DAILY_PANEL_RC} — 소비자는 이전 패널로 채점한다(원장 정체 가능)"
    fi
  else
    echo "[SKIP] backfill_us_daily_features — AG_US_DAILY_PANEL_REFRESH_ENABLE=0 (재개: =1)"
  fi
  echo "[STEP] report_nasdaq_daily_edge_shadow"
  run_optional "report_nasdaq_daily_edge_shadow" \
    python3 multi_agent/tools/report_nasdaq_daily_edge_shadow.py "${NASDAQ_SWING_ARGS[@]}"
fi

# 2026-08-16 수리 (추적 orca/reports/trace-ops-flag-mismatch.md): 중첩 2이름 폴백 제거.
#   이전: ${AG_NASDAQ_SESSION_EDGE_ENABLE:-${AG_NASDAQ_SESSION_EDGE_SHADOW_ENABLE:-0}}
#   1순위 신규명은 리포 전체에서 설정하는 곳이 0건이고, 2순위 레거시명은 호출자
#   (run_primary_market_session_ops.py)가 항상 주입했다 → 3순위 리터럴은 **도달 불가**.
#   2026-07-05 b6d2477 이 "기본 OFF"라며 바꾼 것이 정확히 그 도달 불가 리터럴이라
#   스케줄 경로에서 no-op 이었고, 레인은 06-30 승격 이래 100회 실행 SKIP 0회로 계속 돌았다.
#   이름 하나·기본값 하나·기록 한 곳으로 정리한다. 기본값 1 은 종전 실효 동작(항상 ON)을
#   그대로 옮긴 것이며, 운영자 결정도 이 레인은 수리해 존속이다. 끄려면 =0 을 주면 되고
#   그때는 아래 else 가 [SKIP] 을 남긴다(꺼진 사실이 로그에 보여야 한다).
if [[ "${AG_NASDAQ_SESSION_EDGE_SHADOW_ENABLE:-1}" == "1" ]]; then
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
  # 2026-07-05 주석은 "기본 OFF"라고 적혀 있었으나 실제로는 한 번도 꺼진 적이 없다(위 참조).
  # 후계 논의(report_nasdaq_session_tape, §12-D)는 유효하나 중지 여부는 운영자 결정 사항이며,
  # 지금은 이 플래그가 실제로 동작한다는 것까지가 코드의 책임이다.
  echo "[STEP] report_nasdaq_session_edge_shadow"
  run_optional "report_nasdaq_session_edge_shadow" \
    python3 multi_agent/tools/report_nasdaq_session_edge_shadow.py "${NASDAQ_SESSION_EDGE_ARGS[@]}"
else
  echo "[SKIP] report_nasdaq_session_edge_shadow — AG_NASDAQ_SESSION_EDGE_SHADOW_ENABLE=0 (재개: =1)"
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

# 2026-07-19 운영자 승인 정리: 구 스윙 앙상블 일일 실행 중지 — DEGRADE 확정(정산 112, EV −0.72)·
# P3 교체 완료 상태에서 감시 소임 종료. 원장은 동결 보존. 복원: 이 블록을 git 이력에서.

# ⚠️ 2026-08-17: 이 스텝을 OD-43 으로 백필 앞으로 옮겼다가 **되돌렸다.**
#   파일 읽기만 보면 px_long 뿐이라 옮겨도 될 것처럼 보이지만, _fetch_minute_frame 이
#   KIS 에서 **당일 분봉을 실시간 조회**한다(:271-273). _minute_hours 가 요구하는 시각에
#   ENTRY_INPUT_HOUR(15:00)가 들어가므로 장이 그 시각에 닿기 전에는 봉이 없다.
#   의존은 백필 산출이 아니라 **벽시계**다 — 파일 의존만 보면 안 잡힌다.
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


if [[ "${AG_KR_SELECTIVE_SHADOW_ENABLE:-1}" == "1" ]]; then
  # Observation-only selective high-conviction view over both intraday lane ledgers
  # (RESEARCH_LOG §7): rank-1 by p per day, PRIMARY/CANDIDATE via trailing-40 q0.2 rule,
  # scored by exit-shadow fields. Runs AFTER the two lane steps above. No routing.
  echo "[STEP] report_kr_selective_shadow"
  run_optional "report_kr_selective_shadow" \
    python3 multi_agent/tools/report_kr_selective_shadow.py
fi


# 미채점 행 임계 초과 경보 (F6, swing-main-r6sb, 2026-08-16).
#   원장에 채점되지 않은 행이 쌓여도 경보가 없었다 — resolver 는 bare except 라 실패가 안
#   드러나고, 재시도 상한·dead-letter 가 없어 실패 행이 그냥 넘어가며, report_data_manifest 는
#   원장 최신 date 만 봐서 개별 행 미채점을 못 본다. kr_swing_candidate 의 한 행이 32일간
#   조용히 실패 중이었고, **이 침묵이 7,171건 만료의 상류다.**
if [[ "${AG_UNRESOLVED_STALENESS_ALERT:-1}" == "1" ]]; then
  echo "[STEP] report_unresolved_outcome_staleness"
  # run_optional 을 그대로 쓰지 않는 이유는 패널 갱신과 같다 — 실패가 [WARN] 한 줄로 삼켜진다.
  # 임계 초과 시 종료코드 1 이므로 status 를 라벨 붙여 남겨야 추적된다.
  if STALENESS_OUT="$(python3 multi_agent/tools/report_unresolved_outcome_staleness.py --json-only)"; then
    STALENESS_RC=0
  else
    STALENESS_RC=$?
  fi
  echo "[DATA] unresolved_staleness rc=${STALENESS_RC} ${STALENESS_OUT}"
  if [[ "${STALENESS_RC}" == "0" ]]; then
    echo "[OK] report_unresolved_outcome_staleness"
  else
    echo "[WARN] 미채점 행이 임계를 넘겼다 — 채점 파이프가 그 행들을 놓치고 있다(수동 확인 필요)"
  fi
else
  echo "[SKIP] report_unresolved_outcome_staleness — AG_UNRESOLVED_STALENESS_ALERT=0 (재개: =1)"
fi

# 재귀 연구 게이트: 레인별 forward 자동채점 vs 동결 백테스트 기대 → CONFIRM/DEGRADE/EXCEED,
# 판정 변화 시 beads 재연구 티켓 자동 발행. 비활성: AG_RECURSION_GATE_ENABLE=0.
if [[ "${AG_RECURSION_GATE_ENABLE:-1}" == "1" ]]; then
  echo "[STEP] report_research_recursion_gate"
  run_optional "report_research_recursion_gate" \
    python3 multi_agent/tools/report_research_recursion_gate.py

  # PKG-B ④ (§40): 동시노출·슬리브 자본곡선 계기판 — 8:2 예산 준수 일일 측정.
  echo "[STEP] report_portfolio_exposure"
  run_optional "report_portfolio_exposure" \
    python3 multi_agent/tools/report_portfolio_exposure.py
fi

# 연구 재개봉 큐: "표본 부족 보류" 실험이 데이터 성숙(공매도 120일/확장세션 120일/정산 100건 등)
# 도달 시 자동으로 bd 티켓 발행 — 연구 큐가 스스로 깨어난다. 비활성: AG_REOPEN_QUEUE=0.
if [[ "${AG_REOPEN_QUEUE:-1}" == "1" ]]; then
  echo "[STEP] research_reopen_queue"
  run_optional "research_reopen_queue" \
    python3 multi_agent/tools/research_reopen_queue.py
fi

# 데이터 매니페스트: 전 학습자산 신선도 선언·감시 — 정체 시 bd 티켓 자동 (2026-07-19 체계화).
if [[ "${AG_DATA_MANIFEST:-1}" == "1" ]]; then
  echo "[STEP] report_data_manifest"
  run_optional "report_data_manifest" \
    python3 multi_agent/tools/report_data_manifest.py
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
  # bash 3.2(macOS 기본)는 set -u 아래에서 빈 배열 확장을 unbound variable로 죽인다.
  # 이 두 줄이 2026-06-08~08-14 데일리옵스 153/153 실패의 원인이었다 (swing-main-7x7h).
  echo "[STEP] emit_daily_backtest ${DRIFT_ARGS[*]:-}"
  run_optional "emit_daily_backtest" \
    python3 multi_agent/tools/emit_daily_backtest.py ${DRIFT_ARGS[@]+"${DRIFT_ARGS[@]}"}
fi

if [[ "${AG_DAILY_MODEL_FOUNDATION_GATE_ENABLE:-1}" == "1" ]]; then
  echo "[STEP] report_daily_model_foundation_gate"
  run_optional "report_daily_model_foundation_gate" \
    python3 multi_agent/tools/report_daily_model_foundation_gate.py
fi

echo "[DONE] daily_ops completed"
