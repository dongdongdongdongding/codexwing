import warnings
# Suppress Google Auth Python 3.9 Deprecation & urllib3 LibreSSL warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.auth")
warnings.filterwarnings("ignore", category=FutureWarning, module="google.oauth2")
warnings.filterwarnings("ignore", module="urllib3")

import concurrent.futures
import json
import streamlit as st
import os
from pathlib import Path
from datetime import date
import yfinance as yf
from dotenv import load_dotenv
load_dotenv()
load_dotenv(".env.local")

from modules import vision_analysis, quant_analysis, db_manager, news_analysis, market_intelligence
from modules.live_scan_context import live_mode_enabled, normalize_market_key
from modules.macro_scheduler import get_macro_context, macro_weather_text
from modules.scanner_bridge import run_legacy_agent_bridge
from modules.scanner_runtime import SharedBackoffState, run_parallel_scan, scan_symbol_with_retry
from modules.scanner_services import evaluate_uploaded_candidate, normalize_uploaded_ticker
from modules.scan_policy import (
    compute_market_gate as compute_market_gate_live,
    compute_rank_adjustment as shared_compute_rank_adjustment,
)
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import traceback

# [Phase 8] Global Backoff Synchronization for Rate Limits
_SCAN_BACKOFF_STATE = SharedBackoffState()

st.set_page_config(page_title="스윙 트레이딩 AI", layout="wide", page_icon="📈")

if "deep_dive_ticker" not in st.session_state:
    st.session_state["deep_dive_ticker"] = "AAPL"
if "selected_scan_market" not in st.session_state:
    st.session_state["selected_scan_market"] = "KOSPI"


def _load_json_safe(path_str):
    if not path_str:
        return {}
    try:
        path = Path(str(path_str))
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _load_latest_daily_summary(market):
    reports_dir = Path("runtime_state/reports/daily")
    market = str(market or "").strip().upper()
    if not reports_dir.exists() or not market:
        return {}

    today_path = reports_dir / f"daily_summary_{date.today().isoformat()}_{market}.json"
    if today_path.exists():
        return _load_json_safe(str(today_path))

    candidates = sorted(reports_dir.glob(f"daily_summary_*_{market}.json"))
    if candidates:
        return _load_json_safe(str(candidates[-1]))
    return {}


def _load_contaminated_run_map():
    payload = _load_json_safe("runtime_state/reports/validation/contaminated_runs_all.json")
    runs = payload.get("runs", []) if isinstance(payload.get("runs"), list) else []
    result = {}
    for row in runs:
        if not isinstance(row, dict):
            continue
        run_id = str(row.get("run_id") or "").strip()
        if not run_id:
            continue
        result[run_id] = {
            "validation_excluded": bool(row.get("validation_excluded")),
            "quality_flags": row.get("quality_flags") or [],
        }
    return result


def _coerce_numeric_display(df, columns):
    cleaned = df.copy()
    for col in columns:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
    return cleaned


def _return_metric(return_buckets, bucket, horizon, field="avg_return_pct"):
    bucket_row = return_buckets.get(bucket, {}) if isinstance(return_buckets, dict) else {}
    if not isinstance(bucket_row, dict):
        return 0.0
    horizon_row = bucket_row.get(horizon, {})
    if not isinstance(horizon_row, dict):
        return 0.0
    try:
        return float(horizon_row.get(field, 0.0) or 0.0)
    except Exception:
        return 0.0


def _render_daily_ops_overview():
    st.markdown("### 일일 성과 요약")
    markets = ["KOSPI", "KOSDAQ", "NASDAQ", "AMEX"]
    cols = st.columns(len(markets))
    has_any = False
    for col, market in zip(cols, markets):
        payload = _load_latest_daily_summary(market)
        if not payload:
            col.info(f"{market}\n\n요약 없음")
            continue
        has_any = True
        outcomes = payload.get("outcomes", {}) if isinstance(payload.get("outcomes"), dict) else {}
        buckets = payload.get("outcome_bucket_breakdown", {}) if isinstance(payload.get("outcome_bucket_breakdown"), dict) else {}
        return_buckets = payload.get("return_bucket_breakdown", {}) if isinstance(payload.get("return_bucket_breakdown"), dict) else {}
        picked = (buckets.get("picked", {}) if isinstance(buckets.get("picked"), dict) else {}).get("total", 0)
        watchlist_bucket = (buckets.get("watchlist", {}) if isinstance(buckets.get("watchlist"), dict) else {}).get("total", 0)
        exception_bucket = (
            (buckets.get("exception_leader", {}) if isinstance(buckets.get("exception_leader"), dict) else {}).get("total", 0)
        )
        picked_30m = _return_metric(return_buckets, "picked", "30m")
        picked_1h = _return_metric(return_buckets, "picked", "1h")
        picked_close = _return_metric(return_buckets, "picked", "close")
        col.metric(f"{market} Runs", int(payload.get("total_runs", 0) or 0))
        col.caption(
            f"Picked {int(picked or 0)} | "
            f"Watchlist {int(watchlist_bucket or 0)} | "
            f"Exception {int(exception_bucket or 0)} | "
            f"30m {picked_30m:+.1f}% | "
            f"1H {picked_1h:+.1f}% | "
            f"Close {picked_close:+.1f}%"
        )
    if has_any:
        st.markdown("#### 성과 상태 카드")
        status_cols = st.columns(len(markets))
        for col, market in zip(status_cols, markets):
            payload = _load_latest_daily_summary(market)
            if not payload:
                col.info(f"{market}\n\n데이터 없음")
                continue
            outcomes = payload.get("outcomes", {}) if isinstance(payload.get("outcomes"), dict) else {}
            col.metric(f"{market} Pending", int(outcomes.get("pending", 0) or 0))
            col.metric(f"{market} Resolved", int(outcomes.get("resolved", 0) or 0))
            col.metric(f"{market} Expired", int(outcomes.get("expired", 0) or 0))

        st.markdown("#### 장중 성과 카드")
        intraday_cols = st.columns(len(markets))
        for col, market in zip(intraday_cols, markets):
            payload = _load_latest_daily_summary(market)
            if not payload:
                col.info(f"{market}\n\n데이터 없음")
                continue
            return_buckets = payload.get("return_bucket_breakdown", {}) if isinstance(payload.get("return_bucket_breakdown"), dict) else {}
            picked_30m = _return_metric(return_buckets, "picked", "30m")
            picked_1h = _return_metric(return_buckets, "picked", "1h")
            picked_close = _return_metric(return_buckets, "picked", "close")
            picked_30m_n = int(_return_metric(return_buckets, "picked", "30m", field="samples"))
            picked_1h_n = int(_return_metric(return_buckets, "picked", "1h", field="samples"))
            picked_close_n = int(_return_metric(return_buckets, "picked", "close", field="samples"))
            col.metric(f"{market} 30분", f"{picked_30m:+.2f}%", f"표본 {picked_30m_n}")
            col.metric(f"{market} 1시간", f"{picked_1h:+.2f}%", f"표본 {picked_1h_n}")
            col.metric(f"{market} 종가", f"{picked_close:+.2f}%", f"표본 {picked_close_n}")
        with st.expander("성과측정 상세", expanded=False):
            rows = []
            for market in markets:
                payload = _load_latest_daily_summary(market)
                if not payload:
                    continue
                outcomes = payload.get("outcomes", {}) if isinstance(payload.get("outcomes"), dict) else {}
                buckets = payload.get("outcome_bucket_breakdown", {}) if isinstance(payload.get("outcome_bucket_breakdown"), dict) else {}
                return_buckets = payload.get("return_bucket_breakdown", {}) if isinstance(payload.get("return_bucket_breakdown"), dict) else {}
                rows.append(
                    {
                        "Market": market,
                        "Date": payload.get("target_date", ""),
                        "Runs": payload.get("total_runs", 0),
                        "Picked": ((buckets.get("picked", {}) if isinstance(buckets.get("picked"), dict) else {}).get("total", 0)),
                        "Watchlist": ((buckets.get("watchlist", {}) if isinstance(buckets.get("watchlist"), dict) else {}).get("total", 0)),
                        "ExceptionLeader": (
                            (buckets.get("exception_leader", {}) if isinstance(buckets.get("exception_leader"), dict) else {}).get("total", 0)
                        ),
                        "Picked30m Avg%": (((return_buckets.get("picked", {}) or {}).get("30m", {}) or {}).get("avg_return_pct", 0.0)),
                        "Picked1H Avg%": (((return_buckets.get("picked", {}) or {}).get("1h", {}) or {}).get("avg_return_pct", 0.0)),
                        "PickedClose Avg%": (((return_buckets.get("picked", {}) or {}).get("close", {}) or {}).get("avg_return_pct", 0.0)),
                        "Picked3D Avg%": (((return_buckets.get("picked", {}) or {}).get("3d", {}) or {}).get("avg_return_pct", 0.0)),
                        "Picked3D Win%": (((return_buckets.get("picked", {}) or {}).get("3d", {}) or {}).get("win_rate_pct", 0.0)),
                        "WatchClose Avg%": (((return_buckets.get("watchlist", {}) or {}).get("close", {}) or {}).get("avg_return_pct", 0.0)),
                        "Watch3D Avg%": (((return_buckets.get("watchlist", {}) or {}).get("3d", {}) or {}).get("avg_return_pct", 0.0)),
                        "Watch3D Win%": (((return_buckets.get("watchlist", {}) or {}).get("3d", {}) or {}).get("win_rate_pct", 0.0)),
                        "ExceptionClose Avg%": (((return_buckets.get("exception_leader", {}) or {}).get("close", {}) or {}).get("avg_return_pct", 0.0)),
                        "Exception3D Avg%": (((return_buckets.get("exception_leader", {}) or {}).get("3d", {}) or {}).get("avg_return_pct", 0.0)),
                        "Exception3D Win%": (((return_buckets.get("exception_leader", {}) or {}).get("3d", {}) or {}).get("win_rate_pct", 0.0)),
                        "Outcomes": outcomes.get("total", 0),
                        "Pending": outcomes.get("pending", 0),
                        "Resolved": outcomes.get("resolved", 0),
                        "Expired": outcomes.get("expired", 0),
                        "ClosureRatePct": outcomes.get("closure_rate_pct", 0.0),
                    }
                )
            if rows:
                st.dataframe(pd.DataFrame(rows), width='stretch')
    else:
        st.caption("아직 시장별 일일 성과 요약이 생성되지 않았습니다.")


def _render_agent_bridge_status(bridge_info, market):
    if not isinstance(bridge_info, dict) or not bridge_info:
        return

    compact_payload = _load_json_safe(bridge_info.get("orchestrator_compact_summary"))
    planner_payload = _load_json_safe(bridge_info.get("planner_handoff"))
    profile_payload = _load_json_safe(bridge_info.get("profile_diagnostics"))
    postmortem_payload = _load_json_safe(bridge_info.get("postmortem_report"))
    scanner_payload = _load_json_safe(bridge_info.get("scanner_handoff"))

    planner_warnings = planner_payload.get("global_warnings", []) if isinstance(planner_payload.get("global_warnings"), list) else []
    watchlist = planner_payload.get("watchlist", []) if isinstance(planner_payload.get("watchlist"), list) else []
    watchlist_meta = planner_payload.get("watchlist_meta", []) if isinstance(planner_payload.get("watchlist_meta"), list) else []
    decisions = planner_payload.get("decisions", []) if isinstance(planner_payload.get("decisions"), list) else []

    summary = scanner_payload.get("summary", {}) if isinstance(scanner_payload.get("summary"), dict) else {}
    diagnostics = summary.get("diagnostics", {}) if isinstance(summary.get("diagnostics"), dict) else {}
    reject_counts = diagnostics.get("reject_reason_counts", {}) if isinstance(diagnostics.get("reject_reason_counts"), dict) else {}
    reject_reasons_by_symbol = diagnostics.get("reject_reasons_by_symbol", {}) if isinstance(diagnostics.get("reject_reasons_by_symbol"), dict) else {}
    reject_details_by_symbol = diagnostics.get("reject_details_by_symbol", {}) if isinstance(diagnostics.get("reject_details_by_symbol"), dict) else {}

    compact_scanner = compact_payload.get("scanner", {}) if isinstance(compact_payload.get("scanner"), dict) else {}
    compact_planner = compact_payload.get("planner", {}) if isinstance(compact_payload.get("planner"), dict) else {}
    compact_postmortem = compact_payload.get("postmortem", {}) if isinstance(compact_payload.get("postmortem"), dict) else {}
    compact_reject_counts = compact_scanner.get("reject_reason_counts", {}) if isinstance(compact_scanner.get("reject_reason_counts"), dict) else {}
    compact_warning_codes = compact_planner.get("warning_codes", []) if isinstance(compact_planner.get("warning_codes"), list) else []

    if not reject_counts and compact_reject_counts:
        reject_counts = compact_reject_counts
    if not planner_warnings and compact_warning_codes:
        planner_warnings = [{"code": code, "message": "", "severity": "info"} for code in compact_warning_codes]

    st.markdown("### 운영 진단")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Decisions", len(decisions))
    c2.metric("Watchlist", len(watchlist) or int(compact_planner.get("watchlist_count", 0) or 0))
    c3.metric("Reject Reasons", len(reject_counts))
    c4.metric("Planner Warnings", len(planner_warnings))

    if compact_payload:
        st.caption(
            f"Run `{compact_payload.get('run_id', '-')}` | "
            f"Task `{compact_payload.get('task_kind', '-')}` | "
            f"Status `{compact_payload.get('status', '-')}`"
        )

    if planner_warnings:
        for warning in planner_warnings[:4]:
            if not isinstance(warning, dict):
                continue
            code = str(warning.get("code", "UNKNOWN"))
            message = str(warning.get("message", ""))
            severity = str(warning.get("severity", "info")).lower()
            line = f"`{code}` {message}"
            if severity == "error":
                st.error(line)
            elif severity == "warning":
                st.warning(line)
            else:
                st.info(line)

    if watchlist:
        st.markdown("#### Watchlist Only")
        watchlist_rows = []
        meta_by_ticker = {}
        for row in watchlist_meta:
            if isinstance(row, dict):
                meta_by_ticker[str(row.get("ticker", ""))] = row
        for rank, ticker in enumerate(watchlist, start=1):
            meta = meta_by_ticker.get(str(ticker), {})
            watchlist_rows.append(
                {
                    "Rank": rank,
                    "Ticker": ticker,
                    "Name": meta.get("stock_name", ""),
                    "Reason": meta.get("reason", ""),
                    "Reject": meta.get("reject_reason", ""),
                    "Alpha": meta.get("alpha_score", ""),
                    "Conviction": meta.get("conviction_score", ""),
                    "Prob5": meta.get("prob_5", ""),
                    "Clean": meta.get("prob_clean", ""),
                }
            )
        _watchlist_df = _coerce_numeric_display(pd.DataFrame(watchlist_rows), ["Alpha", "Conviction", "Prob5", "Clean"])
        st.dataframe(_watchlist_df, width='stretch')
        selected_watchlist_ticker = st.selectbox(
            "심층분석으로 넘길 Watchlist 종목",
            options=watchlist,
            key=f"watchlist_select_{market}_{planner_payload.get('produced_at', '')}",
        )
        if st.button("선택 종목을 심층분석 입력값으로 사용", key=f"watchlist_open_{market}_{planner_payload.get('produced_at', '')}"):
            st.session_state["deep_dive_ticker"] = selected_watchlist_ticker
            st.info(f"심층분석 탭 입력값을 `{selected_watchlist_ticker}` 로 설정했습니다.")

    if reject_counts:
        st.markdown("#### Reject Diagnostics")
        reject_rows = [{"Reason": key, "Count": int(value)} for key, value in sorted(reject_counts.items(), key=lambda x: x[1], reverse=True)]
        st.dataframe(_coerce_numeric_display(pd.DataFrame(reject_rows), ["Count"]), width='stretch')
        reject_detail_rows = []
        for ticker, reason in reject_reasons_by_symbol.items():
            detail_rows = reject_details_by_symbol.get(ticker, [])
            if not isinstance(detail_rows, list) or not detail_rows:
                detail_rows = [{}]
            detail = detail_rows[0] if isinstance(detail_rows[0], dict) else {}
            reject_detail_rows.append(
                {
                    "Name": detail.get("stock_name", ""),
                    "Ticker": ticker,
                    "Reason": reason,
                    "Alpha": detail.get("alpha_score", ""),
                    "Conviction": detail.get("conviction_score", ""),
                    "Prob5": detail.get("prob_5", ""),
                    "Clean": detail.get("prob_clean", ""),
                    "Trend": detail.get("real_trend", ""),
                    "Tier": detail.get("tier_sort", ""),
                    "WR": detail.get("wr", ""),
                    "PF": detail.get("pf", ""),
                    "SignalHits": detail.get("signal_hits", ""),
                    "Lookback": detail.get("signal_lookback", ""),
                    "MLProb": detail.get("ml_prob", ""),
                    "Position": detail.get("position", ""),
                    "Strategy": detail.get("strategy_type", ""),
                    "Turnover": detail.get("turnover", ""),
                    "MinTurnover": detail.get("min_turnover", ""),
                    "Stage": detail.get("stage", ""),
                    "Policy": detail.get("policy", ""),
                    "Mode": detail.get("mode", ""),
                }
            )
        if reject_detail_rows:
            st.markdown("##### 종목별 Reject 상세")
            _reject_df = _coerce_numeric_display(pd.DataFrame(reject_detail_rows), ["Alpha", "Conviction", "Prob5", "Clean", "Tier", "WR", "PF", "SignalHits", "Lookback", "MLProb", "Turnover", "MinTurnover"])
            st.dataframe(_reject_df, width='stretch')

    near_miss = profile_payload.get("near_miss_watchlist", {}) if isinstance(profile_payload.get("near_miss_watchlist"), dict) else {}
    watchlist_policy = profile_payload.get("watchlist_only_policy", {}) if isinstance(profile_payload.get("watchlist_only_policy"), dict) else {}
    fallback_watchlist = profile_payload.get("fallback_watchlist", {}) if isinstance(profile_payload.get("fallback_watchlist"), dict) else {}
    exception_leaders = profile_payload.get("exception_leaders", {}) if isinstance(profile_payload.get("exception_leaders"), dict) else {}

    exception_meta = exception_leaders.get("watchlist_meta", []) if isinstance(exception_leaders.get("watchlist_meta"), list) else []
    if exception_meta:
        st.markdown("#### Exception Leaders")
        exception_rows = []
        for idx, row in enumerate(exception_meta, start=1):
            if not isinstance(row, dict):
                continue
            exception_rows.append(
                {
                    "Rank": idx,
                    "Name": row.get("stock_name", ""),
                    "Ticker": row.get("ticker", ""),
                    "Reject": row.get("reject_reason", ""),
                    "ExceptionScore": row.get("exception_score", ""),
                    "Alpha": row.get("alpha_score", ""),
                    "Conviction": row.get("conviction_score", ""),
                    "Prob5": row.get("prob_5", ""),
                    "Clean": row.get("prob_clean", ""),
                    "Trend": row.get("real_trend", ""),
                    "Profile": row.get("profile_policy", ""),
                }
            )
        if exception_rows:
            _exception_df = _coerce_numeric_display(pd.DataFrame(exception_rows), ["ExceptionScore", "Alpha", "Conviction", "Prob5", "Clean"])
            st.dataframe(_exception_df, width='stretch')

    with st.expander("PM / Planner Trace", expanded=False):
        if watchlist_policy:
            st.write(
                {
                    "market": market,
                    "watchlist_only_policy": watchlist_policy,
                    "near_miss_watchlist": near_miss,
                    "fallback_watchlist": fallback_watchlist,
                    "exception_leaders": exception_leaders,
                }
            )
        likely_causes = postmortem_payload.get("likely_causes", []) if isinstance(postmortem_payload.get("likely_causes"), list) else []
        if not likely_causes and isinstance(compact_postmortem.get("likely_causes"), list):
            likely_causes = compact_postmortem.get("likely_causes", [])
        if likely_causes:
            st.markdown("**Likely Causes**")
            for cause in likely_causes[:6]:
                st.write(f"- {cause}")


st.title("🚀 AI 스윙 트레이딩 봇 (Quant + Vision)")
st.markdown("---")
_render_daily_ops_overview()
st.markdown("---")

# Sidebar Settings
st.sidebar.header("⚙️ 설정 (Settings)")
api_key = st.sidebar.text_input("OpenAI API Key (Vision용)", type="password")
if api_key:
    os.environ["OPENAI_API_KEY"] = api_key
    
st.markdown("### Strategy Parameters")
# --- Sidebar: Settings & Visual AI ---
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("OpenAI API Key (Optional)", type="password", help="Required only for Visual AI Analysis")
    
    st.markdown("---")
    # Visual AI moved to Sidebar
    with st.expander("📷 Visual AI Analysis (Image)"):
        uploaded_file = st.file_uploader("Upload Chart", type=["jpg", "png", "jpeg"])
        if uploaded_file is not None and api_key:
            st.image(uploaded_file, caption="Uploaded Chart", width='stretch')
            if st.button("Analyze Image"):
                with st.spinner("AI is analyzing..."):
                    result = vision_analysis.analyze_chart_image(uploaded_file, api_key)
                    st.write(result)
        elif uploaded_file:
            st.warning("Enter API Key above.")

# --- Phase 25: Backtest-Calibrated Rank Adjustment ---
def compute_market_gate(market=None):
    selected_market = market or st.session_state.get("selected_scan_market", "KOSPI")
    return compute_market_gate_live(selected_market)


def compute_rank_adjustment(real_trend, position, strategy_tag, tier, whale_score,
                           vol_ratio, volume_confirmed=None, macro_ctx=None, consec_days=0):
    """Delegate to the shared Decision Score v2 policy implementation."""
    return shared_compute_rank_adjustment(
        real_trend=real_trend,
        position=position,
        strategy_tag=strategy_tag,
        tier=tier,
        whale_score=whale_score,
        vol_ratio=vol_ratio,
        volume_confirmed=volume_confirmed,
        macro_ctx=macro_ctx,
        consec_days=consec_days,
    )

# --- Main Area ---
st.title("🤖 AI Quant Trading Pro")

# --- Phase 34: Global Brain Initialization ---
# Ensure Universal Model exists for Zero-Failure Analysis
if 'universal_model_checked' not in st.session_state:
    with st.spinner("🧠 Initializing Global AI Brain (Universal Model)..."):
        model_path = "models/universal_rf.pkl"
        if not os.path.exists(model_path):
            st.warning("⚠️ Universal Model not found. Training now (this happens once)...")
            qs_init = quant_analysis.QuantStrategy("^KS11")
            qs_init.train_universal_model()
            st.success("✅ Global Brain Activated!")
        st.session_state['universal_model_checked'] = True

# Phase 19: Live Macro Weather Dashboard
if 'macro_ctx' not in st.session_state or st.sidebar.button("🔄 Macro 새로고침"):
    with st.spinner("📡 실시간 매크로 지표 수집 중..."):
        try:
            st.session_state['macro_ctx'] = get_macro_context(force_refresh=True)
        except Exception as _e:
            st.session_state['macro_ctx'] = {'macro_state': 'NORMAL', 'macro_risk_score': 0, 'macro_penalty': 0, 'macro_multiplier': 1.0, 'flags': []}

macro_ctx = st.session_state.get('macro_ctx', {})
macro_state = macro_ctx.get('macro_state', 'NORMAL')
macro_risk  = macro_ctx.get('macro_risk_score', 0)
_mc_colors  = {'NORMAL': ('#1a3a1a', '#4CAF50', '☀️'), 'CAUTION': ('#3a3010', '#FFC107', '⛅'), 'RISK_OFF': ('#3a1010', '#FF5722', '🌧️'), 'CRASH': ('#4a0000', '#FF1744', '🚨')}
_bg, _col, _ico = _mc_colors.get(macro_state, _mc_colors['NORMAL'])

vix_str = f"VIX {macro_ctx['vix']:.1f} ({macro_ctx['vix_change_1d']:+.1f}%)" if macro_ctx.get('vix') else "VIX N/A"
tnx_str = f"10Y {macro_ctx['tnx']:.2f}%" if macro_ctx.get('tnx') else "10Y N/A"
krw_str = f"KRW {macro_ctx['krw']:,.0f} ({macro_ctx['krw_change_1d']:+.2f}%)" if macro_ctx.get('krw') else ""
spy_str = f"SPY {macro_ctx.get('spy_change_1d', 0):+.2f}%"
flags_str = " | ⚠️ " + ", ".join(macro_ctx.get('flags', [])) if macro_ctx.get('flags') else ""

st.markdown(f"""
<div style="padding:12px 18px; border-radius:10px; background:{_bg}; border:1px solid {_col}; margin-bottom:16px;">
  <span style="font-size:1.1em; font-weight:bold; color:{_col};">{_ico} 매크로 날씨: {macro_state}</span>
  <span style="font-size:0.85em; color:#ccc; margin-left:16px;">Risk Score {macro_risk}/100 &nbsp;|&nbsp; {vix_str} &nbsp;|&nbsp; {tnx_str} &nbsp;|&nbsp; {krw_str} &nbsp;|&nbsp; {spy_str}{flags_str}</span>
  {'<br><span style="color:#FF8A80; font-size:0.8em;">⚠️ CRASH: 신규 매수 자제 — 매크로 쇼크 구간</span>' if macro_state == 'CRASH' else ''}
  {'<br><span style="color:#FFCC80; font-size:0.8em;">🌧️ RISK_OFF 감지: Decision Score에 자동 페널티 적용 중</span>' if macro_state == 'RISK_OFF' else ''}
  {'<br><span style="color:#FFF176; font-size:0.8em;">⛅ CAUTION: 매크로 주의 — 고확신 종목 위주로 선별하세요</span>' if macro_state == 'CAUTION' else ''}
</div>
""", unsafe_allow_html=True)

# --- Phase 25: Market Gate (KOSPI/KOSDAQ Daily Gate) ---
# Backtest proved: bad market days have 3~33% win rate → must warn users
_selected_gate_market = st.session_state.get("selected_scan_market", "KOSPI")
if (
    'market_gate' not in st.session_state
    or str(st.session_state.get('market_gate', {}).get('selected_market', '')).upper() != str(_selected_gate_market).upper()
):
    st.session_state['market_gate'] = compute_market_gate(_selected_gate_market)
_gate_info = st.session_state['market_gate']
_gate_colors = {'GREEN': ('#1a3a1a', '#4CAF50'), 'YELLOW': ('#3a3010', '#FFC107'), 'RED': ('#3a0a0a', '#FF5252')}
_gt_bg, _gt_col = _gate_colors.get(_gate_info['gate'], _gate_colors['GREEN'])
st.sidebar.button(
    "🔄 Market Gate 새로고침",
    on_click=lambda: st.session_state.update({
        'market_gate': compute_market_gate(st.session_state.get("selected_scan_market", "KOSPI"))
    }),
)
st.markdown(f"""
<div style="padding:10px 16px; border-radius:8px; background:{_gt_bg}; border:1px solid {_gt_col}; margin-bottom:12px;">
  <span style="font-weight:bold; color:{_gt_col}; font-size:1.0em;">📡 Market Gate [{_gate_info['gate']}]</span>
  <span style="color:#ccc; font-size:0.85em; margin-left:12px;">{_gate_info['msg']}</span>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🚀 스캐너", "📚 아카이브", "🔎 정밀분석"])

# --- Strategy Lab (removed from UI) ---
with tab1:  # dummy context reuse — strategy lab content removed
    pass
if False:
    # Keep lab self-contained: define regime label even when tab1 scanner was not run.
    lab_regime_status = "NEUTRAL"
    if macro_state in ["CRASH", "RISK_OFF"]:
        lab_regime_status = "RISK_OFF"
    elif macro_state == "NORMAL":
        lab_regime_status = "RISK_ON"

    st.header("🧪 Strategy Lab (Antigrav Experiment)")
    st.caption("Phase 30: Advanced Metrics & Simulation Playground")
    
    st.info("이곳은 개발 중인 신규 알고리즘(Tech Score, RRG, Smart Exit)을 테스트하는 실험실입니다.")
    
    # Lab Input
    lab_ticker = st.text_input("실험할 종목코드 (예: 005930, AAPL)", "")
    
    if lab_ticker:
        if lab_ticker.isdigit() and len(lab_ticker) == 6:
            lab_ticker = f"{lab_ticker}.KS"
            
        qs = quant_analysis.QuantStrategy(lab_ticker.upper())
        if qs.fetch_data(period="1y"):
            qs.calculate_indicators()
            qs.check_signals()
            
            # 1. Tech Score Breakdown
            st.subheader("1. Technical Confluence Score (V30)")
            ts_val = qs.df['Antigrav_Score'].iloc[-1] if 'Antigrav_Score' in qs.df.columns else 0
            
            c1, c2 = st.columns(2)
            c1.metric("Pro Tech Score", f"{ts_val:.0f}/100", help="RSI + MA + MACD + Bollinger")
            
            # Fakeout Check
            open_p = qs.df['Open'].iloc[-1]
            close_p = qs.df['Close'].iloc[-1]
            high_p = qs.df['High'].iloc[-1]
            if (high_p - max(open_p, close_p)) > abs(close_p - open_p) * 2:
                 c1.warning("⚠️ Fakeout Warning: Long Upper Wick (-20pts)")
            else:
                 c1.success("✅ Candle Structure: Robust")
                 
            # 2. Smart Exit (Trailing Stop)
            st.subheader("2. Smart Exit Simulation (ATR Trailing Stop)")
            exit_sim = qs.calculate_trailing_stop()
            estatus = exit_sim['status']
            ecolor = "red" if "SELL" in estatus else "green"
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Trailing Stop Price", f"{exit_sim['stop_price']:,.0f}")
            c2.metric("Highest High (20d)", f"{exit_sim['highest_high']:,.0f}")
            c3.markdown(f"Status: <span style='color:{ecolor}; font-weight:bold'>{estatus}</span>", unsafe_allow_html=True)
            
            st.divider()
            
            # 3. XGBoost Features
            st.subheader("3. Advanced AI Features (XGBoost Inputs)")
            f_cols = ['Vol_Change', 'Price_Gap', 'BB_Width', 'ROC_5']
            
            # Check if columns exist
            avail_cols = [c for c in f_cols if c in qs.df.columns]
            
            if avail_cols:
                feat_data = qs.df.iloc[-1][avail_cols]
                
                f1, f2, f3, f4 = st.columns(4)
                if 'Vol_Change' in avail_cols:
                    v_chg = feat_data['Vol_Change']
                    f1.metric("Vol Change", f"{v_chg:.2f}x", delta="Spike" if v_chg > 1.5 else "Low")
                if 'Price_Gap' in avail_cols:
                    p_gap = feat_data['Price_Gap'] * 100
                    f2.metric("Gap %", f"{p_gap:.2f}%", delta="Up" if p_gap > 0 else "Down")
                if 'BB_Width' in avail_cols:
                    bb_w = feat_data['BB_Width']
                    f3.metric("BB Width", f"{bb_w:.2f}", help="Volatility (Low=Squeeze)")
                if 'ROC_5' in avail_cols:
                    roc = feat_data['ROC_5']
                    f4.metric("ROC (5d)", f"{roc:.2f}%")
            else:
                st.info("⚠️ Features not calculated. Please ensure data fetch is complete.")
                
            st.divider()

            # 4. Sector RRG (Visual)
            st.subheader("4. Sector Rotation (RRG) - Trend Visualization")
            sec_data = qs.get_sector_performance()
            
            if sec_data:
                quad = sec_data.get('quadrant', 'Unknown')
                rs_rat = sec_data.get('rs_ratio', 100)
                rs_mom = sec_data.get('rs_mom', 100)
                
                # RRG Plotly Scatter
                rrg_fig = go.Figure()
                
                # Background Quadrants
                rrg_fig.add_shape(type="rect", x0=100, y0=100, x1=120, y1=120, fillcolor="rgba(0,255,0,0.1)", line_width=0, layer="below") # Leading
                rrg_fig.add_shape(type="rect", x0=80, y0=100, x1=100, y1=120, fillcolor="rgba(0,0,255,0.1)", line_width=0, layer="below") # Improving
                rrg_fig.add_shape(type="rect", x0=80, y0=80, x1=100, y1=100, fillcolor="rgba(255,0,0,0.1)", line_width=0, layer="below") # Lagging
                rrg_fig.add_shape(type="rect", x0=100, y0=80, x1=120, y1=100, fillcolor="rgba(255,255,0,0.1)", line_width=0, layer="below") # Weakening
                
                # Axes
                rrg_fig.add_vline(x=100, line_width=1, line_dash="solid", line_color="gray")
                rrg_fig.add_hline(y=100, line_width=1, line_dash="solid", line_color="gray")
                
                # Point
                rrg_fig.add_trace(go.Scatter(
                    x=[rs_rat], y=[rs_mom],
                    mode='markers+text',
                    marker=dict(size=15, color='cyan', line=dict(width=2, color='white')),
                    text=[lab_ticker], textposition="top center",
                    name='Current'
                ))
                
                rrg_fig.update_layout(
                    title="Relative Rotation Graph (RRG)",
                    xaxis_title="RS Ratio (Trend)",
                    yaxis_title="RS Momentum (Velocity)",
                    xaxis=dict(range=[80, 120]),
                    yaxis=dict(range=[80, 120]),
                    width=400, height=400,
                    template="plotly_dark"
                )
                
                c_rrg1, c_rrg2 = st.columns([2, 1])
                with c_rrg1:
                    st.plotly_chart(rrg_fig, width='stretch')
                with c_rrg2:
                    st.markdown(f"**Current: {quad}**")
                    if quad == "Leading": st.success("🚀 주도주: 상승 추세 + 모멘텀 강함")
                    elif quad == "Weakening": st.warning("⚠️ 약화: 추세는 좋으나 힘이 빠짐 (조정 가능성)")
                    elif quad == "Lagging": st.error("❄️ 소외주: 추세 하락 + 모멘텀 약함")
                    elif quad == "Improving": st.info("🌱 회복: 추세는 아직 약하나 모멘텀 살아남 (진입 관찰)")
                    
                    st.metric("Trend Strength", f"{rs_rat:.1f}")
                    st.metric("Velocity", f"{rs_mom:.1f}")
            else:
                 st.write(sec_data)

            st.divider()
            
            st.divider()

            st.divider()

            # 5. Integrated Antigravity Score (V30) - Realtime Logic
            st.subheader("5. Integrated Antigravity Score (V30)")
            
            try:
                # We use defaults for Lab demo if full AI not run yet
                # In a real scenario, this would come from a full analysis run
                val_alpha_v30 = qs.calculate_antigravity_score(
                    win_rate=0.55, 
                    profit_factor=1.5, 
                    ai_return=0, 
                    whale_score=50,
                    sector_data=sec_data,
                    macro_status=lab_regime_status
                )
                
                val_col1, val_col2 = st.columns([1,3])
                with val_col1:
                    st.metric("Antigravity Score", f"{val_alpha_v30}/100", f"{lab_regime_status}")
                with val_col2:
                    if lab_regime_status == 'CRASH':
                        st.error("⚠️ **CRASH DETECTED**: Score Capped at 50. DO NOT BUY.")
                    elif lab_regime_status == 'RISK_OFF':
                        st.warning("🛡️ **Bear Market**: Weights shifted to Whale/Quality. Momentum ignored.")
                    elif lab_regime_status == 'RISK_ON':
                        st.success("🚀 **Bull Market**: Aggressive Momentum Weights active.")
                    else:
                        st.info("⚖️ **Neutral Market**: Balanced Weighting.")
            except Exception as e:
                st.error(f"Calc Error: {e}")

            st.divider()

            # 6. Antigrav Trend Analysis (Visual)
            st.subheader("6. Antigrav Trend Analysis (60 Days)")
            
            if 'Antigrav_Score' in qs.df.columns:
                trend_df = qs.df[['Close', 'Antigrav_Score']].iloc[-60:].copy()
                
                # Dual Axis Chart
                fig_trend = make_subplots(specs=[[{"secondary_y": True}]])
                
                fig_trend.add_trace(
                    go.Scatter(x=trend_df.index, y=trend_df['Close'], name='Price', line=dict(color='gray', width=1)), 
                    secondary_y=False
                )
                fig_trend.add_trace(
                    go.Scatter(x=trend_df.index, y=trend_df['Antigrav_Score'], name='Antigrav Trend', line=dict(color='#00FFAA', width=2)), 
                    secondary_y=True
                )
                
                fig_trend.update_layout(
                    title="Price vs Antigravity Score Correlation", 
                    template="plotly_dark", 
                    height=350,
                    margin=dict(l=10, r=10, t=40, b=10),
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                fig_trend.update_yaxes(title_text="Price", secondary_y=False, showgrid=False)
                fig_trend.update_yaxes(title_text="Antigravity Score", secondary_y=True, range=[0, 100], showgrid=True, gridcolor='rgba(128,128,128,0.2)')
                
                st.plotly_chart(fig_trend, width='stretch')
                
                # Correlation Insight
                corr = trend_df['Close'].corr(trend_df['Antigrav_Score'])
                if corr > 0.5: st.success(f"🔗 Strong Correlation ({corr:.2f}): Antigravity Score leads Price well.")
                elif corr < -0.5: st.error(f"🔗 Inverse Correlation ({corr:.2f}): Score divergence detected.")
                else: st.info(f"🔗 Low Correlation ({corr:.2f}): Score is independent of short-term price.")
            
            st.divider()
            
            # 7. Integrated Antigravity Score (Simulator)
            st.subheader("7. Antigravity Score Simulator (가중치 실험)")
            st.caption("🔍 나만의 전략에 맞춰 가중치를 조절해보세요.")
            
            col_sim1, col_sim2 = st.columns([1, 2])
            
            with col_sim1:
                # Sliders
                w_tech = st.slider("Technical", 0.0, 0.5, 0.2, 0.05)
                w_whale = st.slider("Whale (S/D)", 0.0, 0.5, 0.2, 0.05)
                w_ai = st.slider("AI Forecast", 0.0, 0.5, 0.2, 0.05)
                w_sector = st.slider("Sector (RRG)", 0.0, 0.5, 0.1, 0.05)
                
            with col_sim2:
                # Dynamic Calc
                try:
                    # Robust Fetch or Default
                    wr_lab = 0.55 
                    pf_lab = 1.5
                    
                    # 1. AI Return
                    ai_ret_lab = locals().get('prophet_ret', locals().get('ai_return', 5.0))
                    
                    # 2. Whale Score
                    whale_sc = 50
                    w_data = locals().get('whale_data')
                    w_dict = locals().get('whale')
                    if isinstance(w_data, dict):
                        whale_sc = w_data.get('whale_score', 50)
                    elif isinstance(w_dict, dict):
                        whale_sc = w_dict.get('whale_score', 50)
                    
                    # 3. Sector Score
                    s_sector = 50
                    if sec_data:
                        q = sec_data.get('quadrant')
                        if q == 'Leading': s_sector = 100
                        elif q == 'Improving': s_sector = 80
                        elif q == 'Weakening': s_sector = 40
                        else: s_sector = 20
                    
                    # Component Scores
                    s_tech = ts_val
                    s_whale = whale_sc
                    s_ai = float(min(100.0, max(0.0, float(ai_ret_lab * 5))))
                    
                    # Weighted Sum
                    sim_score = (s_tech * w_tech) + (s_whale * w_whale) + (s_ai * w_ai) + (s_sector * w_sector)
                    
                    # Normalization
                    w_sum = w_tech + w_whale + w_ai + w_sector
                    if w_sum > 0:
                        sim_score = sim_score / w_sum  # Normalize to 0-100 weighted average
                    
                    st.metric("Simulated Antigravity Score", f"{sim_score:.0f}/100")
                    
                    # Verdict
                    if sim_score >= 80: st.success("🔥 POWER BUY (강력 매수)")
                    elif sim_score >= 60: st.success("✅ BUY (매수)")
                    elif sim_score >= 40: st.warning("✋ HOLD (관망)")
                    else: st.error("🔻 SELL/AVOID (매도/회피)")
                    
                    # Breakdown Chart
                    sim_data = pd.DataFrame({
                        'Factor': ['Technical', 'Whale', 'AI', 'Sector'],
                        'Contribution': [s_tech, s_whale, s_ai, s_sector] # Raw scores
                    })
                    # Show raw scores comparison
                    st.caption("Factor Strength (0-100):")
                    st.bar_chart(sim_data.set_index('Factor'))
                    
                except Exception as e:
                    st.error(f"Sim Error: {e}")

# --- Bot Dashboard (removed from UI) ---
if False:
    st.header("🤖 Automated Trading Bot Dashboard")
    st.caption("Live tracking of 24/7 automated signals and paper trading performance.")
    
    from modules import db_manager
    db = db_manager.DBManager()
    
    # Refresh Button
    if st.button("🔄 Refresh Data"):
        st.rerun()
        
    df_sig, win_rate, avg_prof = db.fetch_dashboard_data()
    
    if not df_sig.empty:
        # Top Stats
        k1, k2, k3 = st.columns(3)
        k1.metric("Bot Win Rate (Paper)", f"{win_rate:.1f}%")
        k2.metric("Avg Profit per Trade", f"{avg_prof:.2f}%")
        k3.metric("Total Signals Generated", len(df_sig))
        
        st.subheader("📡 Live Signal Feed")
        st.dataframe(
            df_sig[['created_at', 'stock_name', 'ticker', 'signal_type', 'price', 'alpha_score', 'result_3d']],
            width='stretch'
        )
    else:
        st.info("No signals generated yet. The bot is scanning in the background...")
        st.markdown("### Bot Status")
        st.success("✅ Bot is running (Smart Scheduler Active)")

# --- Batch Analysis (removed from UI) ---
if False:
    st.header("📂 엑셀 일괄 진단 (Batch Deep Dive)")
    st.caption("여러 종목의 엑셀 파일을 업로드하여 AI 정밀 분석을 일괄 수행합니다.")
    
    uploaded_file = st.file_uploader("파일 업로드 (xlsx, csv)", type=['xlsx', 'csv'])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_upload = pd.read_csv(uploaded_file)
            else:
                df_upload = pd.read_excel(uploaded_file)
                
            st.write("미리보기:", df_upload.head(3))
            
            # Column Selection
            col_options = df_upload.columns.tolist()
            default_ix = 0
            if 'Ticker' in col_options: default_ix = col_options.index('Ticker')
            elif 'Symbol' in col_options: default_ix = col_options.index('Symbol')
            elif '종목코드' in col_options: default_ix = col_options.index('종목코드')
            
            ticker_col = st.selectbox("종목코드 컬럼 선택", col_options, index=default_ix)
            
            if st.button("🚀 일괄 분석 시작 (Deep Dive)", type="primary"):
                tickers = df_upload[ticker_col].astype(str).tolist()
                progress_bar = st.progress(0)
                status_text = st.empty()
                log_container = st.expander("📝 진행 상황 & 에러 로그", expanded=True)
                results = []
                
                # --- Parallel Processing Logic (Phase 26) ---
                def process_ticker(raw_ticker):
                    try:
                        ticker = raw_ticker.strip()
                        if ticker.isdigit() and len(ticker) == 6:
                            ticker = f"{ticker}.KS"
                            
                        # 1. Init Strategy
                        qs = quant_analysis.QuantStrategy(ticker)
                        if not qs.fetch_data(period="1y"):
                            return None
                            
                        qs.calculate_indicators()
                        qs.check_signals()
                        
                        if qs.df is None or qs.df.empty: return None
                        
                        latest = qs.df.iloc[-1]
                        
                        # 2. Tech & Fund
                        fund_pass, _ = qs.check_fundamentals()
                        whale = qs.get_investor_flows()  # Use real data (same as Deep Dive)
                        rs = qs.get_relative_strength()
                        
                        # 3. News (Silent)
                        n_score = 0
                        try:
                            na = news_analysis.NewsAnalyzer(ticker)
                            nr = na.get_news_sentiment()
                            n_score = nr.get('score', 0)
                        except: pass
                        
                        # 4. Macro & Sector
                        macro = qs.get_macro_metrics()
                        sector_data = qs.get_sector_performance()
                        
                        # 5. AI Prediction
                        ai_res = qs.predict_future(days=30, sentiment_score=n_score, macro_status=macro['status'])
                        ai_ret = 0
                        if ai_res and 'forecast' in ai_res:
                            try:
                                last_yhat = ai_res['forecast']['yhat'].iloc[-1]
                                ai_ret = ((last_yhat - latest['Close']) / latest['Close']) * 100
                            except: pass
                            
                        # 6. Backtest
                        stats = qs.backtest()
                        try: win_rate = float(stats.get('Win Rate','0').strip('%'))/100
                        except: win_rate = 0
                        try: prof_factor = float(stats.get('Profit Factor','0'))
                        except: prof_factor = 0
                        
                        # 7. Global Brain ML Prediction
                        ml_pred = qs.get_ml_prediction()
                        ml_prob = ml_pred.get('prob', 50)
                        ml_type = ml_pred.get('type', 'N/A')
                        
                        # 8. Antigrav & Verdict (V30 Unified)
                        alpha = qs.calculate_antigravity_score(
                            win_rate, prof_factor, ai_ret, 
                            whale.get('whale_score',0),
                            sector_data=sector_data,
                            macro_status=macro['status']
                        )
                        
                        curr_price = latest['Close']
                        verdict = qs.get_final_verdict(curr_price, ai_res, alpha, macro['status'], rs.get('score',0))
                        setup = qs.get_trade_setup()
                        
                        return {
                            "Ticker": ticker,
                            "Price": curr_price,
                            "Decision": verdict['decision'],
                            "Confidence": verdict['confidence'],
                            "Antigravity Score": alpha,
                            "AI Prob": f"{ml_prob:.1f}%",
                            "AI Type": ml_type,
                            "Sector Leader": "👑" if sector_data.get('is_leader') else "",
                            "AI Return": f"{ai_ret:.1f}%",
                            "Whale Score": whale.get('whale_score', 0),
                            "Entry Zone": f"{setup.get('Entry Min',0):.0f}~{setup.get('Entry Max',0):.0f}",
                            "Target": setup.get('Target Price', 0),
                            "Risk/Reward": setup.get('Risk/Reward', 'N/A')
                        }
                    except Exception as e:
                        return {"error": str(e), "ticker": ticker}

                # Run in Threads
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    futures = {executor.submit(process_ticker, t): t for t in tickers}
                    
                    for i, future in enumerate(concurrent.futures.as_completed(futures)):
                        ticker = futures[future]
                        try:
                            data = future.result()
                            if data:
                                if "error" in data:
                                    with log_container:
                                        st.error(f"❌ {data['ticker']} 분석 실패: {data['error']}")
                                        print(f"Error {data['ticker']}: {data['error']}")
                                else:
                                    results.append(data)
                        except Exception as e:
                             with log_container:
                                st.error(f"❌ {ticker} 실행 중 에러: {e}")
                        
                        progress_bar.progress((i + 1) / len(tickers))
                        status_text.text(f"Analyzing... [{i+1}/{len(tickers)}] {ticker} Completed")
                    
                st.success(f"✅ 분석 완료! ({len(results)}/{len(tickers)} 성공)")
                
                if results:
                    df_res = pd.DataFrame(results)
                    
                    # Style the dataframe?
                    # Color map for Decision
                    def color_decision(val):
                        color = 'white'
                        if 'BUY' in val: color = '#90EE90' # Light Green
                        elif 'SELL' in val: color = '#FFB6C1' # Light Red
                        elif 'HOLD' in val: color = '#FFE4B5' # Moccasin
                        return f'background-color: {color}; color: black'
                        
                    st.dataframe(df_res.style.applymap(color_decision, subset=['Decision']), width='stretch')
                    
                    # CSV Download
                    csv = df_res.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 분석 결과 다운로드 (CSV)", csv, "deep_dive_batch_results.csv", "text/csv")

        except Exception as e:
            st.error(f"파일 처리 에러: {e}")

# TAB 1: MARKET SCANNER
with tab1:
    st.header("🚀 전종목 자동 스캔")
    col1, col2, col3, col4 = st.columns(4)
    market = col1.selectbox(
        "시장 선택 (Market)",
        ["KOSPI", "KOSDAQ", "NASDAQ", "S&P500", "AMEX"],
        key="selected_scan_market",
    )
    max_scan = col2.slider("스캔 개수 (0=전종목)", 0, 3500, 0)
    scan_mode_label = col3.selectbox("스캔 모드", ["스윙", "장중"], index=0)
    scan_mode = "INTRADAY" if scan_mode_label == "장중" else "SWING"
    col4.markdown(
        "**🧠 Filter Mode**<br>"
        + ("⏱️ Intraday Breakout / Trend" if scan_mode == "INTRADAY" else "🔥 Antigravity Score (Single Standard)"),
        unsafe_allow_html=True,
    )
    
    st.markdown("---")
    
    engine_opt = st.radio(
        "⚙️ 백테스트 & 분석 엔진 (Engine Mode)",
        ["🚀 기본 엔진 (Legacy: T+0 종가 진입, 수수료 0%, 선형 거래량비례)", 
         "🔬 완전무결 엔진 (V32.Flawless: T+1 시가 진입, 실전 슬리피지 적용, U-Shape 거래량 보정, 소표본 પે널티)"],
        horizontal=True
    )
    is_advanced_engine = "완전무결" in engine_opt
    st.markdown("---")
    
    if st.button("시장 스캔 시작", type="primary"):
        st.info(
            "⏳ 데이터를 수집하고 분석하는 중입니다... "
            + ("(장중 1시간봉 기준)" if scan_mode == "INTRADAY" else "(스윙 일봉 기준)")
        )
        live_refresh = live_mode_enabled(market)
        intel_force_refresh = True
        try:
            st.session_state['macro_ctx'] = get_macro_context(
                force_refresh=live_refresh,
                market_group=normalize_market_key(market),
            )
        except Exception:
            pass
        st.session_state['market_gate'] = compute_market_gate(market)

        # [Phase 4] Market Regime Detection
        regime = quant_analysis.QuantStrategy.detect_market_regime(market)
        r_status = regime.get('regime', 'NEUTRAL')
        regime_label = f"{regime['emoji']} 시장 레짐: **{regime['regime']}** — {regime['desc']}"
        
        if regime['regime'] == 'BULL':
            st.success(regime_label)
        elif regime['regime'] == 'BEAR':
            st.error(regime_label + " ⚠️ **하락장 — 스캔 결과 더욱 엄격히 필터링됩니다**")
        else:
            st.warning(regime_label)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Get Tickers (Returns Dict: {Ticker: Name})
        tickers_dict = quant_analysis.QuantStrategy.get_market_tickers(market)
        ticker_list = list(tickers_dict.keys())
        planned_scan_count = len(ticker_list) if max_scan <= 0 else min(len(ticker_list), max_scan)
        status_text.text(f"총 {len(ticker_list)}개 종목을 불러왔습니다. 이번 스캔 대상: {planned_scan_count}개")
        
        results = []
        scan_diagnostics = {
            "filtered_count": 0,
            "worker_error_count": 0,
            "executor_exception_count": 0,
            "filtered_symbols": [],
            "error_symbols": [],
            "exception_symbols": [],
            "reject_reason_counts": {},
            "reject_reasons_by_symbol": {},
            "reject_details_by_symbol": {},
        }
        stop_placeholder = st.empty()
        
        # --- Phase 40: Market Intelligence (Gemini LLM) ---
        gemini_key = os.environ.get('GEMINI_API_KEY', '')
        intel_data = market_intelligence.get_market_intelligence(market, gemini_key, force_refresh=intel_force_refresh)
        
        if intel_data:
            with st.expander(f"🧠 AI 시장 인텔리전스 ({intel_data.get('timestamp', '')})", expanded=True):
                sent = intel_data.get('market_sentiment', 'NEUTRAL')
                sent_icon = {'BULLISH': '🟢', 'BEARISH': '🔴', 'MIXED': '🟡', 'NEUTRAL': '⚪'}.get(sent, '⚪')
                st.caption(f"Source: {intel_data.get('source', 'unknown')} | Market: {market}")
                if str(intel_data.get('source', 'unknown')).startswith('fallback'):
                    st.warning("시장 뉴스 헤드라인을 충분히 수집하지 못해 fallback 인텔리전스를 사용 중입니다.")
                st.markdown(f"**시장 분위기**: {sent_icon} **{sent}** (점수: {intel_data.get('sentiment_score', 0)})")
                st.markdown(f"**핵심 인사이트**: {intel_data.get('key_insight', 'N/A')}")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    ben = intel_data.get('beneficiary_sectors', [])
                    if ben:
                        st.success(f"🔥 수혜 섹터: {', '.join(ben)}")
                with col_b:
                    vic = intel_data.get('victim_sectors', [])
                    if vic:
                        st.error(f"⚠️ 피해 섹터: {', '.join(vic)}")
                
                themes = intel_data.get('themes', [])
                if themes:
                    for t in themes[:3]:
                        impact_icon = {'POSITIVE': '📈', 'NEGATIVE': '📉', 'MIXED': '↔️'}.get(t.get('impact', ''), '📌')
                        st.markdown(f"{impact_icon} **{t.get('theme', '')}**: {t.get('description', '')}")
                macro_drivers = intel_data.get('macro_drivers', [])
                if macro_drivers:
                    st.markdown("**거시 드라이버**")
                    for driver in macro_drivers[:5]:
                        signal_icon = {
                            'BULLISH': '📈',
                            'BEARISH': '📉',
                            'MIXED': '↔️',
                            'NEUTRAL': '📌',
                        }.get(str(driver.get('signal', 'NEUTRAL')).upper(), '📌')
                        category = driver.get('category', 'UNKNOWN')
                        impact = driver.get('market_impact', 0)
                        desc = driver.get('description', '')
                        st.markdown(f"{signal_icon} **{category}** ({impact:+}): {desc}")
                cross_asset = intel_data.get('cross_asset_signals', [])
                if cross_asset:
                    st.markdown("**크로스애셋 시그널**")
                    for item in cross_asset[:4]:
                        asset = item.get('asset', 'N/A')
                        direction = item.get('direction', 'N/A')
                        impact = item.get('market_impact', 0)
                        desc = item.get('description', '')
                        st.caption(f"• {asset} {direction} ({impact:+}) — {desc}")
                risk_flags = intel_data.get('risk_flags', [])
                if risk_flags:
                    st.warning(f"리스크 플래그: {', '.join(risk_flags[:6])}")
                # --- 테마 모멘텀 (Naver 실시간) ---
                try:
                    import json as _json
                    from pathlib import Path as _Path
                    _theme_cache_path = _Path("runtime_state/long_term/theme_cache/KR.json")
                    if _theme_cache_path.exists():
                        _tc = _json.loads(_theme_cache_path.read_text(encoding="utf-8"))
                        _mom_updated = _tc.get("theme_momentum_updated_at")
                        _states = [s for s in (_tc.get("theme_states") or []) if s.get("momentum_avg_change_pct") is not None]
                        if _states:
                            _mom_ts = _mom_updated[:16].replace("T", " ") if _mom_updated else "?"
                            st.markdown(f"**테마 모멘텀** <span style='color:gray;font-size:0.8em'>Naver 실시간 · {_mom_ts}</span>", unsafe_allow_html=True)
                            _class_icons = {"EXPLODING": "🔥", "ACCELERATING": "📈", "STEADY": "➡️", "FADING": "📉"}
                            for _s in sorted(_states, key=lambda x: abs(x.get("momentum_avg_change_pct", 0)), reverse=True):
                                _pct = _s["momentum_avg_change_pct"]
                                _mc = _s.get("momentum_class") or ("EXPLODING" if _pct >= 2 else "ACCELERATING" if _pct >= 0.5 else "FADING" if _pct <= -0.5 else "STEADY")
                                _icon = _class_icons.get(_mc, "➡️")
                                _dir = _s.get("direction", "")
                                _dir_tag = " 🟢수혜" if _dir == "BENEFICIARY" else " 🔴역풍" if _dir == "HEADWIND" else ""
                                st.caption(f"{_icon} **{_s['theme_name']}** {_pct:+.2f}% [{_mc}]{_dir_tag}")
                except Exception:
                    pass

                evidence = intel_data.get('evidence_headlines') or intel_data.get('raw_headlines') or []
                if evidence:
                    st.markdown("**근거 헤드라인**")
                    for line in evidence[:4]:
                        st.caption(f"• {line}")
        
        # --- Parallel Processing Logic (Phase 26) ---
        is_us = market in ["NASDAQ", "S&P500", "AMEX"]
        is_amex = market == "AMEX"
        
        def scan_worker(sym):
            def _on_reject(_sym, reason):
                code = str(reason or "UNKNOWN")
                counts = scan_diagnostics["reject_reason_counts"]
                counts[code] = int(counts.get(code, 0) or 0) + 1
                scan_diagnostics["reject_reasons_by_symbol"][_sym] = code

            def _on_reject_detail(_sym, meta):
                details = scan_diagnostics["reject_details_by_symbol"]
                if not isinstance(details.get(_sym), list):
                    details[_sym] = []
                if isinstance(meta, dict):
                    details[_sym].append(meta)

            return scan_symbol_with_retry(
                sym=sym,
                tickers_dict=tickers_dict,
                is_us=bool(is_us),
                is_amex=bool(is_amex),
                is_advanced_engine=bool(is_advanced_engine),
                r_status=str(r_status),
                intel_data=intel_data,
                macro_ctx=st.session_state.get('macro_ctx'),
                market_gate=st.session_state.get('market_gate', {}),
                rank_adjustment_fn=compute_rank_adjustment,
                news_adjustment_fn=market_intelligence.calculate_news_adjustment,
                backoff_state=_SCAN_BACKOFF_STATE,
                max_retries=2,
                scan_mode=scan_mode,
                reject_reason_fn=_on_reject,
                reject_detail_fn=_on_reject_detail,
            )

        # Run in Threads
        log_container = st.expander("📝 스캔 로그", expanded=True)
        scan_ui_logs = []

        def _on_scan_item(i, total_scans, sym, data, exc):
            if exc is not None:
                scan_diagnostics["executor_exception_count"] += 1
                scan_diagnostics["exception_symbols"].append(sym)
                scan_ui_logs.append(("error", f"❌ {sym} 실행 중 에러: {exc}"))
            else:
                if data:
                    if "error" in data:
                        scan_diagnostics["worker_error_count"] += 1
                        scan_diagnostics["error_symbols"].append(sym)
                        scan_ui_logs.append(("error", f"❌ {data['ticker']} 스캔 중 에러: {data['error']}"))
                    else:
                        results.append(data)
                else:
                    scan_diagnostics["filtered_count"] += 1
                    scan_diagnostics["filtered_symbols"].append(sym)
                    print(f"[{i+1}/{total_scans}] {sym} ... Checked (Filtered/Skipped)")

        run_parallel_scan(
            ticker_list=ticker_list,
            max_scan=max_scan,
            worker_fn=scan_worker,
            max_workers=2,
            on_item=_on_scan_item,
        )

        progress_bar.progress(1.0)
        status_text.text("✅ 스캔 완료!")
        with log_container:
            if scan_ui_logs:
                for level, line in scan_ui_logs[:100]:
                    if level == "error":
                        st.error(line)
                    elif level == "warning":
                        st.warning(line)
                    else:
                        st.caption(line)
            else:
                st.caption("실행 오류 없이 스캔이 완료되었습니다.")
        bridge_info = run_legacy_agent_bridge(
            results=results,
            market=market,
            strategy_version="legacy-ui-v1",
            model_version="legacy",
            code_version="bridge-v1",
            summary_overrides={
                "total_scans": planned_scan_count,
                "diagnostics": scan_diagnostics,
                "market_gate": st.session_state.get('market_gate', {}),
                "regime": regime,
                "execution_profile": os.getenv("AG_SCAN_PROFILE", "prod"),
                "warnings": [],
                "source": "scanner_agent_input",
                "scan_mode": scan_mode,
            },
            logger=st.caption,
        )
        if not bridge_info.get("ok", False):
            st.caption("⚠️ Agent bridge completed with warnings.")

        if results:
            st.caption(f"📡 선택 시장 게이트: {st.session_state.get('market_gate', {}).get('msg', '')}")
            planner_payload = _load_json_safe(bridge_info.get("planner_handoff"))
            planner_decisions = planner_payload.get("decisions", []) if isinstance(planner_payload.get("decisions"), list) else []
            planner_warnings = planner_payload.get("global_warnings", []) if isinstance(planner_payload.get("global_warnings"), list) else []
            planner_warning_codes = {str(w.get("code") or "") for w in planner_warnings if isinstance(w, dict)}
            watchlist_only_mode = (
                not planner_decisions
                and (
                    "MARKET_POLICY_WATCHLIST_ONLY" in planner_warning_codes
                    or "FALLBACK_WATCHLIST_ENABLED" in planner_warning_codes
                    or "EMPTY_PLANNER_INPUT" in planner_warning_codes
                )
            )

            # --- Tier Summary ---
            def _norm_tier(row):
                return str(row.get('Tier', '') or '').strip()

            t0_rows = [r for r in results if _norm_tier(r).startswith('⚡T0')]
            t1_rows = [r for r in results if _norm_tier(r).startswith('🏆T1')]
            t2_rows = [r for r in results if _norm_tier(r).startswith('⭐T2')]
            t3_rows = [r for r in results if _norm_tier(r) in {'T3', '⚡T3'} or _norm_tier(r).endswith('T3')]

            t0_count = len(t0_rows)
            t1_count = len(t1_rows)
            t2_count = len(t2_rows)
            t3_count = len(t3_rows)
            if watchlist_only_mode:
                st.warning(
                    "⚠️ 이번 결과는 스캐너 후보가 있었더라도 플래너가 `watchlist-only`로 내린 상태입니다. "
                    "즉, 아래 종목들은 즉시 매수 추천이 아니라 관찰 후보로 봐야 합니다."
                )
                st.info(
                    f"스캐너 후보 {len(results)}개 | ⚡T0: {t0_count} | 🏆T1: {t1_count} | ⭐T2: {t2_count} | T3: {t3_count}"
                )
            else:
                st.success(f"💡 **{len(results)}개** 투자 기회 발견! — ⚡ T0초강력: **{t0_count}**개 | 🏆 T1: **{t1_count}**개 (승률71%) | ⭐ T2: **{t2_count}**개 | T3: {t3_count}개")
                if t0_count > 0:
                    t0_names = [str(r.get('종목명') or r.get('티커', 'Unknown')) for r in t0_rows]
                    st.error(f"⚡ **초강력 매수 신호 {t0_count}개**: {', '.join(t0_names)} — 상한가/5%+ 이상 기대")
            
            df_results = pd.DataFrame(results)

            # ── v3 스코어 enrichment (Phase 19) ──────────────────────────
            # Meta-Quality 모델이 있으면 clean_hit_prob / expected_mae로 보정
            # 모델 없으면 기본값으로 안전하게 동작
            try:
                from modules.meta_quality_ranker import predict_meta_quality
                from modules.regime_classifier import classify_regime
                from modules.regime_router import compute_v3_score_regime_aware, get_prob5_threshold
                _regime_result = classify_regime(market)
                _regime = _regime_result.get("regime", "UNKNOWN")
                _enriched = []
                for _row in results:
                    _alpha  = float(_row.get("Antigrav") or _row.get("alpha_score") or 50)
                    _whale  = float(_row.get("Whale") or _row.get("whale_score") or 50)
                    _prob5  = float(_row.get("_prob_5") or _row.get("ml_prob") or 50)
                    _probcl = float(_row.get("_prob_clean") or _prob5)
                    _vol_r  = float(_row.get("Vol Ratio") or _row.get("vol_ratio") or 1.0)
                    _volcfm = bool(_row.get("Vol Confirmed") or _row.get("volume_confirmed"))
                    _trend  = str(_row.get("Trend") or _row.get("trend") or "")
                    _real_trend = "UP" if "UP" in _trend.upper() else ("DOWN" if "DOWN" in _trend.upper() else "SIDE")
                    _atr    = float(_row.get("_atr_pct") or 0)
                    _p2ma20 = float(_row.get("_price_to_ma20") or 1.0)
                    _p2ma50 = float(_row.get("_price_to_ma50") or 1.0)
                    _mq = predict_meta_quality(
                        alpha_score=_alpha, vol_ratio=_vol_r,
                        atr_pct=_atr, price_to_ma20=_p2ma20, price_to_ma50=_p2ma50,
                    )
                    _v3 = compute_v3_score_regime_aware(
                        prob_5=_prob5, prob_clean=_probcl,
                        alpha_score=_alpha, whale_score=_whale,
                        real_trend=_real_trend, volume_confirmed=_volcfm, vol_ratio=_vol_r,
                        clean_hit_prob=_mq["clean_hit_prob"],
                        fast_hit_prob=_mq["fast_hit_prob"],
                        expected_mae_pct=_mq["expected_mae_pct"],
                        regime=_regime,
                    )
                    _enriched.append({**_row, "v3_score": _v3["v3_score"], "v3_detail": _v3})
                df_results = pd.DataFrame(_enriched)
            except Exception:
                pass  # enrichment 실패 시 원본 df_results 유지

            st.divider()
            try:
                # Phase 18/19/20 Threshold + Top-K Hybrid Ranking (Regime + Mode Aware)
                # SWING: v3_score 우선 정렬 (5d 수익 기반 캘리브레이션)
                # INTRADAY: Decision Score 우선 정렬 (Codex tuned, 1d 휴리스틱 범위)
                # prob5 임계값: scan_mode + regime 모두 반영
                try:
                    from modules.regime_router import get_prob5_threshold
                    from modules.regime_classifier import classify_regime
                    _rc = classify_regime(market)
                    PROB5_THRESHOLD = get_prob5_threshold(_rc.get("regime", "UNKNOWN"), scan_mode)
                except Exception:
                    PROB5_THRESHOLD = 50.0 if scan_mode == "INTRADAY" else 58.0
                TOP_K = 5
                # INTRADAY: expected_return_1d_pct 우선 → fallback Decision Score
                # (실증 데이터: DS 상위 Top5=36% vs expected_1d 상위 Top5=60%)
                # SWING: v3_score(5d MAE/clean_hit 보정) 우선
                if scan_mode == "INTRADAY":
                    if 'expected_return_1d_pct' in df_results.columns:
                        sort_col = 'expected_return_1d_pct'
                        sort_secondary = 'Decision Score'
                    else:
                        sort_col = 'Decision Score'
                        sort_secondary = 'Antigrav'
                else:
                    sort_col = 'v3_score' if 'v3_score' in df_results.columns else 'Decision Score'
                    sort_secondary = 'Antigrav'
                df_results = df_results.sort_values(
                    by=[sort_col, sort_secondary], ascending=[False, False]
                )

                cols_to_drop = ['_tier_sort', '_prob_5', '_prob_clean']

                # 거래량 확인 여부 — '거래량'(KR) 또는 'Volume'(US) 컬럼의 ✅/⚠️ 기호로 판단
                def _vol_ok(row):
                    for col in ('거래량', 'Volume'):
                        v = str(row.get(col, ''))
                        if '✅' in v: return True
                        if '⚠️' in v: return False
                    return True  # 컬럼 없으면 차단하지 않음

                if '_prob_5' in df_results.columns:
                    _vol_mask = df_results.apply(_vol_ok, axis=1)
                    # above: 확률 통과 AND 거래량 확인
                    _prob_pass = df_results['_prob_5'] >= PROB5_THRESHOLD
                    above = df_results[_prob_pass & _vol_mask]
                    # below: 나머지 전체 (거래량 미확인 포함 — shortage 보완용)
                    below = df_results[~_prob_pass | ~_vol_mask]
                    shortage = max(0, TOP_K - len(above))
                    # shortage 보완 시에도 거래량 확인 종목 우선
                    below_sorted = pd.concat([
                        below[_vol_mask.reindex(below.index, fill_value=False)],
                        below[~_vol_mask.reindex(below.index, fill_value=True)],
                    ])
                    top5 = pd.concat([above.head(TOP_K), below_sorted.head(shortage)]).head(TOP_K).copy()
                    prob5_passed = min(len(above), TOP_K)
                else:
                    top5 = df_results.head(TOP_K).copy()
                    prob5_passed = TOP_K

                top5_idx = top5.index
                top5_display = top5.drop(columns=[col for col in cols_to_drop if col in top5.columns])

                _sort_label = "Decision Score" if scan_mode == "INTRADAY" else sort_col
                threshold_caption = (
                    f"AI 확률 {PROB5_THRESHOLD:.0f}% 이상 통과: **{prob5_passed}/{len(top5_display)}개** — "
                    + ("전원 고확신 종목" if prob5_passed == len(top5_display)
                       else f"{len(top5_display) - prob5_passed}개는 임계값 미달이나 {_sort_label} 순으로 보완")
                )

                # ── 핵심 컬럼만 선택 + 한글 rename ────────────────────────
                # 컬럼명은 KR/US/INTRADAY마다 다를 수 있어 여러 alias를 등록
                _SCANNER_CORE_COLS = {
                    # (raw_col_name): (한글명, 툴팁)
                    '종목명':        ('종목명',      None),
                    'Ticker':        ('코드',        None),
                    '티커':          ('코드',        None),
                    'Tier':          ('등급',        'T0=초강력 / T1=강력(승률71%) / T2=관심 / T3=참고'),
                    # 현재가 — KR은 매수가(-2%)에 현재가 저장, US는 Entry(-2%)
                    '매수가(-2%)':   ('현재가',      '스캔 시점 현재가 (진입 기준가. -2% 할인 전 원래 가격)'),
                    'Entry(-2%)':    ('현재가',      '스캔 시점 현재가'),
                    # 전일비 — KR swing/intraday 모두 '전일비' 키, US는 '1D Change'
                    '전일비':        ('전일비(%)',   '스캔 당시 전일 종가 대비 등락률. 스캔 시점의 모멘텀을 보여줌'),
                    '1D Change':     ('전일비(%)',   '스캔 당시 전일 종가 대비 등락률'),
                    # 확률/스코어
                    'AI확률':        ('AI확률',      'ML 모델이 예측한 5% 이상 달성 확률. 58% 이상이 진입 기준'),
                    'AI Prob':       ('AI확률',      'ML 모델이 예측한 5% 이상 달성 확률. 58% 이상이 진입 기준'),
                    'v3_score':      ('종합점수',    '추세·거래량·수급·리스크를 곱셈 공식으로 통합한 최종 순위 점수 (0~100). 높을수록 우선'),
                    'Decision Score':('Decision점수','Antigrav + AI확률 + 추세 + 수급을 가중 합산한 원시 스코어'),
                    'Antigrav':      ('Antigrav',    '기술적 모멘텀·섹터 강도·AI수익 기대치를 합산한 핵심 동력 지수 (0~100). 70+이면 강세 신호'),
                    '수급':          ('수급',        '기관·외국인 수급 강도 (장중=당일 거래량 기반 추정)'),
                    'Whale':         ('수급점수',    '기관·외국인 수급 강도 지수 (0~100). 60 이상이면 수급 유입 신호'),
                    # 추세/거래량
                    'Trend':         ('추세',        'UP=상승추세 / SIDE=횡보 / DOWN=하락추세. UP+거래량확인 조합이 최고 신호'),
                    '추세':          ('추세',        'UP=상승추세 / SIDE=횡보 / DOWN=하락추세'),
                    'Vol Confirmed': ('거래량확인',  '평균 대비 1.5배 이상 거래량 + 방향 확인 여부. True이면 모멘텀 신뢰도 높음'),
                    '거래량':        ('거래량',      '평균 대비 거래량 배율 (✅=확인됨, ⚠️=미확인)'),
                    # 예상수익
                    'expected_return_1d_pct': ('예상1D(%)', '스캐너가 예측하는 1일 기대수익률(%). 인트라데이 정렬 기준'),
                    'expected_return_3d_pct': ('예상3D(%)', '스캐너가 예측하는 3일 기대수익률(%)'),
                    # 기타
                    '위치':          ('포지션',      '가격 위치 (Peak=천장권 / Rising=상승중 / Resting=눌림목)'),
                    'Position':      ('포지션',      '가격 위치 (Peak=천장권 / Rising=상승중 / Resting=눌림목)'),
                    '전략':          ('전략',        '스캐너가 판단한 진입 전략 유형'),
                    'Strategy Tag':  ('전략',        '스캐너가 판단한 진입 전략 유형'),
                    '테마':          ('대표테마',    '현재 시장에서 해당 종목이 속한 주도 테마'),
                    'primary_theme': ('대표테마',    '현재 시장에서 해당 종목이 속한 주도 테마'),
                }
                def _prep_scanner_df(df_in):
                    """핵심 컬럼만 추출하고 한글로 rename."""
                    present = [c for c in _SCANNER_CORE_COLS if c in df_in.columns]
                    df_out = df_in[present].copy()
                    df_out = df_out.rename(columns={c: _SCANNER_CORE_COLS[c][0] for c in present})
                    return df_out

                def _scanner_col_config(df_in):
                    """column_config dict — 툴팁 포함."""
                    cfg = {}
                    for raw_col, (kr_name, tip) in _SCANNER_CORE_COLS.items():
                        if raw_col in df_in.columns and tip:
                            cfg[kr_name] = st.column_config.TextColumn(kr_name, help=tip)
                    return cfg

                _top5_kr = _prep_scanner_df(top5_display)
                _rest_raw = df_results[~df_results.index.isin(top5_idx)].drop(
                    columns=[col for col in cols_to_drop if col in df_results.columns]
                )
                _rest_kr = _prep_scanner_df(_rest_raw)

                if watchlist_only_mode:
                    st.markdown("### 📋 Top 5 후보" + (" (장중)" if scan_mode == "INTRADAY" else ""))
                    st.caption("스캐너 원시 후보입니다. 플래너가 매수 추천으로 승격하지 않았으므로 관찰용입니다.")
                    st.dataframe(_top5_kr, column_config=_scanner_col_config(top5_display),
                                 use_container_width=True, hide_index=True)
                else:
                    st.markdown("### 🔥 Top 5 매수 후보" + (" (장중)" if scan_mode == "INTRADAY" else ""))
                    st.caption(threshold_caption)
                    st.dataframe(_top5_kr, column_config=_scanner_col_config(top5_display),
                                 use_container_width=True, hide_index=True)

                st.divider()

                # 2. Remaining qualified setups
                st.markdown("### 📋 추가 후보" if not watchlist_only_mode else "### 📋 기타 스캔 종목")
                if not _rest_kr.empty:
                    st.dataframe(_rest_kr, column_config=_scanner_col_config(_rest_raw),
                                 use_container_width=True, hide_index=True)
                else:
                    st.info("Top 5 외에 추가 종목이 없습니다.")
                st.divider()
                _render_agent_bridge_status(bridge_info, market)
            except Exception as e:
                # Fallback to old simple render
                # print(f"Render format error: {e}")
                st.dataframe(df_results, width='stretch')
                st.divider()
                _render_agent_bridge_status(bridge_info, market)
        else:
            st.warning("⚠️ 조건에 맞는 종목을 찾지 못했습니다.")
            _render_agent_bridge_status(bridge_info, market)

    # --- Excel Upload Scanner ---
    st.markdown("---")
    with st.expander("📂 나만의 종목 스캔 (Excel 업로드)", expanded=False):
        st.caption("엑셀 파일을 업로드하면 해당 종목들만 집중 분석합니다. (필수 컬럼: 'Code' 또는 'Ticker')")
        u_file = st.file_uploader("Excel/CSV 파일 업로드", type=['xlsx', 'xls', 'csv'], key="excel_upload_scanner")
        if u_file and st.button("파일 스캔 시작", type="primary"):
            try:
                if u_file.name.endswith('.csv'):
                    udf = pd.read_csv(u_file)
                else:
                    udf = pd.read_excel(u_file)
                code_col = None
                for c in udf.columns:
                    if c.lower() in ['code', 'ticker', 'symbol', '종목코드', '티커']:
                        code_col = c
                        break
                if not code_col:
                    st.error("❌ 'Code' 또는 'Ticker' 컬럼을 찾을 수 없습니다.")
                else:
                    target_tickers = udf[code_col].astype(str).tolist()
                    st.info(f"📋 파일에서 {len(target_tickers)}개 종목을 확인했습니다. 스캔을 시작합니다...")
                    u_progress = st.progress(0)
                    u_status = st.empty()
                    u_results = []
                    for i, sym in enumerate(target_tickers):
                        sym = normalize_uploaded_ticker(sym)
                        u_status.text(f"🔍 Analyzing {sym}...")
                        u_progress.progress((i+1)/len(target_tickers))
                        try:
                            eval_result = evaluate_uploaded_candidate(ticker=sym, display_name=sym)
                            if not eval_result:
                                continue
                            u_results.append(eval_result["ui_row"])
                            db = db_manager.DBManager()
                            db.save_scan_result(eval_result["db_payload"])
                        except Exception:
                            continue
                    if u_results:
                        st.success("✅ 파일 스캔 완료!")
                        st.dataframe(pd.DataFrame(u_results), width='stretch')
            except Exception as e:
                st.error(f"파일 처리 중 오류 발생: {e}")

# TAB 3: SINGLE STOCK ANALYSIS (정밀분석)
with tab3:
    st.header("🔎 정밀분석 — 종목 심층 분석")
    
    col_input, col_opt = st.columns([3, 1])
    ticker = col_input.text_input(
        "종목 코드 입력 (Ticker)",
        value=st.session_state.get("deep_dive_ticker", "AAPL"),
        help="예: AAPL, TSLA, 005930.KS",
    )
    st.session_state["deep_dive_ticker"] = ticker
    time_opt = col_opt.selectbox("차트/예측 단위", ["Daily (1일)", "4-Hour (4시간)"])
    
    interval = "4h" if "4-Hour" in time_opt else "1d"
    
    if st.button("🚀 AI 정밀 분석 실행", type="primary"):
        with st.spinner(f"'{ticker}'에 대한 Pro-Quant 분석을 수행하고 있습니다..."):
            
            # Try to fetch real name
            stock_name = ticker
            try:
                t_info = quant_analysis.yf.Ticker(ticker).info
                stock_name = t_info.get('shortName') or t_info.get('longName') or ticker
            except: pass
            
            st.markdown(f"## 🏢 {stock_name} ({ticker})") # Display Name
            
            qs = quant_analysis.QuantStrategy(ticker)
            
            # Warn about 4H
            if interval == "4h":
                st.info("ℹ️ 4시간 단위 분석은 최근 2년 데이터만 사용하며, 변동성이 클 수 있습니다.")

            if qs.fetch_data(period="max", interval=interval):
                qs.calculate_indicators()
                qs.check_signals()
                stats = qs.backtest()
                latest = qs.get_latest_metrics()
                setup = qs.get_trade_setup()
                latest = qs.df.iloc[-1]
                
                # --- Price Board (Real-time Data) ---
                st.markdown("### 📊 Market Data (매매 데이터)")
                # Fetch Real-time Price explicitly
                rt_price = qs.get_realtime_price()
                if rt_price == 0: rt_price = latest['Close'] # Fallback
                
                # Check deviation
                dev = ((rt_price - latest['Close']) / latest['Close']) * 100
                dev_color = "normal" if abs(dev) < 1 else "off"
                
                p1, p2, p3, p4, p5 = st.columns(5)
                is_kr = ".KS" in ticker or ".KQ" in ticker
                currency = "₩" if is_kr else "$"
                p_fmt = "{:,.0f}" if is_kr else "{:,.2f}"
                
                # Fetch Position
                pos_status = qs.get_price_position()
                
                p1.metric("현재가 (Real-time)", f"{currency}{p_fmt.format(rt_price)}", f"{pos_status}", delta_color="off")
                p2.metric("시가 (Open)", f"{currency}{p_fmt.format(latest['Open'])}")
                p3.metric("고가 (High)", f"{currency}{p_fmt.format(latest['High'])}")
                p4.metric("저가 (Low)", f"{currency}{p_fmt.format(latest['Low'])}")
                p5.metric("거래량 (Vol)", f"{latest['Volume']:,}")
                
                st.divider()

                # --- Phase 18: Macro & Context Dashboard ---
                st.markdown("### 🌍 시장/섹터 컨텍스트 (Hyper-Accuracy)")
                
                # Fetch Latest Context Data
                latest = qs.df.iloc[-1]
                
                # 1. Macro Cards
                c1, c2, c3, c4 = st.columns(4)
                
                # VIX
                vix = latest.get('VIX', 0)
                vix_color = "red" if vix > 25 else "green"
                c1.metric("🌪️ 공포지수(VIX)", f"{vix:.2f}", delta=None, delta_color="inverse")
                if vix > 25: c1.caption(f":{vix_color}[공포 구간]")
                else: c1.caption(f":{vix_color}[안정 구간]")
                
                # TNX
                tnx = latest.get('TNX', 0)
                c2.metric("💵 미 국채 10년", f"{tnx:.2f}%")
                
                # Sector RS (Phase 22)
                sector_data = qs.get_sector_performance()
                s_ratio = sector_data.get('rs_ratio', 0)
                s_lead = "👑 주도주" if sector_data.get('is_leader') else "💤 소외주"
                lead_color = "normal" if sector_data.get('is_leader') else "off"
                
                c3.metric("🏆 섹터 대비 강도", f"{s_ratio:+.2f}%", s_lead, delta_color=lead_color)
                
                # Relative Strength (Old) -> Rename to Market Trend? 
                # Or keep as internal RS
                rs = latest.get('RS_Mansfield', 0)
                rs_emoji = "🔥" if rs > 0 else "☁️"
                c4.metric("💪 시장 대비 강도", f"{rs:.2f}", f"{rs_emoji} (Mansfield)")
                
                st.divider()
                
                # Update Antigravity Score with Sector Data
                # Re-calculate Antigrav
                # Parse Win Rate string "55.0%" -> 0.55
                wr_str = stats.get("Win Rate", "0").replace('%', '')
                try: wr_val = float(wr_str) / 100.0
                except: wr_val = 0
                
                pf_str = stats.get("Profit Factor", "0")
                try: pf_val = float(pf_str)
                except: pf_val = 0
                

                
                
                curr_price = qs.df['Close'].iloc[-1]
                
                # Fetch Whale Data
                whale_data = qs.get_investor_flows()
                
                # Fetch Macro Data
                try: macro = qs.get_macro_metrics()
                except: macro = {'status': 'RISK_ON'}
                
                # Fetch News (for n_score) - Simplified
                n_score = 0
                try: 
                    na = news_analysis.NewsAnalyzer(ticker)
                    n_res = na.get_news_sentiment()
                    n_score = n_res.get('score', 0)
                except: pass

                alpha_new = qs.calculate_antigravity_score(
                    win_rate=wr_val,
                    profit_factor=pf_val,
                    ai_return=((setup.get('Target Price', 0) - curr_price)/curr_price)*100,
                    whale_score=whale_data.get('whale_score', 0),
                    sector_data=sector_data,
                    macro_status=macro['status']
                )
                
                # --- Phase 24: Risk Analysis (Shorts & News Fade) ---
                # Check for advanced risks
                # We need news score for "News Fade" check. 
                # Re-use n_score if available or 0.
                risk_data = qs.check_risk_factors(news_score=n_score)
                
                if risk_data['risk_score'] > 0:
                    st.error(f"⚠️ 위험 신호 감지 (Risk Score: {risk_data['risk_score']})")
                    for f in risk_data['factors']:
                        st.write(f"- {f}")
                    st.caption("※ 공매도 과열, 재료 소진, 기술적 과열 등을 분석한 결과입니다.")
                    st.divider()
                else:
                    # Clean
                    pass
                
                # --- Action Plan (Trade Setup) ---
                st.markdown(f"### ⚡ Action Plan (AI Antigrav: {alpha_new}점) - 1~2 Day Swing Strategy")
                
                entry_min = setup.get('Entry Min', setup.get('Entry Price', 0))
                entry_max = setup.get('Entry Max', entry_min)
                
                target_price = setup.get('Target Price', 0)
                stop_loss = setup.get('Stop Loss', 0)
                curr_price = latest['Close']
                
                # Calc Potentials based on Entry Price, not Current Price (since it's a limit order)
                upside_from_entry = ((target_price - entry_min) / entry_min) * 100 if entry_min > 0 else 0
                downside_from_entry = ((entry_min - stop_loss) / entry_min) * 100 if entry_min > 0 else 0
                risk_reward = upside_from_entry / downside_from_entry if downside_from_entry > 0 else 0
                
                c1, c2, c3, c4 = st.columns(4)
                
                currency = "₩" if ".KS" in ticker or ".KQ" in ticker else "$"
                
                # Format string
                if entry_max > entry_min * 1.001:
                    entry_str = f"{currency}{entry_min:,.0f}~{entry_max:,.0f}"
                else:
                    entry_str = f"{currency}{entry_min:,.0f}"

                entry_price = entry_min # For calcs
                
                c1.metric("진입권장 (-2% Limit Buy)", entry_str, help="현재가 대비 -2% 부근. 지정가 매수를 권장합니다.")
                c2.metric("목표가 (Target)", f"{currency}{target_price:,.0f}", f"+{upside_from_entry:.2f}% (진입가 대비)", delta_color="normal")
                c3.metric("손절가 (Stop Loss)", f"{currency}{stop_loss:,.0f}", f"-{downside_from_entry:.2f}% (진입가 대비)", delta_color="inverse")
                c4.metric("손익비 (R/R Ratio)", f"{risk_reward:.2f}", delta_color="normal" if risk_reward > 1.0 else "off", help="단타 스윙 시 1.0 이상 권장")
                
                st.caption(f"💡 시장가 추격 매수보다 **진입권장가({entry_str}) 부근에 지정가(Limit Order) 매수**를 걸어두어 승률을 높이세요.")
                st.divider()

                # --- AI Forecast Graph ---
                st.markdown("### 🤖 AI 주가 예측 (Hybrid Neural Prophet)")
                
                # Market Regime Check
                regime_info = qs.get_advanced_regime()
                r_status = regime_info['status']
                is_safe = r_status in ['BULL', 'BOX', 'NEUTRAL']
                
                regime_color = "green" if is_safe else "red"
                st.markdown(f"**시장 상황 (Market Regime)**: :{regime_color}[{r_status}] ({regime_info['reason']})")
                
                # --- Phase 13: Predictive Analytics (Deep Dive 2.0) ---
                st.divider()
                st.markdown("### 🔮 Predictive Analytics (과거/미래 분석)")
                
                col_h1, col_h2 = st.columns([2, 1])
                
                # 1. Peer Rank (Market Comparison)
                try:
                    m_type = "KR" if ".KS" in ticker or ".KQ" in ticker else "US"
                    db = db_manager.DBManager()
                    market_stats = db.get_market_stats(m_type)
                    history = db.get_ticker_history(ticker)
                    
                    if market_stats:
                        avg_alpha = market_stats.get('avg_alpha', 50)
                        my_alpha = latest.get('Antigravity Score', 50) # Need to ensure Antigrav is in latest, or calc it
                        # Recalc Antigrav for display consistency
                        # (qs.calculate_alpha_score might not store in df directly, let's recalculate or use DB history last point)
                        
                        # Get live calc alpha
                        ml_pred = qs.get_ml_prediction()
                        whale_data = qs.get_investor_flows()
                        # Assuming 'stats' from backtest has WR/PF
                        wr_disp = float(stats.get("Win Rate", "0").strip('%'))
                        pf_disp = float(stats.get("Profit Factor", "0"))
                        curr_alpha = qs.calculate_antigravity_score(wr_disp/100, pf_disp, 0, whale_score=whale_data.get('whale_score', 0), macro_status=r_status)
                        
                        delta = curr_alpha - avg_alpha
                        rank_msg = "상위권 🏆" if delta > 10 else "평균 이하 📉" if delta < -10 else "평균적 😐"
                        
                        with col_h2:
                            st.metric(f"{m_type} 시장 평균 점수", f"{avg_alpha:.1f}점")
                            st.metric("나의 Antigrav 점수", f"{curr_alpha}점", f"{delta:.1f} ({rank_msg})")

                    # 2. Antigrav Trend Chart
                    if history:
                        df_hist = pd.DataFrame(history)
                        # Parse date
                        df_hist['date'] = pd.to_datetime(df_hist['created_at']).dt.strftime('%m-%d %H:%M')
                        df_hist = df_hist.set_index('date')
                        
                        with col_h1:
                            st.markdown("**📉 Antigravity Score Trend (최근 30회)**")
                            st.line_chart(df_hist[['alpha_score', 'whale_score']])
                    else:
                        with col_h1:
                            st.info("데이터가 충분하지 않아 추세 차트를 그릴 수 없습니다. (스캔 기록 필요)")

                except Exception as e:
                    st.error(f"Analytics Error: {e}")

                # --- Detailed Plots ---

                if r_status == "CRASH":
                    st.error("🚨 시장 붕괴 경보! 모든 매수를 중단하고 현금을 확보하세요.")
                elif not is_safe:
                    st.warning("⚠️ 시장이 하락세입니다. 보수적으로 접근하세요.")
                
                # --- Phase 3: Macro Analysis (Risk Gating) ---
                with st.expander("📊 거시 경제 및 시장 국면 (Macro Logic)"):
                    try:
                        macro_data = qs.get_macro_metrics() 
                        m_status = macro_data['status']
                        m_vix = macro_data.get('vix', 0)
                        m_krw = macro_data.get('usd_krw', 0)
                        
                        mc1, mc2, mc3 = st.columns(3)
                        
                        mc1.metric("공포 지수 (VIX)", f"{m_vix:.2f}", delta_color="inverse" if m_vix < 20 else "normal", help="25 이상이면 위험")
                        mc2.metric("원/달러 환율", f"{m_krw:.2f}원", delta_color="inverse" if m_krw < 1350 else "normal", help="1420원 이상이면 위험")
                        
                        if m_status == 'RISK_OFF':
                            mc3.error("🌪️ RISK OFF (보수적 운용)")
                            st.error("🚨 시장 위험 감지: VIX 또는 환율이 임계치를 초과했습니다. AI 예측 범위가 넓어지고, 매수 점수가 하향 조정(Max 75)됩니다.")
                        else:
                            mc3.success("☀️ RISK ON (적극적 운용)")
                            st.info("시장 상황이 안정적입니다. 정상적인 AI 예측 및 스코어링이 적용됩니다.")
                        
                        # Store for later
                        st.session_state['last_macro_data'] = macro_data
                        
                    except:
                        st.warning("거시 경제 데이터를 불러오지 못했습니다.")
                        macro_data = {'status': 'RISK_ON'}

                # --- 0. Deep Insight Header (News & Patterns - Moved ONLY Logic, Display later) ---
                # We need sentiment score for AI Prediction
                n_score = 0
                news_res = {}
                with st.spinner("Analyzing News & Sentiment..."):
                     try:
                         news_analyzer = news_analysis.NewsAnalyzer(ticker, stock_name=stock_name)
                         news_res = news_analyzer.get_news_sentiment()
                         n_score = news_res.get('score', 0)
                     except Exception as ne:
                         st.error(f"News Analysis Error: {ne}")
                         import traceback
                         traceback.print_exc()

                # --- 1. Performance Metrics (Update with new AI Forecast call) ---
                # We need AI forecast result first for Antigravity Score
                # Phase 1: Pass Sentiment Score to Prophet
                # Phase 3: Pass Macro Status to Prophet (Widen intervals if Risk-Off)
                ai_result = None
                try:
                    ai_result = qs.predict_future(days=30, sentiment_score=n_score, macro_status=macro_data['status'])
                except Exception as e:
                    st.session_state['ai_error'] = f"Prophet 실행 오류: {str(e)}"
                    import traceback
                    traceback.print_exc()
                
                prophet_ret = 0
                mape_score = 0
                forecast_df = None
                
                if ai_result is not None and 'error' not in ai_result:
                     forecast_df = ai_result['forecast']
                     mape_score = ai_result['mape']
                     
                     curr = qs.df['Close'].iloc[-1]
                     pred = forecast_df['yhat'].iloc[-1]
                     prophet_ret = ((pred - curr)/curr)*100
                elif ai_result and 'error' in ai_result:
                     st.session_state['ai_error'] = ai_result['error']

                # --- 1.5 Supply/Demand Analysis (Phase 2) ---
                whale_data = qs.get_investor_flows()
                whale_score = whale_data.get('whale_score', 0)

                # --- 1.6 Relative Strength (Phase 4) ---
                rs_data = qs.get_relative_strength()
                rs_score = rs_data.get('score', 0)

                # Calculate Pro Antigravity Score (Pass Prophet Return & Whale Score & RS Score & Macro Status)
                val_wr = float(stats.get("Win Rate", "0").strip('%')) / 100.0
                val_pf = float(stats.get("Profit Factor", "0"))
                
                # Updated Call with Whale Score AND Macro Status AND RS Score
                alpha_score = qs.calculate_antigravity_score(val_wr, val_pf, prophet_ret, whale_score=whale_score, macro_status=macro_data['status'])
                
                # Calc Volume Surge (Needed for DB & Display)
                vol_now = qs.df['Volume'].iloc[-1]
                vol_avg = qs.df['Volume'].rolling(20).mean().iloc[-1]
                is_surge = vol_now > (vol_avg * 1.5)

                # --- LOGGING TO DB (Manual Scan) ---
                db_status = st.empty()
                db_status.info("💾 데이터베이스 연결 중...")
                
                try:
                    db = db_manager.DBManager()
                    if not db.client:
                        raise Exception("Supabase 클라이언트 초기화 실패.")
                        
                    # Use cached macro context if available, else fetch
                    macro_ctx = st.session_state.get('last_macro_ctx') or qs.get_macro_context()
                    
                    # 1. Save Features
                    feature_data = {
                        "ticker": ticker,
                        "price": latest['Close'],
                        "rsi": latest['RSI'],
                        "vol_surge": bool(is_surge),
                        "ma_weekly_trend": "UP" if latest.get('Weekly_Trend', 0)==1 else "DOWN",
                        "market_index_value": macro_ctx['market_index_value'],
                        "forex_rate": macro_ctx['forex_rate'],
                        "market_regime": "Safe" if is_safe else "Danger",
                        "ai_prediction_30d": prophet_ret,
                        "ai_mape_score": mape_score,
                        "alpha_score": alpha_score,
                        "future_return_3d": None
                    }
                    db.save_market_features(feature_data)
                    
                    # 2. Save Signal (including Trade Setup details)
                    signal_type = "BUY" if alpha_score >= 70 else "DETECTED"
                    db.save_signal(
                        ticker=ticker,
                        stock_name=stock_name, # Use fetched name
                        price=latest['Close'],
                        alpha_score=alpha_score,
                        ai_prediction=prophet_ret,
                        signal_type=signal_type,
                        entry_price=setup.get('Entry Price'),
                        target_price=setup.get('Target Price'),
                        stop_loss=setup.get('Stop Loss')
                    )
                    
                    db_status.success(f"✅ **DB 저장 완료**: {ticker} | 진입가: {setup.get('Entry Price'):.2f} | AI점수: {alpha_score:.0f}")
                    
                except Exception as e:
                    import traceback
                    err_msg = traceback.format_exc()
                    db_status.error(f"❌ DB 저장 실패: {e}")
                    st.expander("에러 상세 내용").code(err_msg)
                    print(f"DB Logging Error: {e}")
                
                # --- 0. Deep Insight Header (News & Patterns) ---
                st.markdown("### 🧠 Deep Insight & Sentiment (심층 분석)")
                d1, d2 = st.columns(2)
                
                # A. News Sentiment (Display Only - Calc done above)
                with d1:
                    st.markdown("**📰 AI News Sentiment**")
                    n_status = "Positive" if n_score > 0.2 else "Negative" if n_score < -0.2 else "Neutral"
                    n_color = "green" if n_score > 0.2 else "red" if n_score < -0.2 else "gray"
                     
                    st.markdown(f"<h3 style='color:{n_color}'>{n_status} ({n_score:.2f})</h3>", unsafe_allow_html=True)
                    if n_score == 0:
                         st.caption(f"ℹ️ 점수가 0.00입니다. ({news_res.get('status', 'Unknown')})")
                         with st.expander("🔍 News Debug Info"):
                             st.write(f"Ticker: {ticker}")
                             st.write(f"News Res: {news_res}")
                    if news_res.get('headlines'):
                         with st.expander("Recent Headlines"):
                             for h in news_res['headlines']:
                                 st.caption(f"{'🟢' if h['score']>0 else '🔴'} {h['title']}")

                # B. Pattern Recognition
                with d2:
                    st.markdown("**🕯️ Candlestick Patterns**")
                    patterns = qs.get_pattern_recognition()
                    if patterns:
                        for p in patterns:
                            p_color = "red" if "Bearish" in p or "Dark" in p else "green" 
                            st.markdown(f"- <span style='color:{p_color}; font-weight:bold'>{p}</span>", unsafe_allow_html=True)
                    else:
                        st.info("No specific candlestick patterns detected.")

                st.divider()

                # --- NEW: Phase 2 Supply/Demand (Whale) Analysis ---
                st.markdown(f"### 🐋 메이저 수급 분석 (Whale Score: {whale_score}점)")
                
                if whale_data.get('valid'):
                    w1, w2, w3 = st.columns(3)
                    
                    if whale_data.get('type') == 'KR':
                        # KR Logic (Flow)
                        f_val = whale_data['foreigner'] / 100000000
                        i_val = whale_data['institution'] / 100000000
                        r_val = whale_data['retail'] / 100000000
                        
                        w1.metric("Foreigner (외인)", f"{f_val:.1f}억", delta_color="normal" if f_val > 0 else "inverse")
                        w2.metric("Institution (기관)", f"{i_val:.1f}억", delta_color="normal" if i_val > 0 else "inverse")
                        w3.metric("Retail (개인)", f"{r_val:.1f}억", delta_color="inverse" if r_val > 0 else "normal", help="개인이 많이 사면 보통 좋지 않습니다.")
                        st.caption("※ 최근 10일 누적 순매수 금액 (단위: 억 원)")
                        
                    elif whale_data.get('type') == 'US':
                        # US Logic (Ownership)
                        inst_own = whale_data.get('institution_own', 0)
                        insider_own = whale_data.get('insider_own', 0)
                        
                        w1.metric("Institutional Hold", f"{inst_own}%", help="기관 보유 비중 (높을수록 좋음)")
                        w2.metric("Insider Hold", f"{insider_own}%", help="내부자 보유 비중")
                        w3.metric("Retail/Public", f"{100 - inst_own - insider_own:.1f}%", help="나머지 유통 물량")
                        st.caption("※ 기관/내부자 보유 비중 (Source: Yahoo Finance)")

                    if whale_score >= 70:
                        dominant = whale_data.get('dominant', '기관/외인')
                        st.success(f"🔥 **{dominant} 주도!** 메이저 세력의 순매수가 우세합니다.")
                    elif whale_score <= 30:
                        dominant = whale_data.get('dominant', '개인')
                        st.error(f"🐜 **{dominant} 위주!** 메이저 세력이 빠지고 있습니다. 주의하세요.")
                else:
                    reason = whale_data.get('reason', '데이터를 불러올 수 없습니다.')
                    st.warning(f"⚠️ **수급 데이터 조회 실패 (Whale Data Error)**")
                    st.caption(f"원인: {reason}")
                    if "PyKrx" in reason:
                         st.info("팁: 한국 주식은 `pykrx` 라이브러리가 필요합니다. 티커가 정확한지 확인해주세요.")
                
                st.divider()

                # --- NEW: Phase 4 Relative Strength (RS) Analysis ---
                st.markdown(f"### 🚀 주도주 분석 (RS Score: {rs_score}점)")
                rs_c1, rs_c2 = st.columns(2)
                
                ratio = rs_data.get('rs_ratio', 1.0)
                is_leader = rs_data.get('is_leader', False)
                rs_icon = "🔥 주도주 (Leader)" if is_leader else "🐢 소외주 (Laggard)" if ratio < 1.0 else "😐 시장 수익률 (Market Perform)"
                rs_color = "green" if is_leader else "red" if ratio < 1.0 else "gray"
                
                rs_c1.metric("RS Ratio (vs Market)", f"{ratio}x", delta="Outperforming" if ratio > 1 else "Underperforming")
                rs_c2.markdown(f"**Status**:<br><span style='color:{rs_color}; font-size:1.2em; font-weight:bold'>{rs_icon}</span>", unsafe_allow_html=True)
                
                st.divider()

                # --- NEW: Fundamental Guardrails Section ---
                st.markdown("### 🛡️ Fundamental Quality Guard (가치 투자 필터)")
                f_col1, f_col2, f_col3 = st.columns(3)
                
                # Get Fundamentals
                try:
                    t_info = quant_analysis.yf.Ticker(ticker).info
                    rev_g = t_info.get('revenueGrowth', 0)
                    roe = t_info.get('returnOnEquity', 0)
                    fund_passed, fund_reason = qs.check_fundamentals()
                    
                    f_col1.metric("Revenue Growth (YoY)", f"{rev_g:.1%}", delta_color="normal" if rev_g > 0 else "inverse")
                    f_col2.metric("ROE (Return on Equity)", f"{roe:.1%}", delta_color="normal" if roe > 0 else "inverse")
                    
                    status_color = "green" if fund_passed else "red"
                    status_icon = "✅ PASS" if fund_passed else "❌ FAIL"
                    f_col3.markdown(f"**Quality Status**:<br><span style='color:{status_color}; font-size:1.2em; font-weight:bold'>{status_icon}</span>", unsafe_allow_html=True)
                    
                    if not fund_passed:
                        st.error(f"⚠️ **경고**: {fund_reason}. 펀더멘털이 좋지 않습니다. 기술적 신호가 있어도 비중을 줄이세요.")
                except:
                    st.info("펀더멘털 데이터를 불러올 수 없습니다.")

                st.divider()

                st.divider()
                
                # --- NEW: Phase 5 Key Levels (Technical Confluence) ---
                st.markdown("### 📐 Key Technical Levels (지지/저항 라인)")
                
                # Fetch Data
                fibs = qs.get_fibonacci_levels()
                pivots = qs.get_pivot_points()
                
                k1, k2 = st.columns(2)
                
                # Column 1: Fibonacci
                with k1:
                    st.markdown("**1. Fibonacci Retracement (Swing)**")
                    if fibs:
                        st.text(f"  0.0% (Low) : {fibs.get('0.0',0):,.0f}")
                        st.text(f" 38.2%       : {fibs.get('0.382',0):,.0f} (1차 지지)")
                        st.text(f" 50.0%       : {fibs.get('0.5',0):,.0f} (중심값)")
                        st.text(f" 61.8%       : {fibs.get('0.618',0):,.0f} (Golden Pocket)")
                        st.text(f"100.0% (High): {fibs.get('1.0',0):,.0f}")
                    else:
                        st.info("데이터 부족으로 계산 불가")
                        
                # Column 2: Pivot Points
                with k2:
                    st.markdown("**2. Pivot Points (Floor Trader)**")
                    if pivots:
                        st.text(f" Resistance 2 : {pivots.get('R2',0):,.0f}")
                        st.text(f" Resistance 1 : {pivots.get('R1',0):,.0f}")
                        st.text(f" Pivot Point  : {pivots.get('P',0):,.0f} (기준)")
                        st.text(f" Support 1    : {pivots.get('S1',0):,.0f}")
                        st.text(f" Support 2    : {pivots.get('S2',0):,.0f}")
                    else:
                        st.info("데이터 부족으로 계산 불가")
                
                # Confluence Badge
                conf_score = setup.get('Confluence Score', 0)
                if conf_score >= 2:
                    st.success(f"🎯 **Sniper Entry 발견!** {conf_score}개의 주요 지지선이 겹치는 강력한 타점입니다.")
                
                st.divider()

                # --- NEW: Phase 6 AI Brain Center (ML) ---
                st.markdown("### 🧠 AI Brain Center (머신러닝 분석)")
                
                # Inference
                ml_pred = qs.get_ml_prediction() or {}
                prob_3 = ml_pred.get('3pct', 0.0)
                prob_5 = ml_pred.get('5pct', 0.0)
                prob_10 = ml_pred.get('10pct', 0.0)
                
                b1, b2, b3 = st.columns(3)
                
                # Probability Metrics
                b1.metric("P(+3%) Bounce Prob", f"{prob_3:.1f}%")
                b2.metric("P(+5%) Swing Prob", f"{prob_5:.1f}%")
                b3.metric("P(+10%) Surge Prob", f"{prob_10:.1f}%")
                
                # 3. Macro Context
                macro = quant_analysis.QuantStrategy._fetch_global_macro_data()
                if macro is not None and not macro.empty:
                    vix_now = macro['^VIX'].iloc[-1] if '^VIX' in macro.columns else 0
                    b3.metric("Macro Context (VIX)", f"{vix_now:.2f}", "시장 공포지수", delta_color="inverse")
                else:
                    b3.info("Macro Data Unavailable")

                st.divider()

                # --- NEW: Phase 8 Grand Synergy Report ---
                synergy_report = qs.generate_synergy_report()
                st.info(synergy_report)
                
                st.divider()

                st.subheader(f"1. AI 알파 스코어 & 성과 분석")
                
                m1, m2, m3, m4 = st.columns(4)
                
                # Restore Missing Metrics
                m1.metric("Pro Antigravity Score", f"{alpha_score:.0f}/100", help="기술적 + AI + 백테스트 종합 점수")
                m2.metric("Backtest Win Rate", stats.get("Win Rate", "N/A"), help="과거 시뮬레이션 승률")
                m3.metric("Profit Factor", stats.get("Profit Factor", "N/A"), help="손익비 (Profit Factor)")
                
                is_surge = vol_now > (vol_avg * 1.5)
                m4.metric("Volume Surge", "🔥 YES" if is_surge else "Noise", help="거래량 폭발 여부 (>평균 1.5배)")
                
                # --- 2. Actionable Setup (Same as before) ---
                st.subheader("2. Actionable Trade Setup")
                if setup:
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Entry Price", f"${setup.get('Entry Price',0):.2f}", help="진입가")
                    c2.metric("Stop Loss", f"${setup.get('Stop Loss',0):.2f}", delta="-2.0 ATR", delta_color="inverse", help="손절가")
                    c3.metric("Target Price", f"${setup.get('Target Price',0):.2f}", delta="+4.0 ATR", help="목표가")
                    c4.metric("Risk:Reward", setup.get("Risk/Reward"), help="손익비")

                # --- 3. Charts (Equity + Prophet) ---
                st.subheader("3. Equity Curve & AI Forecast")
                
                # Equity Curve
                if "Equity Curve" in stats:
                    st.caption("Strategy Equity Growth")
                    # st.line_chart(stats["Equity Curve"]) -> Simple
                    # Upgrade to Plotly for consistency
                    eq_fig = go.Figure()
                    eq_curve = stats["Equity Curve"]
                    # Fix: inputs are list, not Series
                    # eq_curve is a list of floats
                    x_values = list(range(len(eq_curve)))
                    eq_fig.add_trace(go.Scatter(x=x_values, y=eq_curve, mode='lines', name='Equity', line=dict(color='#00CCFF')))
                    eq_fig.update_layout(template="plotly_dark", height=300, margin=dict(t=10, b=10, l=10, r=10), hovermode="x unified")
                    st.plotly_chart(eq_fig, width='stretch')
                
                # Prophet/Hybrid Forecast
                if forecast_df is not None:
                    # Check Hybrid Status
                    is_tuned = ai_result.get('is_tuned', False)
                    model_type = "🧬 Hybrid Ensemble (Prophet + XGBoost)" if is_tuned else "🤖 Standard Prophet (Trend Only)"
                    
                # Prophet/Hybrid Forecast
                if forecast_df is not None:
                    # Check Hybrid Status
                    is_tuned = ai_result.get('is_tuned', False)
                    sniper_status = ai_result.get('sniper_status', 'READY') # Default READY for backward compat
                    
                    model_type = "🧬 Hybrid Ensemble + Conformal Prediction"
                    tuning_mode = ai_result.get('tuning_mode', 'Standard')
                    st.write(f"**📈 {model_type}** <span style='background-color:#262730; padding:4px 8px; border-radius:4px; font-size:0.8em'>⚙️ Mode: {tuning_mode}</span>", unsafe_allow_html=True)
                    
                    # Sniper Mode Logic
                    if sniper_status == 'HAZY':
                         st.warning("☁️ **관망 권장 (Hazy Market)**: 시장 변동성이 커서 95% 신뢰 구간이 넓습니다. (Conformal Interval > 10%)")
                    elif sniper_status == 'INACCURATE':
                         st.error(f"⚠️ **신뢰도 낮음**: 예측 오차({mape_score:.1f}%)가 높습니다. 퀀트 지표를 우선하세요.")
                    else:
                        st.success("🎯 **Sniper Locked**: 기술적 보정 완료. 95% 신뢰 구간 내 예측입니다.")
                    
                    # --- Common Chart Logic (Shows for ALL statuses) ---
                    # Accuracy Badge
                    acc_color = "green" if mape_score < 10 else "orange" if mape_score < 20 else "red"
                    acc_text = "높음 (High)" if mape_score < 10 else "보통 (Medium)" if mape_score < 20 else "낮음 (Low)"
                    
                    val_mape = ai_result.get('validation_mape', 0)
                    val_msg = f" (Val Error: {val_mape:.1f}%)" if val_mape > 0 else ""
                    
                    st.caption(f"Predictability: :{acc_color}[{acc_text}] (MAPE: {mape_score:.1f}%){val_msg}")

                    # Main Chart
                    fig_ai = go.Figure()
                    
                    fc = forecast_df 
                    
                    # 1. History (Candlestick)
                    # Force TZ-naive for compatibility
                    df_viz = qs.df.copy()
                    if df_viz.index.tzinfo is not None:
                        df_viz.index = df_viz.index.tz_localize(None)
                        
                    hist_limit = df_viz.iloc[-120:]
                    fig_ai.add_trace(go.Candlestick(
                        x=hist_limit.index,
                        open=hist_limit['Open'], high=hist_limit['High'],
                        low=hist_limit['Low'], close=hist_limit['Close'],
                        name='History'
                    ))
                    
                    # 2. Confidence Zone (Conformal 95%)
                    # Ensure fc['ds'] is naive
                    if fc['ds'].dt.tz is not None:
                        fc['ds'] = fc['ds'].dt.tz_localize(None)
                        
                    last_hist_date = df_viz.index[-1]
                    # Show last 120 days of HISTORY + ALL FUTURE
                    # prediction start date = last_hist_date - 120 days
                    start_plot_date = last_hist_date - pd.Timedelta(days=120)
                    
                    viz_fc = fc[fc['ds'] > start_plot_date]
                    
                    if not viz_fc.empty:
                        # Color logic: Always nice Blue/Green, just darker if hazy
                        fill_col = 'rgba(0, 176, 246, 0.2)' # Blue-ish for confidence
                        
                        fig_ai.add_trace(go.Scatter(
                            x=pd.concat([viz_fc['ds'], viz_fc['ds'][::-1]]),
                            y=pd.concat([viz_fc['yhat_upper'], viz_fc['yhat_lower'][::-1]]),
                            fill='toself',
                            fillcolor=fill_col,
                            line=dict(color='rgba(255,255,255,0)'),
                            hoverinfo="skip",
                            name='Confidence Zone (95%)'
                        ))
                    
                    # 3. AI Prediction Line
                    # Always show vibrant Hybrid line
                    line_col = '#00FF00' if is_tuned else '#00B0F6' # Green if Hybrid, Blue if Prophet
                    line_dash = 'solid'
                    
                    fig_ai.add_trace(go.Scatter(x=viz_fc['ds'], y=viz_fc['yhat'], mode='lines', name='AI Prediction', line=dict(color=line_col, width=3, dash=line_dash)))
                    
                    # Current Price Line
                    fig_ai.add_vline(x=df_viz.index[-1], line_dash="dash", line_color="white")

                    # --- Action Plan Lines ---
                    if setup:
                        tp = setup.get('Target Price', 0)
                        if tp > 0: fig_ai.add_hline(y=tp, line_dash="dot", line_color="#00FF00", annotation_text="Target")
                        sl = setup.get('Stop Loss', 0)
                        if sl > 0: fig_ai.add_hline(y=sl, line_dash="dot", line_color="#FF0000", annotation_text="Stop Loss")
                        ep = setup.get('Entry Price', 0)
                        if ep > 0: fig_ai.add_hline(y=ep, line_dash="dot", line_color="gray", annotation_text="Entry")
                    
                    fig_ai.update_layout(template="plotly_dark", height=500, margin=dict(t=30, b=20, l=20, r=20), hovermode="x unified", xaxis_rangeslider_visible=False)
                    st.plotly_chart(fig_ai, width='stretch')
                    
                    # Result Metrics
                    curr = qs.df['Close'].iloc[-1]
                    pred = fc['yhat'].iloc[-1]
                    pct = ((pred - curr)/curr)*100
                    
                    target_label = "Sniper Target" if sniper_status == 'READY' else "AI Forecast (Low Conf)"
                    currency_sym = "₩" if ".KS" in ticker or ".KQ" in ticker.upper() else "$"
                    st.metric(f"{target_label} (30 Days)", f"{currency_sym}{pred:,.2f}", f"{pct:.2f}%")
                else:
                    err_detail = st.session_state.get('ai_error', '데이터 부족 또는 알 수 없는 에러')
                    st.error(f"📉 AI 예측 실패: {err_detail}")
                    st.info("💡 팁: 최근 데이터가 50개(봉) 이상인지 확인해주세요.")
                
                # --- NEW: Phase 19 The Oracle (Final Verdict) ---
                st.divider()
                st.markdown("### 🔮 The Oracle (최종 판결)")
                
                # Ensure metrics are available (Antigrav, RS, Macro are calc'd above)
                # alpha_score, macro_data['status'], rs_score are in scope
                verdict = qs.get_final_verdict(
                    qs.df['Close'].iloc[-1], 
                    ai_result, 
                    alpha_score, 
                    macro_data['status'], 
                    rs_score
                )
                
                v_col1, v_col2 = st.columns([1, 2])
                
                with v_col1:
                    conf_color = "red"
                    if verdict['confidence'] > 80: conf_color = "green"
                    elif verdict['confidence'] > 50: conf_color = "orange"
                    
                    st.metric("Oracle Confidence", f"{verdict['confidence']}/100", help="기술적+AI+거시경제 통합 점수")
                    st.caption(f"신뢰도: :{conf_color}[{verdict['decision']}]")
                    
                with v_col2:
                    v_color = verdict['color']
                    
                    # Custom HTML Box
                    st.markdown(f"""
                    <div style="border: 2px solid {v_color}; padding: 15px; border-radius: 12px; text-align: center; background-color: rgba(0,0,0,0.2);">
                        <h2 style="color: {v_color}; margin:0; font-size: 2em;">{verdict['decision']}</h2>
                        <p style="margin:5px 0 10px 0; font-weight: bold;">{verdict['reason']}</p>
                        <div style="border-top: 1px solid gray; margin: 10px 0;"></div>
                        <p style="font-size: 1.1em; margin:0;">⏳ 추천 보유 기간: <span style="color: #00B0F6; font-weight:bold">{verdict['holding_period']}</span></p>
                    </div>
                    """, unsafe_allow_html=True)
                
                if "STRONG BUY" in verdict['decision']:
                    st.balloons()
                
                st.divider()
                
                # --- 4. Recent Data ---
                with st.expander("Show Recent Signals Data"):
                     st.dataframe(qs.df.tail(20)[['Close', 'RSI', 'Signal']].style.format("{:.2f}"))


                     
            else:
                st.error(f"Could not load data for {ticker}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: SCAN ARCHIVE (아카이브)
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.header("📚 스캔 아카이브 — 복기 & 성과 확인")
    st.caption("날짜별 스캔 결과 복기. 실제 수익률과 비교해 전략을 점검합니다. 같은 날 같은 티커는 최신 스캔 기준으로 표시됩니다.")

    try:
        from modules.db_manager import DBManager as _DBM
        import yfinance as _yf

        _db6 = _DBM()

        if not _db6.client:
            st.warning("⚠️ Supabase 연결 없음.")
        else:
            with st.spinner("📡 DB에서 스캔 이력 로드 중..."):
                _archive_rows = []
                _batch_size = 1000
                _max_rows = 25000
                _offset = 0
                while _offset < _max_rows:
                    _res6 = (
                        _db6.client.table("market_scan_results")
                        .select("*")
                        .order("created_at", desc=True)
                        .range(_offset, _offset + _batch_size - 1)
                        .execute()
                    )
                    _batch = list(_res6.data or [])
                    if not _batch:
                        break
                    _archive_rows.extend(_batch)
                    if len(_batch) < _batch_size:
                        break
                    _offset += _batch_size
                _df6 = pd.DataFrame(_archive_rows)
            _contaminated_map = _load_contaminated_run_map()

            if _df6.empty:
                st.info("아직 저장된 스캔 결과가 없습니다. 스캐너를 1회 이상 돌리면 여기에 표시됩니다.")
            else:
                # Supabase appends +00:00 to the naive local datetime stored by db_manager.
                # Strip the fake UTC timezone and localize to true KST.
                _df6['created_at'] = pd.to_datetime(_df6['created_at']).dt.tz_localize(None)
                _df6['created_at_kst'] = _df6['created_at'].dt.tz_localize('Asia/Seoul')
                _df6['effective_trade_date'] = pd.to_datetime(_df6.get('base_trade_date'), errors='coerce').dt.date
                _df6['scan_date'] = _df6['effective_trade_date'].where(_df6['effective_trade_date'].notna(), _df6['created_at_kst'].dt.date)
                if 'run_id' in _df6.columns:
                    _df6['validation_excluded'] = _df6['run_id'].map(
                        lambda x: bool((_contaminated_map.get(str(x), {}) or {}).get('validation_excluded', False))
                    )
                    _df6['quality_flags'] = _df6['run_id'].map(
                        lambda x: ", ".join((_contaminated_map.get(str(x), {}) or {}).get('quality_flags', []))
                    )
                else:
                    _df6['validation_excluded'] = False
                    _df6['quality_flags'] = ""

                _available_dates = sorted(_df6['scan_date'].unique(), reverse=True)
                _today_kst = pd.Timestamp.today(tz='Asia/Seoul').date()
                _measurement_cols = [
                    "return_30m_pct", "return_1h_pct", "return_close_pct",
                    "return_1d_pct", "return_2d_pct", "return_3d_pct", "return_5d_pct", "return_7d_pct",
                ]
                _existing_measurement_cols = [c for c in _measurement_cols if c in _df6.columns]
                _perf_ready_dates = set()
                if _existing_measurement_cols:
                    _perf_ready_mask = _df6[_existing_measurement_cols].notna().any(axis=1)
                    _perf_ready_dates = set(_df6.loc[_perf_ready_mask, 'scan_date'].dropna().tolist())
                _default_date = _available_dates[0] if _available_dates else None
                for _candidate_date in _available_dates:
                    if _candidate_date in _perf_ready_dates:
                        _default_date = _candidate_date
                        break

                _col_date, _col_mkt = st.columns([2, 2])
                _selected_date = _col_date.selectbox(
                    "📅 날짜 선택",
                    _available_dates,
                    index=max(0, _available_dates.index(_default_date)) if _available_dates and _default_date in _available_dates else 0,
                    format_func=lambda d: f"{'🟢 오늘 ' if d == _today_kst else '📅 '}{d}"
                )
                _selected_mkt = _col_mkt.selectbox("🌏 시장 필터", ["전체", "KR", "US"], index=0)

                _day_df = _df6[_df6['scan_date'] == _selected_date].copy()
                if _selected_mkt != "전체":
                    _day_df = _day_df[_day_df['market_type'] == _selected_mkt]

                _col_bucket, _col_mode, _col_valid = st.columns(3)
                _bucket_options = ["전체", "picked", "watchlist", "exception_leader"]
                _selected_bucket = _col_bucket.selectbox("🏷️ 분류 필터", _bucket_options, index=0)
                _mode_options = ["전체", "SWING", "INTRADAY"]
                _selected_mode = _col_mode.selectbox("⏱️ 스캔모드 필터", _mode_options, index=0)
                _validation_options = ["전체", "정상", "검증제외"]
                _selected_valid = _col_valid.selectbox("🧪 검증 필터", _validation_options, index=0)
                if _selected_bucket != "전체" and "decision_bucket" in _day_df.columns:
                    _day_df = _day_df[_day_df["decision_bucket"] == _selected_bucket]
                if _selected_mode != "전체" and "scan_mode" in _day_df.columns:
                    _day_df = _day_df[_day_df["scan_mode"].fillna("SWING").str.upper() == _selected_mode]
                if _selected_valid == "정상":
                    _day_df = _day_df[_day_df["validation_excluded"] != True]
                elif _selected_valid == "검증제외":
                    _day_df = _day_df[_day_df["validation_excluded"] == True]

                # View-level dedup: keep only LATEST scan per ticker per day
                _enriched_cols = [
                    "decision", "decision_bucket", "outcome_status", "latest_return_pct",
                    "return_30m_pct", "return_1h_pct", "return_close_pct",
                    "return_1d_pct", "return_2d_pct", "return_3d_pct", "return_5d_pct",
                    "return_7d_pct",
                ]
                _day_df["_archive_enriched_score"] = 0
                for _col in _enriched_cols:
                    if _col in _day_df.columns:
                        _day_df["_archive_enriched_score"] += _day_df[_col].notna().astype(int)
                _day_df = (
                    _day_df
                    .sort_values(['_archive_enriched_score', 'created_at_kst'], ascending=[False, False])
                    .groupby('ticker', as_index=False)
                    .first()
                )
                _day_df = _day_df.drop(columns=['_archive_enriched_score'], errors='ignore')

                _last_scan_time = _df6[_df6['scan_date'] == _selected_date]['created_at_kst'].max()
                st.markdown(f"**{_selected_date} — {len(_day_df)}종목** | 🕐 마지막 스캔: `{_last_scan_time.strftime('%H:%M KST')}`")
                intraday_count = 0
                swing_count = 0
                if "scan_mode" in _day_df.columns:
                    intraday_count = int((_day_df["scan_mode"].fillna("SWING").str.upper() == "INTRADAY").sum())
                    swing_count = int((_day_df["scan_mode"].fillna("SWING").str.upper() != "INTRADAY").sum())
                c_mode1, c_mode2, c_mode3 = st.columns(3)
                c_mode1.metric("전체", len(_day_df))
                c_mode2.metric("장중", intraday_count)
                c_mode3.metric("스윙", swing_count)

                # Sort by Decision Score (true ML-based rank, not the bugged alpha+ml formula)
                _day_df = _day_df.sort_values('decision_score', ascending=False, na_position='last')

                _has_stored_returns = any(col in _day_df.columns and _day_df[col].notna().any() for col in _measurement_cols + ["latest_return_pct"])
                _measured_count = 0
                if _existing_measurement_cols:
                    _measured_count = int(_day_df[_existing_measurement_cols].notna().any(axis=1).sum())
                if _measured_count == 0:
                    st.info("이 날짜의 아카이브는 아직 1D/2D/3D/5D/7D 측정값이 없거나, 측정 horizon이 아직 지나지 않았습니다.")
                else:
                    st.caption(f"측정 완료 종목: {_measured_count} / {len(_day_df)}")
                _show_perf = st.checkbox("📈 외부 즉시 수익률 추적 (Max & Current ROI)", value=False)

                if (not _has_stored_returns) and _show_perf and _selected_date <= _today_kst:
                    _max_perf_map = {}
                    _curr_perf_map = {}
                    with st.spinner("📡 수익률 추적 중 (약 5~10초 소요)..."):
                        from concurrent.futures import ThreadPoolExecutor
                        import datetime as _datetime

                        def _fetch_perf(tkr):
                            try:
                                h = _yf.Ticker(tkr).history(start=_selected_date)
                                if len(h) >= 2:
                                    base_close = h['Close'].iloc[0]
                                    max_high   = h['High'].iloc[1:].max()
                                    curr_close = h['Close'].iloc[-1]
                                    max_roi  = round((max_high   - base_close) / base_close * 100, 2)
                                    curr_roi = round((curr_close - base_close) / base_close * 100, 2)
                                    return tkr, max_roi, curr_roi
                            except:
                                pass
                            return tkr, None, None

                        with ThreadPoolExecutor(max_workers=15) as executor:
                            for _tkr, _max_p, _curr_p in executor.map(_fetch_perf, _day_df['ticker'].tolist()):
                                if _max_p is not None:
                                    _max_perf_map[_tkr]  = _max_p
                                    _curr_perf_map[_tkr] = _curr_p

                    _day_df['최고 수익률(%)'] = _day_df['ticker'].map(_max_perf_map)
                    _day_df['현재 수익률(%)'] = _day_df['ticker'].map(_curr_perf_map)

                # ── 아카이브 핵심 컬럼 + 한글 rename + column_config 툴팁 ──
                _ARCHIVE_COLS = [
                    ('tier',                    '등급',       'T0=초강력 / T1=강력 / T2=관심 / T3=참고'),
                    ('ticker',                  '코드',       None),
                    ('stock_name',              '종목명',     None),
                    ('market_type',             '시장',       'KOSPI / KOSDAQ / NASDAQ / AMEX'),
                    ('scan_mode',               '모드',       'SWING=스윙(3~5일) / INTRADAY=장중(1일)'),
                    ('decision_score',          'Decision점수','Antigrav + AI확률 + 추세 + 수급 가중 합산 스코어'),
                    ('alpha_score',             'Antigrav',   '기술적 모멘텀·섹터 강도·AI기대수익 합산 동력 지수 (0~100). 70+이면 강세'),
                    ('ml_prob',                 'AI확률(%)',  'ML 모델이 예측한 5% 이상 달성 확률. 58% 이상이 진입 기준'),
                    ('whale_score',             '수급점수',   '기관·외국인 수급 강도 지수 (0~100). 60 이상이면 수급 유입 신호'),
                    ('trend',                   '추세',       'UP=상승 / SIDE=횡보 / DOWN=하락'),
                    ('position',                '포지션',     '가격 위치 (Peak=천장권 / Rising=상승중 / Resting=눌림목)'),
                    ('primary_theme',           '대표테마',   '스캔 시점의 주도 테마'),
                    ('outcome_status',          '성과상태',   '실현된 성과 (HIT=목표달성 / MISS=미달 / PENDING=미확인)'),
                    ('decision',                'Planner판정','플래너가 최종 매수 추천했는지 여부'),
                    ('expected_return_1d_pct',  '예상1D(%)',  '스캐너 예측 1일 기대수익률'),
                    ('expected_return_3d_pct',  '예상3D(%)',  '스캐너 예측 3일 기대수익률'),
                    ('return_1d_pct',           '1D실적(%)',  '스캔 다음날 실제 수익률'),
                    ('return_3d_pct',           '3D실적(%)',  '스캔 3일 후 실제 수익률'),
                    ('return_5d_pct',           '5D실적(%)',  '스캔 5일 후 실제 수익률'),
                    ('return_7d_pct',           '7D실적(%)',  '스캔 7일 후 실제 수익률'),
                    ('latest_return_pct',       '현재수익률(%)','가장 최근 측정된 실제 수익률'),
                    ('created_at_kst',          '스캔시각',   '스캔이 실행된 한국 시간'),
                ]
                if (not _has_stored_returns) and _show_perf and '최고 수익률(%)' in _day_df.columns:
                    _ARCHIVE_COLS += [
                        ('최고 수익률(%)', '최고수익(%)', '스캔 이후 최고점 수익률 (yfinance 조회)'),
                        ('현재 수익률(%)', '현재수익(%)', '현재 주가 기준 수익률 (yfinance 조회)'),
                    ]

                _arc_raw_cols = [c for c, _, _ in _ARCHIVE_COLS if c in _day_df.columns]
                _arc_rename   = {c: kr for c, kr, _ in _ARCHIVE_COLS}
                _arc_col_cfg  = {
                    kr: st.column_config.NumberColumn(kr, help=tip, format="%.2f")
                         if tip and any(kw in c for kw in ('pct', '수익')) else
                         st.column_config.TextColumn(kr, help=tip) if tip else None
                    for c, kr, tip in _ARCHIVE_COLS
                }
                _arc_col_cfg = {k: v for k, v in _arc_col_cfg.items() if v is not None}

                _show_df = _day_df[_arc_raw_cols].rename(columns=_arc_rename)

                # --- TOP 5 vs OTHERS SPLIT ---
                st.divider()
                st.markdown(f"### 🔥 Top 5 — {_selected_date}")
                _top5 = _show_df.head(5).copy()
                st.dataframe(_top5, column_config=_arc_col_cfg,
                             use_container_width=True, hide_index=True)

                st.divider()
                st.markdown("### 📋 기타 후보")
                if len(_show_df) > 5:
                    st.dataframe(_show_df.iloc[5:].copy(), column_config=_arc_col_cfg,
                                 use_container_width=True, hide_index=True)
                else:
                    st.info("Top 5 외에 추가 종목이 없습니다.")

                _perf_col = None
                if 'return_7d_pct' in _day_df.columns:
                    _perf_col = 'return_7d_pct'
                elif 'return_3d_pct' in _day_df.columns:
                    _perf_col = 'return_3d_pct'
                elif _show_perf and '오늘 등락(%)' in _day_df.columns:
                    _perf_col = '오늘 등락(%)'
                if _perf_col:
                    _valid = _day_df.dropna(subset=[_perf_col])
                    if not _valid.empty:
                        _avg = _valid[_perf_col].mean()
                        _winners = (_valid[_perf_col] > 0).sum()
                        c1, c2, c3 = st.columns(3)
                        c1.metric("평균 수익률", f"{_avg:+.2f}%", "수익" if _avg > 0 else "손실")
                        c2.metric("수익 종목 수", f"{_winners}/{len(_valid)}")
                        c3.metric("승률", f"{_winners/len(_valid)*100:.0f}%")

    except Exception as _e6:
        st.error(f"Scan Archive 오류: {_e6}")
        import traceback; st.code(traceback.format_exc())
