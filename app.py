import warnings
# Suppress Google Auth Python 3.9 Deprecation & urllib3 LibreSSL warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.auth")
warnings.filterwarnings("ignore", category=FutureWarning, module="google.oauth2")
warnings.filterwarnings("ignore", module="urllib3")

import html
import json
import math
import threading
import streamlit as st
import os
from pathlib import Path
from datetime import date
from dotenv import load_dotenv
load_dotenv()
load_dotenv(".env.local")

from modules import quant_analysis, db_manager, market_intelligence
from modules.live_scan_context import live_mode_enabled, normalize_market_key
from modules.macro_scheduler import get_macro_context
from modules.scanner_bridge import run_legacy_agent_bridge
from modules.scanner_runtime import SharedBackoffState, run_parallel_scan, scan_symbol_with_retry
from modules.scanner_services import evaluate_uploaded_candidate, normalize_uploaded_ticker
from modules.segment_accuracy import get_segment_accuracy_snapshot
from modules.scan_policy import (
    compute_market_gate as compute_market_gate_live,
    compute_rank_adjustment as shared_compute_rank_adjustment,
)
from modules.theme_data_pipeline import build_theme_distribution_summary
from modules.top_deep_report import generate_and_store_top_deep_reports
from modules.ui_helpers import (
    BackgroundScanState,
    build_signal_display_rows,
    build_watchlist_display_rows,
    compute_progress_fraction,
    enrich_signal_rows_with_planner_trace,
    format_volume_display,
    resolve_display_price,
    should_auto_refresh_scan_panel,
    split_stream_records,
    sort_signal_rows_by_planner_rank,
)
from ui.theme import inject_theme as _inject_design_tokens
from ui.components import compact_status_bar as _compact_status_bar
from ui.scan_cockpit import (
    render_scan_top_candidates as _render_scan_top_candidates,
    render_signal_card_list as _render_signal_card_list,
)
import pandas as pd
import plotly.graph_objects as go
import traceback

# [Phase 8] Global Backoff Synchronization for Rate Limits
_SCAN_BACKOFF_STATE = SharedBackoffState()
ENABLE_ADVANCED_UI = os.getenv("AG_UI_ADVANCED", "0").strip().lower() in {"1", "true", "yes", "on"}

st.set_page_config(
    page_title="스윙 트레이딩 AI",
    layout="wide",
    page_icon="📈",
    initial_sidebar_state="collapsed",
)

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


def _inject_toss_theme():
    """디자인 토큰/CSS 주입. 실제 구현은 ui.theme.inject_theme."""
    _inject_design_tokens()


def _render_section_intro(kicker, title, body, chips=None):
    chip_html = ""
    if chips:
        chip_html = '<div class="section-chip-row">' + "".join(
            f'<span class="section-chip">{html.escape(str(chip))}</span>'
            for chip in chips
            if str(chip).strip()
        ) + "</div>"
    st.markdown(
        f"""
        <section class="section-intro">
          <div class="section-kicker">{html.escape(str(kicker))}</div>
          <div class="section-title">{html.escape(str(title))}</div>
          <div class="section-body">{html.escape(str(body))}</div>
          {chip_html}
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_status_banner(title, body, tone="good", caption=None):
    caption_html = (
        f'<div class="status-caption" style="margin-top:0.45rem;">{html.escape(str(caption))}</div>'
        if caption
        else ""
    )
    st.markdown(
        f"""
        <section class="status-banner {html.escape(str(tone))}">
          <div class="status-title">{html.escape(str(title))}</div>
          <div class="status-body">{html.escape(str(body))}</div>
          {caption_html}
        </section>
        """,
        unsafe_allow_html=True,
    )


def _coerce_text_rows(value, *, limit=4):
    rows = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key or "").strip()
            item_text = str(item or "").strip()
            if key_text and item_text:
                rows.append(f"{key_text}: {item_text}")
            elif key_text:
                rows.append(key_text)
            elif item_text:
                rows.append(item_text)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                if item.get("label") and item.get("value"):
                    rows.append(f"{item.get('label')}: {item.get('value')}")
                    continue
                if item.get("title") and item.get("summary"):
                    rows.append(f"{item.get('title')}: {item.get('summary')}")
                    continue
                if item.get("signal") and item.get("value") is not None:
                    rows.append(f"{item.get('signal')}: {item.get('value')}")
                    continue
                if item.get("theme_name") and item.get("strength_score") is not None:
                    rows.append(f"{item.get('theme_name')} ({item.get('strength_score')})")
                    continue
                text = " · ".join(str(v).strip() for v in item.values() if str(v).strip())
                if text:
                    rows.append(text)
            else:
                text = str(item or "").strip()
                if text:
                    rows.append(text)
    else:
        text = str(value or "").strip()
        if text:
            rows.append(text)
    deduped = []
    for row in rows:
        if row not in deduped:
            deduped.append(row)
    return deduped[:limit]


def _theme_tone(direction):
    direction_key = str(direction or "NEUTRAL").upper()
    if direction_key == "BENEFICIARY":
        return "good", "수혜"
    if direction_key == "HEADWIND":
        return "risk", "역풍"
    return "neutral", "중립"


def _render_intelligence_highlights(highlights):
    if not highlights:
        return
    rows_html = []
    for label, text in highlights:
        label_text = html.escape(str(label or "").strip())
        body_text = html.escape(str(text or "").strip())
        if not body_text:
            continue
        rows_html.append(
            f"""
            <div class="intel-highlight-item">
              <span class="intel-highlight-badge">{label_text}</span>
              <div class="intel-highlight-text">{body_text}</div>
            </div>
            """
        )
    if rows_html:
        st.markdown('<div class="intel-highlight-list">' + "".join(rows_html) + "</div>", unsafe_allow_html=True)


def _render_theme_cards(theme_rows, *, empty_text, compact=False):
    rows = theme_rows or []
    if not rows:
        st.caption(empty_text)
        return
    limit = 3 if compact else 6
    for row in rows[:limit]:
        if not isinstance(row, dict):
            continue
        tone, badge = _theme_tone(row.get("direction"))
        strength = float(row.get("strength_score", 0.0) or 0.0)
        confidence = float(row.get("confidence", 0.0) or 0.0)
        momentum = str(row.get("momentum_class") or "").strip()
        evidence_rows = _coerce_text_rows(row.get("evidence"), limit=2 if compact else 3)
        evidence_text = " / ".join(evidence_rows) if evidence_rows else "아직 핵심 근거가 구조화되지 않았습니다."
        meta_parts = [
            f"강도 {strength:.1f}",
            f"신뢰 {int(round(confidence * 100))}%",
        ]
        if momentum:
            meta_parts.append(f"모멘텀 {momentum}")
        if row.get("momentum_avg_change_pct") is not None:
            try:
                meta_parts.append(f"평균변화 {float(row.get('momentum_avg_change_pct')):+.2f}%")
            except Exception:
                pass
        st.markdown(
            f"""
            <div class="intel-theme-card {tone}">
              <div class="intel-theme-head">
                <div class="intel-theme-name">{html.escape(str(row.get('theme_name') or '-'))}</div>
                <div class="intel-theme-badge {tone}">{html.escape(badge)}</div>
              </div>
              <div class="intel-theme-meta">{html.escape(' · '.join(meta_parts))}</div>
              <div class="intel-theme-evidence"><strong>핵심 근거</strong>{html.escape(evidence_text)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _build_intelligence_highlights(intel_data):
    highlights = []
    key_insight = str(intel_data.get("key_insight") or "").strip()
    if key_insight:
        highlights.append(("핵심", key_insight))
    beneficiary = intel_data.get("beneficiary_themes") or []
    headwind = intel_data.get("headwind_themes") or []
    if beneficiary:
        top_names = ", ".join(
            str(row.get("theme_name") or "").strip()
            for row in beneficiary[:3]
            if str(row.get("theme_name") or "").strip()
        )
        if top_names:
            highlights.append(("수혜", f"강하게 받쳐주는 테마는 {top_names} 입니다."))
    if headwind:
        top_names = ", ".join(
            str(row.get("theme_name") or "").strip()
            for row in headwind[:3]
            if str(row.get("theme_name") or "").strip()
        )
        if top_names:
            highlights.append(("역풍", f"부담 요인으로 보이는 테마는 {top_names} 입니다."))
    else:
        highlights.append(("역풍", "뚜렷한 역풍 테마는 아직 크게 보이지 않습니다."))
    risk_rows = _coerce_text_rows(intel_data.get("risk_flags"), limit=2)
    if risk_rows:
        highlights.append(("리스크", " / ".join(risk_rows)))
    macro_rows = _coerce_text_rows(intel_data.get("macro_drivers"), limit=2)
    if macro_rows:
        highlights.append(("매크로", " / ".join(macro_rows)))
    return highlights[:5]


def _theme_name_line(rows, limit=5):
    names = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("theme_name") or "").strip()
        if name and name not in names:
            names.append(name)
    return ", ".join(names[:limit])


def _intelligence_driver_line(intel_data, *, positive=True, limit=3):
    labels = []
    for row in intel_data.get("macro_drivers", []) or []:
        if not isinstance(row, dict):
            continue
        signal = str(row.get("signal") or "").upper()
        impact = float(row.get("market_impact", 0) or 0)
        if positive and signal in {"BULLISH", "MIXED"} and impact > 0:
            labels.append(str(row.get("category") or "").strip())
        elif (not positive) and signal in {"BEARISH", "MIXED"} and impact < 0:
            labels.append(str(row.get("category") or "").strip())
    deduped = []
    for label in labels:
        if label and label not in deduped:
            deduped.append(label)
    return ", ".join(deduped[:limit])


def _intelligence_signal_line(intel_data, *, kind="beneficiary", limit=4):
    if kind == "beneficiary":
        theme_line = _theme_name_line(intel_data.get("beneficiary_themes") or [], limit=limit)
        if theme_line:
            return theme_line
        sectors = [str(row).strip() for row in (intel_data.get("beneficiary_sectors") or []) if str(row).strip()]
        if sectors:
            return ", ".join(sectors[:limit])
        driver_line = _intelligence_driver_line(intel_data, positive=True, limit=limit)
        if driver_line:
            return driver_line
        return "수급/실적 버팀목 선별 구간"

    theme_line = _theme_name_line(intel_data.get("headwind_themes") or [], limit=limit)
    if theme_line:
        return theme_line
    sectors = [str(row).strip() for row in (intel_data.get("victim_sectors") or []) if str(row).strip()]
    if sectors:
        return ", ".join(sectors[:limit])
    risks = [str(row).strip() for row in (intel_data.get("risk_flags") or []) if str(row).strip()]
    if risks:
        return ", ".join(risks[:limit])
    driver_line = _intelligence_driver_line(intel_data, positive=False, limit=limit)
    if driver_line:
        return driver_line
    return "과열 추격보다는 리스크 점검 우선"


def _intelligence_tactical_line(intel_data):
    evidence = _coerce_text_rows(intel_data.get("macro_drivers"), limit=1)
    if evidence:
        return evidence[0]
    risk = _coerce_text_rows(intel_data.get("risk_flags"), limit=2)
    if risk:
        return f"핵심 경계 요인: {' / '.join(risk)}"
    disclosure = intel_data.get("disclosure_events") or []
    if disclosure and isinstance(disclosure[0], dict):
        first = disclosure[0]
        company = str(first.get("company") or "").strip()
        label = str(first.get("label") or "").strip()
        if company and label:
            return f"{company} {label} 이슈가 단기 심리에 반영되고 있습니다."
    return "시장 전반보다 선별 대응이 중요한 구간입니다."


def _build_next_session_theme_line(theme_summary, intel_data):
    candidates = []
    for row in (theme_summary.get("rows", []) if isinstance(theme_summary, dict) else []):
        if not isinstance(row, dict):
            continue
        avg_ret = row.get("avg_day_return_pct")
        strength = float(row.get("strength_score", 0.0) or 0.0)
        positive_ratio = float(row.get("positive_ratio", 0.0) or 0.0)
        score = (float(avg_ret) if avg_ret is not None else -9.0) + (strength * 0.03) + (positive_ratio * 1.2)
        candidates.append((score, str(row.get("theme_name") or "").strip()))
    if not candidates:
        return _theme_name_line(intel_data.get("beneficiary_themes") or [], limit=4) or "뚜렷한 선도 테마 없음"
    deduped = []
    for _, theme_name in sorted(candidates, reverse=True):
        if theme_name and theme_name not in deduped:
            deduped.append(theme_name)
    return ", ".join(deduped[:4]) if deduped else "뚜렷한 선도 테마 없음"


def _build_intelligence_catalysts(intel_data, theme_summary):
    rows = []
    top_theme_rows = (theme_summary.get("rows", []) if isinstance(theme_summary, dict) else [])[:3]
    for row in top_theme_rows:
        if not isinstance(row, dict):
            continue
        theme_name = str(row.get("theme_name") or "").strip()
        avg_ret = row.get("avg_day_return_pct")
        positive_ratio = row.get("positive_ratio")
        industry = ", ".join(row.get("industry_samples", [])[:2]) if isinstance(row.get("industry_samples"), list) else ""
        if theme_name and avg_ret is not None:
            line = f"{theme_name}: 평균 {float(avg_ret):+.2f}%"
            if positive_ratio is not None:
                line += f", 양봉 비중 {int(round(float(positive_ratio) * 100))}%"
            if industry:
                line += f", 대표 업종 {industry}"
            rows.append(line)
    for event in intel_data.get("disclosure_events", []) or []:
        if not isinstance(event, dict):
            continue
        company = str(event.get("company") or "").strip()
        label = str(event.get("label") or "").strip()
        report_name = str(event.get("report_name") or "").strip()
        if company and label:
            rows.append(f"{company}: {label} 이벤트 반영 ({report_name or '공시'})")
        if len(rows) >= 5:
            break
    for row in intel_data.get("macro_drivers", []) or []:
        if not isinstance(row, dict):
            continue
        desc = str(row.get("description") or "").strip()
        if desc and desc not in rows:
            rows.append(desc)
        if len(rows) >= 5:
            break
    deduped = []
    for row in rows:
        if row not in deduped:
            deduped.append(row)
    return deduped[:5]


def _render_intelligence_overview_dashboard(market, intel_data, theme_summary):
    if not isinstance(intel_data, dict) or not intel_data:
        return
    sentiment = str(intel_data.get("market_sentiment", "NEUTRAL") or "NEUTRAL").upper()
    sent_icon = {"BULLISH": "🟢", "BEARISH": "🔴", "MIXED": "🟡", "NEUTRAL": "⚪"}.get(sentiment, "⚪")
    sent_score = int(float(intel_data.get("sentiment_score", 0) or 0))
    key_insight = str(intel_data.get("key_insight") or "").strip() or "핵심 인사이트가 아직 구조화되지 않았습니다."
    beneficiary_line = _theme_name_line(intel_data.get("beneficiary_themes") or [], limit=6) or "뚜렷한 수혜 테마 없음"
    headwind_line = _theme_name_line(intel_data.get("headwind_themes") or [], limit=4) or "뚜렷한 피해 테마 없음"
    next_session_line = _build_next_session_theme_line(theme_summary, intel_data)
    source = str(intel_data.get("source", "unknown") or "unknown")
    headline_count = int(intel_data.get("headline_count", 0) or 0)

    st.markdown(
        '<div class="intel-overview-shell">'
        f'<div class="intel-scoreline">시장 분위기: {html.escape(sent_icon)} {html.escape(sentiment)} '
        f'<span class="muted">(점수: {sent_score:+d} · 헤드라인 {headline_count} · {html.escape(source)})</span></div>'
        f'<div class="intel-insight-box"><strong>핵심 인사이트:</strong> {html.escape(key_insight)}</div>'
        '<div class="intel-signal-grid">'
        f'<section class="intel-signal-card good"><div class="intel-signal-title">수혜 테마</div><div class="intel-signal-body">🔥 {html.escape(beneficiary_line)}</div><div class="intel-signal-meta">현재 시장에서 상대적으로 받쳐주는 테마 축입니다.</div></section>'
        f'<section class="intel-signal-card risk"><div class="intel-signal-title">피해 테마</div><div class="intel-signal-body">⚠️ {html.escape(headwind_line)}</div><div class="intel-signal-meta">리스크 관리 시 먼저 체크할 부담 구간입니다.</div></section>'
        f'<section class="intel-signal-card focus"><div class="intel-signal-title">내일 주도 예상</div><div class="intel-signal-body">🔮 {html.escape(next_session_line)}</div><div class="intel-signal-meta">LLM 테마 방향성과 당일 모멘텀 분포를 함께 반영했습니다.</div></section>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    momentum_rows = (theme_summary.get("rows", []) if isinstance(theme_summary, dict) else [])[:5]
    if momentum_rows:
        st.markdown("### 📊 테마 모멘텀 순위")
        cards = []
        for idx, row in enumerate(momentum_rows, start=1):
            theme_name = str(row.get("theme_name") or "-")
            avg_ret = row.get("avg_day_return_pct")
            positive_ratio = row.get("positive_ratio")
            direction = str(row.get("direction", "NEUTRAL") or "NEUTRAL").upper()
            direction_icon = "🔥" if direction == "BENEFICIARY" else ("⚠️" if direction == "HEADWIND" else "➡️")
            ret_class = "pos" if avg_ret is not None and float(avg_ret) > 0 else ("neg" if avg_ret is not None and float(avg_ret) < 0 else "neu")
            ret_text = f"{float(avg_ret):+.2f}%" if avg_ret is not None else "-"
            breadth_text = (
                f"↑ 양봉 {int(round(float(positive_ratio) * 100))}%"
                if positive_ratio is not None
                else "브레드스 없음"
            )
            meta_parts = [
                f"분류 {int(row.get('symbol_count', 0) or 0)}종목",
                f"강도 {float(row.get('strength_score', 0.0) or 0.0):.1f}",
            ]
            if row.get("return_coverage"):
                meta_parts.append(f"수익률커버 {int(row.get('return_coverage', 0))}")
            cards.append(
                f'<section class="intel-momentum-card"><div class="intel-momentum-rank">#{idx} {direction_icon}</div>'
                f'<div class="intel-momentum-theme">{html.escape(theme_name)}</div>'
                f'<div class="intel-momentum-return {ret_class}">{html.escape(ret_text)}</div>'
                f'<span class="intel-momentum-chip">{html.escape(breadth_text)}</span>'
                f'<div class="intel-momentum-meta">{html.escape(" · ".join(meta_parts))}</div></section>'
            )
        st.markdown('<div class="intel-momentum-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)

    catalysts = _build_intelligence_catalysts(intel_data, theme_summary)
    if catalysts:
        st.markdown("### 🔥 핵심 촉매")
        st.markdown(
            '<div class="intel-catalyst-list">' + "".join(
                f'<div class="intel-catalyst-item">{html.escape(str(row))}</div>' for row in catalysts
            ) + "</div>",
            unsafe_allow_html=True,
        )

    headline_rows = _coerce_text_rows(intel_data.get("evidence_headlines") or intel_data.get("raw_headlines"), limit=4)
    if headline_rows:
        st.markdown("### 📰 근거 헤드라인")
        st.markdown(
            '<div class="intel-headline-list">' + "".join(
                f'<div class="intel-headline-item">{html.escape(str(row))}</div>' for row in headline_rows
            ) + "</div>",
            unsafe_allow_html=True,
        )

def _render_main_controls():
    control_left, control_right = st.columns([1, 1])
    refresh_macro = control_left.button("🔄 매크로 새로고침", use_container_width=True)
    refresh_gate = control_right.button("🔄 마켓 게이트 새로고침", use_container_width=True)
    return refresh_macro, refresh_gate


def _render_daily_ops_overview():
    _render_section_intro(
        "Daily Pulse",
        "일일 성과 요약",
        "시장별 운영 상태와 수익률을 시장당 한 카드에 모아 빠르게 훑을 수 있게 정리했습니다. 전체 표는 아래 ‘성과측정 상세’ 에서 확인하세요.",
        ["KOSPI", "KOSDAQ", "NASDAQ", "AMEX"],
    )
    markets = ["KOSPI", "KOSDAQ", "NASDAQ", "AMEX"]
    cols = st.columns(len(markets))
    has_any = False
    for col, market in zip(cols, markets):
        payload = _load_latest_daily_summary(market)
        with col.container(border=True):
            st.markdown(f"#### {market}")
            if not payload:
                st.caption("요약 없음")
                continue
            has_any = True
            outcomes = payload.get("outcomes", {}) if isinstance(payload.get("outcomes"), dict) else {}
            buckets = payload.get("outcome_bucket_breakdown", {}) if isinstance(payload.get("outcome_bucket_breakdown"), dict) else {}
            return_buckets = payload.get("return_bucket_breakdown", {}) if isinstance(payload.get("return_bucket_breakdown"), dict) else {}
            picked = int((buckets.get("picked", {}) if isinstance(buckets.get("picked"), dict) else {}).get("total", 0) or 0)
            watchlist_bucket = int((buckets.get("watchlist", {}) if isinstance(buckets.get("watchlist"), dict) else {}).get("total", 0) or 0)
            exception_bucket = int(
                (buckets.get("exception_leader", {}) if isinstance(buckets.get("exception_leader"), dict) else {}).get("total", 0) or 0
            )
            picked_30m = _return_metric(return_buckets, "picked", "30m")
            picked_1h = _return_metric(return_buckets, "picked", "1h")
            picked_close = _return_metric(return_buckets, "picked", "close")
            picked_close_n = int(_return_metric(return_buckets, "picked", "close", field="samples"))
            picked_3d_win = _return_metric(return_buckets, "picked", "3d", field="win_rate_pct")
            pending = int(outcomes.get("pending", 0) or 0)
            resolved = int(outcomes.get("resolved", 0) or 0)

            # 헤드라인 — Runs / 3D 승률
            st.metric(
                "Runs",
                int(payload.get("total_runs", 0) or 0),
                delta=f"3D 승률 {picked_3d_win:+.0f}%" if picked_3d_win else None,
            )
            # 분류 / 진행 상태
            st.caption(
                f"Picked {picked} · Watch {watchlist_bucket} · Exception {exception_bucket}\n"
                f"Pending {pending} · Resolved {resolved}"
            )
            st.markdown(
                f"<div class='detail-grid-hint' style='margin-top:0.4rem;'>"
                f"30m <b>{picked_30m:+.2f}%</b> · 1H <b>{picked_1h:+.2f}%</b> · "
                f"종가 <b>{picked_close:+.2f}%</b>"
                f" <span style='color:var(--muted);'>(n={picked_close_n})</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
    if has_any:
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
        watchlist_rows, visible_numeric_fields = build_watchlist_display_rows(
            watchlist,
            watchlist_meta,
            decisions,
            scanner_payload=scanner_payload,
        )
        st.caption("Watchlist 표는 실제 planner/scanner 원천값만 표시합니다. 값이 없는 지표는 대체치로 채우지 않습니다.")
        _watchlist_df = _coerce_numeric_display(pd.DataFrame(watchlist_rows), visible_numeric_fields)
        ordered_columns = ["Rank", "Ticker", "Name", "Reason", "Reject"] + visible_numeric_fields
        ordered_columns = [col for col in ordered_columns if col in _watchlist_df.columns]
        if ordered_columns:
            _watchlist_df = _watchlist_df[ordered_columns]
        st.dataframe(_watchlist_df, width='stretch')
        if ENABLE_ADVANCED_UI:
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
            summary_rows = []
            strict_gate = watchlist_policy.get("strict_gate") if isinstance(watchlist_policy, dict) else None
            if strict_gate is not None:
                summary_rows.append(f"watchlist_only_policy.strict_gate={strict_gate}")
            near_miss_count = len(near_miss.get("tickers", []) or []) if isinstance(near_miss, dict) else 0
            if near_miss_count:
                summary_rows.append(f"near_miss_watchlist={near_miss_count}개")
            fallback_count = len(fallback_watchlist.get("tickers", []) or []) if isinstance(fallback_watchlist, dict) else 0
            if fallback_count:
                summary_rows.append(f"fallback_watchlist={fallback_count}개")
            exception_count = len(exception_leaders.get("watchlist_meta", []) or []) if isinstance(exception_leaders, dict) else 0
            if exception_count:
                summary_rows.append(f"exception_leaders={exception_count}개")
            if summary_rows:
                st.markdown("**Planner Summary**")
                for row in summary_rows:
                    st.caption(row)
        likely_causes = postmortem_payload.get("likely_causes", []) if isinstance(postmortem_payload.get("likely_causes"), list) else []
        if not likely_causes and isinstance(compact_postmortem.get("likely_causes"), list):
            likely_causes = compact_postmortem.get("likely_causes", [])
        if likely_causes:
            st.markdown("**Likely Causes**")
            for cause in likely_causes[:6]:
                st.write(f"- {cause}")


def _get_scan_state_snapshot():
    state = st.session_state.get("scan_job_state")
    if state is None:
        return None
    return state.snapshot()


def _load_top_deep_reports(limit=500):
    rows = []
    warning = ""
    try:
        db = db_manager.DBManager()
        if db.client:
            res = (
                db.client.table("scan_deep_reports")
                .select("*")
                .order("generated_at", desc=True)
                .limit(int(limit or 500))
                .execute()
            )
            rows = list(res.data or [])
    except Exception as exc:
        warning = str(exc)
    if rows:
        return rows, warning

    local_rows = []
    report_dir = Path("runtime_state/reports/top_deep")
    if report_dir.exists():
        for path in sorted(report_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:100]:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, list):
                    local_rows.extend([row for row in payload if isinstance(row, dict)])
            except Exception:
                continue
    return local_rows[: int(limit or 500)], warning


def _fmt_metric_pct(value):
    if value in (None, ""):
        return "-"
    try:
        return f"{float(value):+.2f}%"
    except Exception:
        return "-"


def _fmt_metric_num(value, digits=1):
    if value in (None, ""):
        return "-"
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "-"


def _render_top_deep_reports_page():
    _render_section_intro(
        "Top Deep Reports",
        "Top 종목 자동 정밀분석",
        "스캔 완료 시 Top 후보에 대해 생성된 실제 데이터 기반 분석 리포트를 날짜/스캔별로 조회합니다.",
        ["Auto after scan", "Real data only", "Signal review"],
    )
    rows, warning = _load_top_deep_reports()
    if warning:
        st.warning(f"Supabase 조회 실패 또는 제한: {warning}. 로컬 리포트가 있으면 대체 표시합니다.")
    if not rows:
        st.info("아직 생성된 Top 정밀분석 리포트가 없습니다. 스캔을 1회 완료하면 자동 생성됩니다.")
        return

    df = pd.DataFrame(rows)
    df["generated_at_dt"] = pd.to_datetime(df.get("generated_at"), errors="coerce", utc=True)
    df["report_date"] = df["generated_at_dt"].dt.tz_convert("Asia/Seoul").dt.date
    dates = sorted([d for d in df["report_date"].dropna().unique()], reverse=True)
    col_date, col_run, col_size = st.columns([1.4, 2.2, 1])
    selected_date = col_date.selectbox("날짜", dates, index=0)
    day_df = df[df["report_date"] == selected_date].copy()
    runs = list(day_df.sort_values("generated_at_dt", ascending=False)["run_id"].dropna().unique())
    selected_run = col_run.selectbox("스캔 Run", runs, index=0)
    page_size = col_size.selectbox("페이지 크기", [1, 3, 5, 10], index=1)
    run_df = day_df[day_df["run_id"] == selected_run].copy()
    run_df["rank"] = pd.to_numeric(run_df.get("rank"), errors="coerce")
    run_df = run_df.sort_values(["rank", "generated_at_dt"], ascending=[True, False])
    total = len(run_df)
    max_page = max(1, math.ceil(total / int(page_size)))
    page = st.number_input("페이지", min_value=1, max_value=max_page, value=1, step=1)
    page_df = run_df.iloc[(int(page) - 1) * int(page_size): int(page) * int(page_size)]
    st.caption(f"{selected_date} · `{selected_run}` · {total}건 · {page}/{max_page} 페이지")

    for row in page_df.to_dict("records"):
        price = row.get("price") if isinstance(row.get("price"), dict) else {}
        news = row.get("news") if isinstance(row.get("news"), dict) else {}
        prediction = row.get("prediction") if isinstance(row.get("prediction"), dict) else {}
        trade_plan = row.get("trade_plan") if isinstance(row.get("trade_plan"), dict) else {}
        theme = row.get("theme") if isinstance(row.get("theme"), dict) else {}
        title = f"#{int(row.get('rank') or 0)} {row.get('stock_name') or row.get('ticker')} ({row.get('ticker')})"
        with st.container(border=True):
            st.markdown(f"### {title}")
            st.caption(f"{row.get('signal_label') or '-'} · {row.get('decision') or '-'} · {theme.get('primary_theme') or '-'}")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("매수점수", _fmt_metric_num(row.get("buy_score"), 1))
            c2.metric("정확성", _fmt_metric_pct(row.get("accuracy")))
            c3.metric("전일비", _fmt_metric_pct(row.get("day_change_pct")))
            c4.metric("손실위험", _fmt_metric_num(row.get("loss_risk_score"), 1))
            c5.metric("뉴스감성", _fmt_metric_num(news.get("sentiment_score"), 2))

            p1, p2, p3, p4 = st.columns(4)
            p1.metric("현재가", _fmt_metric_num(price.get("current_price"), 2))
            p2.metric("거래량", f"{int(price.get('volume')):,}" if price.get("volume") is not None else "-")
            p3.metric("거래량/20D", _fmt_metric_num(price.get("volume_ratio_20d"), 2))
            p4.metric("차트추세", str(price.get("trend") or "-"))

            e1, e2, e3, e4 = st.columns(4)
            e1.metric("1D 기대", _fmt_metric_pct(prediction.get("expected_return_1d_pct")))
            e2.metric("3D 기대", _fmt_metric_pct(prediction.get("expected_return_3d_pct")))
            e3.metric("Entry", str(trade_plan.get("entry_policy") or _fmt_metric_num(trade_plan.get("entry_reference_price"), 2)))
            e4.metric("TP/SL", f"{_fmt_metric_pct(trade_plan.get('target_tp_pct'))} / {_fmt_metric_pct(trade_plan.get('stop_sl_pct'))}")

            ohlcv = price.get("ohlcv_tail") if isinstance(price.get("ohlcv_tail"), list) else []
            if ohlcv:
                chart_df = pd.DataFrame(ohlcv)
                if "date" in chart_df and "close" in chart_df:
                    st.line_chart(chart_df.set_index("date")[["close"]])

            flags = row.get("risk_flags") if isinstance(row.get("risk_flags"), list) else []
            rationale = row.get("rationale") if isinstance(row.get("rationale"), list) else []
            if flags or rationale:
                st.caption("리스크/판단 근거: " + " / ".join([str(x) for x in (flags + rationale)[:8]]))

            headlines = news.get("headlines") if isinstance(news.get("headlines"), list) else []
            if headlines:
                with st.expander("뉴스/공시성 헤드라인", expanded=False):
                    for item in headlines[:5]:
                        st.caption(f"{_fmt_metric_num(item.get('score'), 2)} · {item.get('title')}")
            warnings = row.get("data_warnings") if isinstance(row.get("data_warnings"), list) else []
            if warnings:
                st.caption("데이터 경고: " + " / ".join(str(x) for x in warnings[:5]))


def _scan_is_running(snapshot=None):
    snap = snapshot or _get_scan_state_snapshot()
    return bool(snap and snap.get("status") in {"queued", "running"})


def _start_market_scan_job(*, market, max_scan, scan_mode, engine_opt, is_advanced_engine):
    if _scan_is_running():
        return False

    live_refresh = live_mode_enabled(market)
    try:
        st.session_state["macro_ctx"] = get_macro_context(
            force_refresh=live_refresh,
            market_group=normalize_market_key(market),
        )
    except Exception:
        pass
    st.session_state["market_gate"] = compute_market_gate(market)

    scan_state = BackgroundScanState(
        market=str(market),
        scan_mode=str(scan_mode),
        engine_label=str(engine_opt),
        max_scan=int(max_scan or 0),
    )
    st.session_state["scan_job_state"] = scan_state

    thread = threading.Thread(
        target=_run_market_scan_job,
        kwargs={
            "scan_state": scan_state,
            "market": market,
            "max_scan": max_scan,
            "scan_mode": scan_mode,
            "engine_opt": engine_opt,
            "is_advanced_engine": is_advanced_engine,
            "macro_ctx": st.session_state.get("macro_ctx", {}),
            "market_gate": st.session_state.get("market_gate", {}),
        },
        daemon=True,
    )
    st.session_state["scan_job_thread"] = thread
    thread.start()
    return True


def _run_market_scan_job(*, scan_state, market, max_scan, scan_mode, engine_opt, is_advanced_engine, macro_ctx, market_gate):
    try:
        scan_state.update(status="running", status_line="스캔 실행을 준비 중입니다.")
        regime = quant_analysis.QuantStrategy.detect_market_regime(market)
        scan_state.update(regime=regime or {})

        tickers_dict = quant_analysis.QuantStrategy.get_market_tickers(market)
        ticker_list = list(tickers_dict.keys())
        planned_scan_count = len(ticker_list) if max_scan <= 0 else min(len(ticker_list), max_scan)
        scan_state.update(
            total_scans=planned_scan_count,
            status_line=f"총 {len(ticker_list)}개 종목 중 {planned_scan_count}개를 스캔합니다.",
        )

        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        intel_data = market_intelligence.get_market_intelligence(market, gemini_key, force_refresh=True)
        if isinstance(intel_data, dict):
            scan_state.update(intel_data=intel_data)

        is_us = market in ["NASDAQ", "S&P500", "AMEX"]
        is_amex = market == "AMEX"
        diagnostics = scan_state.scan_diagnostics
        results = []

        def scan_worker(sym):
            def _on_reject(_sym, reason):
                code = str(reason or "UNKNOWN")
                counts = diagnostics["reject_reason_counts"]
                counts[code] = int(counts.get(code, 0) or 0) + 1
                diagnostics["reject_reasons_by_symbol"][_sym] = code

            def _on_reject_detail(_sym, meta):
                details = diagnostics["reject_details_by_symbol"]
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
                r_status=str((regime or {}).get("regime", "NEUTRAL")),
                intel_data=intel_data,
                macro_ctx=macro_ctx,
                market_gate=market_gate,
                rank_adjustment_fn=compute_rank_adjustment,
                news_adjustment_fn=market_intelligence.calculate_news_adjustment,
                backoff_state=_SCAN_BACKOFF_STATE,
                max_retries=2,
                scan_mode=scan_mode,
                run_id=scan_state.run_id,
                reject_reason_fn=_on_reject,
                reject_detail_fn=_on_reject_detail,
            )

        def _on_scan_item(i, total_scans, sym, data, exc):
            scan_state.update(
                completed_scans=i + 1,
                current_symbol=sym,
                progress=compute_progress_fraction(i + 1, total_scans),
                status_line=f"스캔 진행 중... [{i + 1}/{total_scans}] {sym}",
            )
            if exc is not None:
                diagnostics["executor_exception_count"] += 1
                diagnostics["exception_symbols"].append(sym)
                scan_state.append_log("error", f"❌ {sym} 실행 중 에러: {exc}")
                return

            if data:
                if "error" in data:
                    diagnostics["worker_error_count"] += 1
                    diagnostics["error_symbols"].append(sym)
                    scan_state.append_log("error", f"❌ {data['ticker']} 스캔 중 에러: {data['error']}")
                else:
                    results.append(data)
                    scan_state.append_result(data)
                    scan_state.append_log("info", f"✅ {data.get('종목명') or data.get('Ticker') or sym} 후보 반영")
            else:
                diagnostics["filtered_count"] += 1
                diagnostics["filtered_symbols"].append(sym)

        run_parallel_scan(
            ticker_list=ticker_list,
            max_scan=max_scan,
            worker_fn=scan_worker,
            max_workers=2,
            on_item=_on_scan_item,
        )

        bridge_info = run_legacy_agent_bridge(
            results=results,
            market=market,
            strategy_version="legacy-ui-v1",
            model_version="legacy",
            code_version="bridge-v1",
            summary_overrides={
                "total_scans": planned_scan_count,
                "diagnostics": diagnostics,
                "market_gate": market_gate,
                "regime": regime,
                "execution_profile": os.getenv("AG_SCAN_PROFILE", "prod"),
                "warnings": [],
                "source": "scanner_agent_input",
                "scan_mode": scan_mode,
                "run_id": scan_state.run_id,
            },
            run_id=scan_state.run_id,
            logger=lambda line: scan_state.append_log("info", line),
        )
        try:
            planner_payload = _load_json_safe(bridge_info.get("planner_handoff")) if isinstance(bridge_info, dict) else {}
            deep_result = generate_and_store_top_deep_reports(
                scan_rows=results,
                planner_payload=planner_payload,
                run_id=scan_state.run_id,
                market=market,
                scan_mode=scan_mode,
                top_n=5,
                write_db=os.getenv("AG_TOP_DEEP_WRITE_DB", "1") != "0",
            )
            if isinstance(bridge_info, dict):
                bridge_info["top_deep_reports"] = deep_result
            scan_state.append_log(
                "info",
                f"🔬 Top 정밀분석 리포트 {deep_result.get('count', 0)}건 생성: {deep_result.get('local_path', '')}",
            )
            db_warning = ((deep_result.get("db_result") or {}) if isinstance(deep_result, dict) else {}).get("warning")
            if db_warning:
                scan_state.append_log("warning", f"⚠️ Top 정밀분석 DB 저장 경고: {db_warning}")
        except Exception as exc:
            if isinstance(bridge_info, dict):
                bridge_info.setdefault("errors", []).append(f"top_deep_report_failed:{exc}")
            scan_state.append_log("error", f"❌ Top 정밀분석 리포트 생성 실패: {exc}")

        scan_state.update(
            status="completed",
            finished_at=date.today().toordinal(),
            progress=1.0,
            current_symbol="",
            status_line="스캔이 완료되었습니다.",
            bridge_info=bridge_info or {},
            scan_diagnostics=diagnostics,
        )
    except Exception as exc:
        scan_state.update(
            status="failed",
            error=str(exc),
            status_line=f"스캔 실패: {exc}",
        )
        scan_state.append_log("error", f"❌ 스캔 실패: {exc}")


def _render_market_intelligence_panel(intel_data, market, *, compact=False):
    if not isinstance(intel_data, dict) or not intel_data:
        if compact:
            st.caption("아직 불러온 시장 인텔리전스가 없습니다.")
        return

    sent = str(intel_data.get("market_sentiment", "NEUTRAL") or "NEUTRAL").upper()
    sent_icon = {"BULLISH": "🟢", "BEARISH": "🔴", "MIXED": "🟡", "NEUTRAL": "⚪"}.get(sent, "⚪")
    tone = {"BULLISH": "good", "BEARISH": "danger", "MIXED": "caution", "NEUTRAL": "good"}.get(sent, "good")
    source = str(intel_data.get("source", "unknown") or "unknown")
    display_origin = str(intel_data.get("_display_origin", "live") or "live")
    timestamp = str(intel_data.get("timestamp", "") or "")
    headline_count = int(intel_data.get("headline_count", 0) or 0)
    theme_states = intel_data.get("theme_states") if isinstance(intel_data.get("theme_states"), list) else []
    beneficiary = intel_data.get("beneficiary_themes") if isinstance(intel_data.get("beneficiary_themes"), list) else []
    headwind = intel_data.get("headwind_themes") if isinstance(intel_data.get("headwind_themes"), list) else []

    source_label = source
    if display_origin == "cache":
        source_label = f"{source} (cached)"
    elif display_origin == "scan_snapshot":
        source_label = f"{source} (scan snapshot)"

    if headline_count <= 0:
        st.warning("시장 헤드라인 수집이 제한되어 기본 인텔리전스를 사용 중입니다.")
    elif source.startswith("rss_rule_based_rate_limited"):
        st.info("LLM 호출 한도에 걸려 현재 헤드라인 기반 rule 인텔리전스를 사용 중입니다.")
    elif source.startswith("rss_rule_based"):
        st.info("현재 헤드라인을 기반으로 rule 인텔리전스를 사용 중입니다.")
    elif source.startswith("fallback") or "error" in source:
        st.warning("시장 인텔리전스 생성 중 오류가 있었지만, 수집된 헤드라인으로 분석을 이어가고 있습니다.")

    beneficiary_line = _intelligence_signal_line(intel_data, kind="beneficiary", limit=4)
    headwind_line = _intelligence_signal_line(intel_data, kind="headwind", limit=4)
    tactical_line = _intelligence_tactical_line(intel_data)

    if compact:
        key_insight = str(intel_data.get("key_insight", "") or "").strip() or "아직 핵심 인사이트가 구조화되지 않았습니다."
        meta = f"{market} · {source_label} · 헤드라인 {headline_count}"
        if timestamp:
            meta += f" · {timestamp}"
        st.markdown(
            f"""
            <div class="top-intel-grid">
              <section class="top-intel-card">
                <div class="top-intel-kicker">Market Brief</div>
                <div class="top-intel-title">{html.escape(sent_icon)} {html.escape(sent)}</div>
                <div class="top-intel-body">{html.escape(key_insight)}</div>
                <div class="top-intel-meta">{html.escape(meta)}</div>
              </section>
              <section class="top-intel-card">
                <div class="top-intel-kicker">Tailwind</div>
                <div class="top-intel-title">강세 축</div>
                <div class="top-intel-body">{html.escape(beneficiary_line)}</div>
                <div class="top-intel-meta">현재 시장에서 버티는 섹터/스타일 축입니다.</div>
              </section>
              <section class="top-intel-card">
                <div class="top-intel-kicker">Risk</div>
                <div class="top-intel-title">경계 축</div>
                <div class="top-intel-body">{html.escape(headwind_line)}</div>
                <div class="top-intel-meta">{html.escape(tactical_line)}</div>
              </section>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    _render_status_banner(
        f"🧠 {market} Intelligence · {sent_icon} {sent}",
        str(intel_data.get("key_insight", "N/A") or "N/A"),
        tone=tone,
        caption=(f"Source {source_label} · Headlines {headline_count} · {timestamp}" if timestamp else f"Source {source_label} · Headlines {headline_count}"),
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric("Sentiment", sent)
    metric_cols[1].metric("Theme Count", len(theme_states))
    metric_cols[2].metric("Beneficiary", len(beneficiary))
    metric_cols[3].metric("Headwind", len(headwind) if headwind else 0, f"헤드라인 {headline_count}")

    _render_intelligence_highlights(_build_intelligence_highlights(intel_data))

    theme_col1, theme_col2 = st.columns(2)
    with theme_col1:
        st.markdown("#### 강세 테마")
        _render_theme_cards(
            beneficiary if beneficiary else [row for row in theme_states if str(row.get("direction", "")).upper() == "BENEFICIARY"],
            empty_text="현재 뚜렷한 강세 테마가 많지 않습니다.",
            compact=compact,
        )
    with theme_col2:
        st.markdown("#### 약세 테마")
        _render_theme_cards(
            headwind if headwind else [row for row in theme_states if str(row.get("direction", "")).upper() == "HEADWIND"],
            empty_text="현재 크게 눌리는 테마는 많지 않습니다.",
            compact=compact,
        )

    neutral_rows = [row for row in theme_states if str(row.get("direction", "")).upper() == "NEUTRAL"]
    if neutral_rows:
        st.markdown("#### 관찰 테마")
        _render_theme_cards(neutral_rows, empty_text="중립 관찰 테마가 없습니다.", compact=False)

    support_col1, support_col2 = st.columns(2)
    with support_col1:
        risk_rows = _coerce_text_rows(intel_data.get("risk_flags"), limit=4)
        macro_rows = _coerce_text_rows(intel_data.get("macro_drivers"), limit=4)
        if risk_rows:
            st.markdown(
                '<div class="intel-subtle-card"><strong>리스크 플래그</strong><span>'
                + html.escape(" / ".join(risk_rows))
                + '</span></div>',
                unsafe_allow_html=True,
            )
        if macro_rows:
            st.markdown(
                '<div class="intel-subtle-card"><strong>매크로 드라이버</strong><span>'
                + html.escape(" / ".join(macro_rows))
                + '</span></div>',
                unsafe_allow_html=True,
            )
    with support_col2:
        cross_rows = _coerce_text_rows(intel_data.get("cross_asset_signals"), limit=4)
        disclosure_rows = _coerce_text_rows(intel_data.get("disclosure_events"), limit=3)
        if cross_rows:
            st.markdown(
                '<div class="intel-subtle-card"><strong>크로스애셋 신호</strong><span>'
                + html.escape(" / ".join(cross_rows))
                + '</span></div>',
                unsafe_allow_html=True,
            )
        if disclosure_rows:
            st.markdown(
                '<div class="intel-subtle-card"><strong>공시 이벤트</strong><span>'
                + html.escape(" / ".join(disclosure_rows))
                + '</span></div>',
                unsafe_allow_html=True,
            )


def _render_intelligence_detail_sections(intel_data):
    if not isinstance(intel_data, dict) or not intel_data:
        return
    neutral_rows = [
        row for row in (intel_data.get("theme_states") or [])
        if isinstance(row, dict) and str(row.get("direction", "")).upper() == "NEUTRAL"
    ]
    if neutral_rows:
        st.markdown("### 👀 관찰 테마")
        _render_theme_cards(neutral_rows, empty_text="중립 관찰 테마가 없습니다.", compact=False)

    support_col1, support_col2 = st.columns(2)
    with support_col1:
        risk_rows = _coerce_text_rows(intel_data.get("risk_flags"), limit=4)
        macro_rows = _coerce_text_rows(intel_data.get("macro_drivers"), limit=4)
        if risk_rows:
            st.markdown(
                '<div class="intel-subtle-card"><strong>리스크 플래그</strong><span>'
                + html.escape(" / ".join(risk_rows))
                + '</span></div>',
                unsafe_allow_html=True,
            )
        if macro_rows:
            st.markdown(
                '<div class="intel-subtle-card"><strong>매크로 드라이버</strong><span>'
                + html.escape(" / ".join(macro_rows))
                + '</span></div>',
                unsafe_allow_html=True,
            )
    with support_col2:
        cross_rows = _coerce_text_rows(intel_data.get("cross_asset_signals"), limit=4)
        disclosure_rows = _coerce_text_rows(intel_data.get("disclosure_events"), limit=4)
        if cross_rows:
            st.markdown(
                '<div class="intel-subtle-card"><strong>크로스애셋 신호</strong><span>'
                + html.escape(" / ".join(cross_rows))
                + '</span></div>',
                unsafe_allow_html=True,
            )
        if disclosure_rows:
            st.markdown(
                '<div class="intel-subtle-card"><strong>공시 이벤트</strong><span>'
                + html.escape(" / ".join(disclosure_rows))
                + '</span></div>',
                unsafe_allow_html=True,
            )


def _render_top_intelligence_summary(market, intel_data):
    if not isinstance(intel_data, dict) or not intel_data:
        return
    sentiment = str(intel_data.get("market_sentiment", "NEUTRAL") or "NEUTRAL").upper()
    key_insight = str(intel_data.get("key_insight", "") or "").strip() or "아직 핵심 인사이트가 없습니다."
    top_beneficiary = ", ".join(
        str(row.get("theme_name") or "").strip()
        for row in (intel_data.get("beneficiary_themes") or [])[:3]
        if str(row.get("theme_name") or "").strip()
    ) or "뚜렷한 강세 테마 없음"
    top_headwind = ", ".join(
        str(row.get("theme_name") or "").strip()
        for row in (intel_data.get("headwind_themes") or [])[:3]
        if str(row.get("theme_name") or "").strip()
    ) or "뚜렷한 약세 테마 없음"
    source = str(intel_data.get("source", "unknown") or "unknown")
    display_origin = str(intel_data.get("_display_origin", "live") or "live")
    timestamp = str(intel_data.get("timestamp", "") or "")
    if display_origin == "cache":
        source = f"{source} (cached)"
    elif display_origin == "scan_snapshot":
        source = f"{source} (scan snapshot)"
    meta = f"{market} · {source}"
    if timestamp:
        meta += f" · {timestamp}"

    st.markdown(
        f"""
        <div class="top-intel-grid">
          <section class="top-intel-card">
            <div class="top-intel-kicker">Market Mood</div>
            <div class="top-intel-title">{html.escape(sentiment)}</div>
            <div class="top-intel-body">{html.escape(key_insight)}</div>
            <div class="top-intel-meta">{html.escape(meta)}</div>
          </section>
          <section class="top-intel-card">
            <div class="top-intel-kicker">Beneficiary Themes</div>
            <div class="top-intel-title">강세 테마</div>
            <div class="top-intel-body">{html.escape(top_beneficiary)}</div>
            <div class="top-intel-meta">현재 시장에서 상대적으로 받쳐주는 축입니다.</div>
          </section>
          <section class="top-intel-card">
            <div class="top-intel-kicker">Headwind Themes</div>
            <div class="top-intel-title">약세 테마</div>
            <div class="top-intel-body">{html.escape(top_headwind)}</div>
            <div class="top-intel-meta">리스크 관리 시 먼저 확인할 부담 축입니다.</div>
          </section>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_theme_distribution_workspace(market, intel_data, summary=None):
    summary = summary or build_theme_distribution_summary(market, intel_data=intel_data, top_n=12)
    rows = summary.get("rows", [])
    return_covered_symbols = sum(int(row.get("return_coverage", 0) or 0) for row in rows)
    best_row = rows[0] if rows else {}
    best_return = best_row.get("avg_day_return_pct")
    _render_status_banner(
        "테마 분포 맵",
        f"총 {summary.get('total_symbols', 0)}개 종목 중 {summary.get('classified_symbols', 0)}개가 테마로 분류되었고, 그래프는 테마별 평균 당일 등락률 기준으로 집계됩니다.",
        tone="good",
        caption=(
            f"분류율 {round(float(summary.get('classified_ratio', 0.0) or 0.0) * 100, 1)}%"
            f" · 수익률 커버리지 {return_covered_symbols}개"
            f" · 최고 테마 {summary.get('top_theme', 'unclassified')}"
        ),
    )
    if not rows:
        st.info("아직 테마 분포를 그릴 수 있을 만큼 분류된 종목 데이터가 없습니다.")
        return

    metric_cols = st.columns(4)
    metric_cols[0].metric("분류 종목", int(summary.get("classified_symbols", 0)))
    metric_cols[1].metric("수익률 커버리지", int(return_covered_symbols))
    metric_cols[2].metric("대분류 수", len(rows))
    metric_cols[3].metric(
        "Top Return",
        f"{float(best_return):+.2f}%" if best_return is not None else "-",
        str(best_row.get("theme_name", "unclassified")),
    )

    theme_df = pd.DataFrame(
        [
            {
                "Theme": row.get("theme_name"),
                "AvgReturnPct": float(row.get("avg_day_return_pct", 0.0) or 0.0),
                "Coverage": int(row.get("return_coverage", 0)),
                "Symbols": int(row.get("symbol_count", 0)),
                "Confidence": round(float(row.get("avg_confidence", 0.0) or 0.0) * 100, 1),
                "Strength": float(row.get("strength_score", 0.0) or 0.0),
                "Direction": str(row.get("direction", "NEUTRAL") or "NEUTRAL"),
                "Momentum": str(row.get("momentum_class", "") or ""),
                "HasReturn": row.get("avg_day_return_pct") is not None,
            }
            for row in rows
        ]
    )
    theme_df["BarColor"] = theme_df.apply(
        lambda row: "#d0d5dd" if not bool(row["HasReturn"]) else ("#17b26a" if float(row["AvgReturnPct"]) >= 0 else "#f04452"),
        axis=1,
    )
    fig = go.Figure(
        go.Bar(
            x=theme_df["AvgReturnPct"],
            y=theme_df["Theme"],
            orientation="h",
            marker=dict(color=theme_df["BarColor"]),
            customdata=theme_df[["Coverage", "Symbols", "Confidence", "Strength", "Momentum", "Direction"]],
            hovertemplate=(
                "<b>%{y}</b><br>평균 당일 등락률 %{x:+.2f}%"
                "<br>수익률 커버리지 %{customdata[0]}개"
                "<br>분류 종목수 %{customdata[1]}개"
                "<br>평균 신뢰 %{customdata[2]}%"
                "<br>강도 %{customdata[3]}"
                "<br>모멘텀 %{customdata[4]}"
                "<br>방향 %{customdata[5]}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        height=460,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="평균 당일 등락률 (%)",
        yaxis_title="테마 대분류",
    )
    fig.update_yaxes(categoryorder="array", categoryarray=list(reversed(theme_df["Theme"].tolist())))
    fig.add_vline(x=0.0, line_width=1, line_dash="dash", line_color="#98a2b3")
    st.plotly_chart(fig, use_container_width=True)

    selected_theme = st.selectbox(
        "테마 상세 보기",
        options=[row.get("theme_name") for row in rows],
        key=f"intelligence_theme_detail_{market}",
    )
    selected_row = next((row for row in rows if row.get("theme_name") == selected_theme), rows[0])

    detail_col1, detail_col2 = st.columns([1.4, 1])
    with detail_col1:
        st.markdown(f"#### {selected_row.get('theme_name')} 상세 종목")
        symbol_rows = selected_row.get("symbols", []) or []
        if symbol_rows:
            symbol_rows = sorted(
                symbol_rows,
                key=lambda row: (
                    -9999.0 if row.get("day_return_pct") is None else float(row.get("day_return_pct", 0.0) or 0.0),
                    float(row.get("confidence", 0.0) or 0.0),
                ),
                reverse=True,
            )
            detail_df = pd.DataFrame(
                [
                    {
                        "Ticker": row.get("symbol"),
                        "Name": row.get("name"),
                        "1D Return %": round(float(row.get("day_return_pct", 0.0) or 0.0), 2) if row.get("day_return_pct") is not None else None,
                        "Confidence": round(float(row.get("confidence", 0.0) or 0.0) * 100, 1),
                        "Source": row.get("theme_source"),
                        "Industry": row.get("official_industry"),
                        "Products": row.get("official_products"),
                    }
                    for row in symbol_rows
                ]
            )
            st.dataframe(detail_df, use_container_width=True, hide_index=True)
        else:
            st.caption("이 테마에 연결된 종목 상세가 아직 없습니다.")
    with detail_col2:
        st.markdown("#### 테마 해석")
        st.markdown(
            '<div class="intel-subtle-card"><strong>평균 당일 등락률</strong><span>'
            + html.escape(
                (
                    f"{float(selected_row.get('avg_day_return_pct')):+.2f}%"
                    if selected_row.get("avg_day_return_pct") is not None
                    else "데이터 없음"
                )
            )
            + '</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="intel-subtle-card"><strong>수익률 커버리지</strong><span>'
            + html.escape(
                f"{int(selected_row.get('return_coverage', 0))}/{int(selected_row.get('symbol_count', 0))} 종목"
            )
            + '</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="intel-subtle-card"><strong>방향/강도</strong><span>'
            + html.escape(
                f"{selected_row.get('direction', 'NEUTRAL')} · 강도 {selected_row.get('strength_score', 0)} · 모멘텀 {selected_row.get('momentum_class', '-') or '-'}"
            )
            + '</span></div>',
            unsafe_allow_html=True,
        )
        source_mix = selected_row.get("source_mix", {}) or {}
        if source_mix:
            source_text = " / ".join(f"{key}:{value}" for key, value in source_mix.items())
            st.markdown(
                '<div class="intel-subtle-card"><strong>분류 근거 소스</strong><span>'
                + html.escape(source_text)
                + '</span></div>',
                unsafe_allow_html=True,
            )
        industry_samples = selected_row.get("industry_samples", []) or []
        if industry_samples:
            st.markdown(
                '<div class="intel-subtle-card"><strong>대표 업종</strong><span>'
                + html.escape(" / ".join(industry_samples))
                + '</span></div>',
                unsafe_allow_html=True,
            )
        product_samples = selected_row.get("product_samples", []) or []
        if product_samples:
            st.markdown(
                '<div class="intel-subtle-card"><strong>대표 제품/사업</strong><span>'
                + html.escape(" / ".join(product_samples))
                + '</span></div>',
                unsafe_allow_html=True,
            )


def _render_scan_results_snapshot(snapshot):
    results = snapshot.get("results", [])
    bridge_info = snapshot.get("bridge_info", {})
    market = snapshot.get("market", "KOSPI")
    if not results:
        if isinstance(snapshot.get("intel_data"), dict) and snapshot.get("intel_data"):
            _render_market_intelligence_panel(snapshot.get("intel_data", {}), market, compact=True)
        st.warning("⚠️ 조건에 맞는 종목을 찾지 못했습니다.")
        _render_agent_bridge_status(bridge_info, market)
        return

    st.success(f"✅ 스캔 완료: {len(results)}개 후보가 유지되었습니다.")
    st.caption(snapshot.get("status_line", ""))
    _render_market_intelligence_panel(snapshot.get("intel_data", {}), market, compact=True)

    df_results = pd.DataFrame(results)
    sort_col = "Decision Score" if "Decision Score" in df_results.columns else df_results.columns[0]
    if sort_col in df_results.columns:
        df_results = df_results.sort_values(sort_col, ascending=False, na_position="last")
    _render_scan_top_candidates(df_results, bridge_info, market)

    if len(df_results) > 5:
        with st.expander("추가 후보 보기", expanded=False):
            planner_payload = _load_json_safe(bridge_info.get("planner_handoff")) if isinstance(bridge_info, dict) else {}
            extra_records = enrich_signal_rows_with_planner_trace(
                df_results.to_dict("records"),
                planner_payload,
            )
            extra_records = sort_signal_rows_by_planner_rank(extra_records, planner_payload)[5:]
            _render_signal_card_list(build_signal_display_rows(extra_records))
    _render_agent_bridge_status(bridge_info, market)


def _render_scan_job_panel():
    snapshot = _get_scan_state_snapshot()
    if not snapshot:
        st.info("시장, 모드, 엔진을 고른 뒤 스캔을 시작하면 여기서 실시간 진행상태와 결과를 이어서 볼 수 있습니다.")
        return

    tone = "good"
    if snapshot["status"] in {"queued", "running"}:
        tone = "caution"
    elif snapshot["status"] == "failed":
        tone = "danger"

    _render_status_banner(
        f"스캔 상태 · {snapshot['status'].upper()}",
        f"{snapshot.get('status_line', '')} · {snapshot.get('market', '')} · {snapshot.get('scan_mode', '')}",
        tone=tone,
        caption=f"진행률 {int(round(float(snapshot.get('progress', 0.0)) * 100))}% | 완료 {snapshot.get('completed_scans', 0)}/{snapshot.get('total_scans', 0)}",
    )

    st.progress(float(snapshot.get("progress", 0.0)))
    if isinstance(snapshot.get("intel_data"), dict) and snapshot.get("intel_data"):
        st.markdown("### 실시간 인텔리전스 요약")
        _render_market_intelligence_panel(snapshot.get("intel_data", {}), snapshot.get("market", "KOSPI"), compact=True)
    if snapshot["status"] in {"queued", "running"}:
        with st.expander("📝 진행 로그", expanded=True):
            logs = snapshot.get("logs", [])
            if logs:
                for row in logs[-20:]:
                    level = row.get("level")
                    message = row.get("message", "")
                    if level == "error":
                        st.error(message)
                    else:
                        st.caption(message)
            else:
                st.caption("아직 기록된 로그가 없습니다.")
    elif snapshot["status"] == "failed":
        st.error(snapshot.get("error", "알 수 없는 오류"))
    else:
        _render_scan_results_snapshot(snapshot)


def _render_intelligence_workspace():
    _render_section_intro(
        "Market Intelligence",
        "테마 인텔리전스",
        "시장 분위기, 강세·약세 테마, 핵심 리스크를 한 화면에서 읽을 수 있도록 정리한 전용 탭입니다.",
        ["Theme view", "Core summary", "Readable evidence"],
    )
    selector_col, action_col = st.columns([4, 1])
    intel_market = selector_col.selectbox(
        "인텔리전스 시장",
        ["KOSPI", "KOSDAQ", "NASDAQ", "S&P500", "AMEX"],
        key="selected_intelligence_market",
    )
    refresh_intel = action_col.button("새로고침", key="refresh_intelligence_tab", use_container_width=True)

    snapshot = _get_scan_state_snapshot()
    snapshot_market = str(snapshot.get("market", "") or "") if snapshot else ""
    if (
        snapshot
        and _scan_is_running(snapshot)
        and snapshot_market == intel_market
        and isinstance(snapshot.get("intel_data"), dict)
        and snapshot.get("intel_data")
    ):
        intel_data = dict(snapshot.get("intel_data", {}))
        intel_data["_display_origin"] = "scan_snapshot"
    else:
        intel_data = market_intelligence.get_market_intelligence(
            intel_market,
            os.environ.get("GEMINI_API_KEY", ""),
            force_refresh=bool(refresh_intel),
        )

    # Top intelligence summary (Market Mood / 강세 / 약세 카드) — L0 에서 옮겨옴
    _render_top_intelligence_summary(intel_market, intel_data)

    theme_summary = build_theme_distribution_summary(intel_market, intel_data=intel_data, top_n=12)
    _render_intelligence_overview_dashboard(intel_market, intel_data, theme_summary)
    st.markdown("---")
    _render_theme_distribution_workspace(intel_market, intel_data, summary=theme_summary)
    st.markdown("---")
    _render_intelligence_detail_sections(intel_data)


def _render_scan_continuity_banner(active_tab):
    snapshot = _get_scan_state_snapshot()
    if not snapshot:
        return

    prev_tab = st.session_state.get("last_active_main_tab")
    if _scan_is_running(snapshot) and prev_tab == "🚀 스캐너" and active_tab != "🚀 스캐너":
        toast_key = f"{snapshot['job_id']}:{active_tab}:running"
        if st.session_state.get("scan_nav_toast_key") != toast_key:
            st.session_state["scan_nav_toast_key"] = toast_key
            st.toast(
                f"스캐너가 백그라운드에서 진행 중입니다. {snapshot.get('completed_scans', 0)}/{snapshot.get('total_scans', 0)} 완료",
                icon="⏳",
            )

    status_key = f"{snapshot['job_id']}:{snapshot['status']}"
    if snapshot["status"] == "completed" and st.session_state.get("scan_status_toast_key") != status_key:
        st.session_state["scan_status_toast_key"] = status_key
        st.toast("스캔이 완료되었습니다. 스캐너 탭에서 결과를 확인하세요.", icon="✅")

    if _scan_is_running(snapshot) and active_tab != "🚀 스캐너":
        _render_status_banner(
            "스캐너가 계속 실행 중입니다",
            snapshot.get("status_line", ""),
            tone="caution",
            caption=f"{snapshot.get('completed_scans', 0)}/{snapshot.get('total_scans', 0)} 완료",
        )
        if st.button("스캐너로 돌아가기", key="return_to_scanner"):
            st.session_state["active_main_tab"] = "🚀 스캐너"
            st.rerun()


_inject_toss_theme()
# 새로고침 트리거는 L0 디테일 expander에서 받는다. 기본값은 미클릭.
# 보조 도구 (차트 이미지 분석) 는 L0 에서 빠지고 🔎 정밀분석 탭 안으로 이동했다.
refresh_macro_clicked = False
refresh_gate_clicked = False

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

# Phase 19: Live Macro Weather Dashboard
# 첫 진입은 모듈 자체 10분 캐시(_macro_cache)에 위임 → 빠른 hit. 사용자가 명시적으로
# 새로고침 버튼을 누른 경우에만 force_refresh=True 로 강제 fetch.
if 'macro_ctx' not in st.session_state or refresh_macro_clicked:
    try:
        st.session_state['macro_ctx'] = get_macro_context(force_refresh=bool(refresh_macro_clicked))
    except Exception:
        st.session_state['macro_ctx'] = {'macro_state': 'NORMAL', 'macro_risk_score': 0, 'macro_penalty': 0, 'macro_multiplier': 1.0, 'flags': []}

macro_ctx = st.session_state.get('macro_ctx', {})
macro_state = macro_ctx.get('macro_state', 'NORMAL')
macro_risk  = macro_ctx.get('macro_risk_score', 0)
_mc_icons = {'NORMAL': '☀️', 'CAUTION': '⛅', 'RISK_OFF': '🌧️', 'CRASH': '🚨'}
_ico = _mc_icons.get(macro_state, _mc_icons['NORMAL'])

vix_str = f"VIX {macro_ctx['vix']:.1f} ({macro_ctx['vix_change_1d']:+.1f}%)" if macro_ctx.get('vix') else "VIX N/A"
tnx_str = f"10Y {macro_ctx['tnx']:.2f}%" if macro_ctx.get('tnx') else "10Y N/A"
krw_str = f"KRW {macro_ctx['krw']:,.0f} ({macro_ctx['krw_change_1d']:+.2f}%)" if macro_ctx.get('krw') else "KRW N/A"
spy_str = f"SPY {macro_ctx.get('spy_change_1d', 0):+.2f}%"
flags_str = ", ".join(macro_ctx.get('flags', [])) if macro_ctx.get('flags') else ""
macro_note = None
if macro_state == "CRASH":
    macro_note = "신규 매수 자제 구간입니다. 매크로 쇼크가 Decision Score에 직접 반영됩니다."
elif macro_state == "RISK_OFF":
    macro_note = "리스크 오프 감지로 방어적 필터와 페널티가 강화된 상태입니다."
elif macro_state == "CAUTION":
    macro_note = "주의 구간입니다. 고확신 후보 위주로 선별하는 보수적 해석이 유리합니다."
macro_tone = {"NORMAL": "good", "CAUTION": "caution", "RISK_OFF": "risk", "CRASH": "danger"}.get(macro_state, "good")
macro_body = f"Risk Score {macro_risk}/100 · {vix_str} · {tnx_str} · {krw_str} · {spy_str}"
if flags_str:
    macro_body += f" · Flags {flags_str}"

# --- Phase 25: Market Gate (KOSPI/KOSDAQ Daily Gate) ---
# Backtest proved: bad market days have 3~33% win rate → must warn users
_selected_gate_market = st.session_state.get("selected_scan_market", "KOSPI")
if (
    'market_gate' not in st.session_state
    or str(st.session_state.get('market_gate', {}).get('selected_market', '')).upper() != str(_selected_gate_market).upper()
):
    st.session_state['market_gate'] = compute_market_gate(_selected_gate_market)
_gate_info = st.session_state['market_gate']
_gate_tone_map = {"GREEN": "good", "YELLOW": "caution", "RED": "danger"}
_gate_tone = _gate_tone_map.get(_gate_info["gate"], "good")
try:
    _segment_accuracy_snapshot = get_segment_accuracy_snapshot()
except Exception as _segment_snapshot_error:
    _segment_accuracy_snapshot = {
        "source": "unavailable",
        "source_status": "error",
        "warning": str(_segment_snapshot_error),
        "rows_loaded": 0,
        "resolved_rows": 0,
        "segment_count": 0,
    }
_data_source = str(_segment_accuracy_snapshot.get("source") or "unknown").upper()
_data_status = str(_segment_accuracy_snapshot.get("source_status") or "unknown").upper()
_data_rows = int(_segment_accuracy_snapshot.get("resolved_rows") or 0)
_data_segments = int(_segment_accuracy_snapshot.get("segment_count") or 0)
_data_tone = "good" if _data_status == "OK" and _data_rows > 0 else "caution"

# === L0: 한 줄 컴팩트 상태바 (Market · Macro · Gate) ===
_compact_status_bar([
    {
        "label": "MARKET",
        "value": _selected_gate_market,
        "meta": "스캐너 탭에서 변경",
        "tone": "focus",
    },
    {
        "label": "MACRO",
        "value": f"{_ico} {macro_state}",
        "meta": f"Risk {macro_risk}/100 · {vix_str}",
        "tone": macro_tone,
    },
    {
        "label": "GATE",
        "value": f"{_gate_info['gate']}",
        "meta": str(_gate_info.get("msg", "") or "")[:80],
        "tone": _gate_tone,
    },
    {
        "label": "DATA",
        "value": f"{_data_source} · {_data_status}",
        "meta": f"resolved {_data_rows:,} · segments {_data_segments}",
        "tone": _data_tone,
    },
])

# 디테일 + 새로고침 컨트롤은 expander 안으로 (사용 빈도 낮음)
with st.expander("Macro / Gate 상세 · 새로고침", expanded=False):
    detail_left, detail_right = st.columns([1, 1])
    refresh_macro_clicked = detail_left.button(
        "🔄 매크로 새로고침", use_container_width=True, key="refresh_macro_detail"
    )
    refresh_gate_clicked = detail_right.button(
        "🔄 마켓 게이트 새로고침", use_container_width=True, key="refresh_gate_detail"
    )
    if refresh_macro_clicked:
        with st.spinner("📡 실시간 매크로 지표 갱신 중..."):
            try:
                st.session_state['macro_ctx'] = get_macro_context(force_refresh=True)
            except Exception:
                pass
        st.rerun()
    if refresh_gate_clicked:
        st.session_state['market_gate'] = compute_market_gate(_selected_gate_market)
        st.rerun()
    _render_status_banner(
        f"{_ico} Macro Weather · {macro_state}",
        macro_body,
        tone=macro_tone,
        caption=macro_note,
    )
    _render_status_banner(
        f"📡 Market Gate · {_gate_info['gate']}",
        _gate_info['msg'],
        tone=_gate_tone,
        caption=f"선택 시장: {_selected_gate_market}",
    )

with st.expander("운영 데이터 상태 · 정확성 원천", expanded=False):
    horizon_counts = _segment_accuracy_snapshot.get("horizon_counts", {})
    if not isinstance(horizon_counts, dict):
        horizon_counts = {}
    latest_ts = _segment_accuracy_snapshot.get("latest_timestamp") or "-"
    cols = st.columns(4)
    cols[0].metric("정확성 원천", f"{_data_source}", _data_status)
    cols[1].metric("누적 resolved", f"{_data_rows:,}")
    cols[2].metric("측정 segment", f"{_data_segments:,}")
    cols[3].metric("최신 데이터", str(latest_ts)[:10])
    hcols = st.columns(6)
    for idx, horizon in enumerate([1, 3, 5, 7, 14, 30]):
        hcols[idx].metric(f"{horizon}D 표본", f"{int(horizon_counts.get(horizon, 0) or 0):,}")
    warning = _segment_accuracy_snapshot.get("warning")
    source_path = _segment_accuracy_snapshot.get("source_path")
    if warning:
        st.warning(f"Supabase 직접 조회 실패 또는 제한: {warning}. 표시값은 실제 archive 누적 데이터로 대체됩니다.")
    if source_path:
        st.caption(f"fallback archive: {source_path}")

# 운영 기본 화면은 실제 매매 판단 흐름만 노출한다.
# 연구/진단 도구는 AG_UI_ADVANCED=1 에서만 열어 UI 잡음을 줄인다.
MAIN_TABS = ["🚀 스캐너", "🔬 Top 분석", "📚 아카이브"]
if ENABLE_ADVANCED_UI:
    MAIN_TABS = ["🚀 스캐너", "🔬 Top 분석", "🧠 인텔리전스", "📈 성과", "📚 아카이브", "🔎 정밀분석"]
if "active_main_tab" not in st.session_state:
    st.session_state["active_main_tab"] = MAIN_TABS[0]
elif st.session_state["active_main_tab"] not in MAIN_TABS:
    st.session_state["active_main_tab"] = MAIN_TABS[0]
active_main_tab = st.segmented_control(
    "메인 탭",
    MAIN_TABS,
    key="active_main_tab",
    selection_mode="single",
    label_visibility="collapsed",
)
if active_main_tab is None:
    active_main_tab = MAIN_TABS[0]


@st.fragment(run_every=2)
def _render_scan_continuity_fragment(active_tab_value):
    _render_scan_continuity_banner(active_tab_value)


_render_scan_continuity_fragment(active_main_tab)
st.session_state["last_active_main_tab"] = active_main_tab

if active_main_tab == "📈 성과":
    _render_daily_ops_overview()

if active_main_tab == "🔬 Top 분석":
    _render_top_deep_reports_page()

if active_main_tab == "🧠 인텔리전스":
    _render_intelligence_workspace()

# TAB 1: MARKET SCANNER
if active_main_tab == "🚀 스캐너":
    _render_section_intro(
        "Scanner",
        "전종목 자동 스캔",
        "시장과 모드만 고르고 큰 버튼 한 번이면 바로 스캔이 시작됩니다. Top 5 후보가 가장 위에, 추가 후보는 그 아래에 나옵니다.",
        ["Top 5 focus", "Market-aware gate", "Shared trace output"],
    )

    # Row 1: 시장 (좌) · 모드 (우) — 두 핵심 결정만
    col_market, col_mode = st.columns([1.4, 1])
    market = col_market.selectbox(
        "시장 선택",
        ["KOSPI", "KOSDAQ", "NASDAQ", "S&P500", "AMEX"],
        key="selected_scan_market",
    )
    scan_mode_label = col_mode.radio(
        "스캔 모드",
        ["스윙", "장중"],
        index=0,
        horizontal=True,
        key="scanner_mode_radio",
    )
    scan_mode = "INTRADAY" if scan_mode_label == "장중" else "SWING"
    _filter_caption = (
        "⏱️ Intraday Breakout / Trend" if scan_mode == "INTRADAY"
        else "🔥 Antigravity Score (Single Standard)"
    )

    # Row 2: Advanced 옵션 (스캔 개수) — 엔진은 V32.Flawless 단일화
    # 기존 Legacy(T+0) 엔진은 실전 슬리피지/볼륨 보정이 없어 production 표준으로 부적합 → 제거.
    engine_opt = "🔬 완전무결 엔진 (V32.Flawless: T+1 시가 진입, 실전 슬리피지 적용, U-Shape 거래량 보정, 소표본 패널티)"
    is_advanced_engine = True
    with st.expander("⚙️ 고급 옵션 · 스캔 개수", expanded=False):
        max_scan = st.slider(
            "스캔 개수 (0 = 전종목)",
            0, 3500, 0,
            key="scanner_max_scan_slider",
        )

    # Row 3: Primary CTA — 작은 caption 으로 현재 적용 모드 명시
    cta_col, hint_col = st.columns([1.1, 1.4])
    start_scan = cta_col.button(
        "🚀 스캔 시작",
        type="primary",
        use_container_width=True,
        disabled=_scan_is_running(),
    )
    hint_col.markdown(
        f'<div class="control-note" style="margin:0;">'
        f'<strong>적용 설정</strong>'
        f'<span>{html.escape(market)} · {html.escape(scan_mode_label)} · {html.escape(_filter_caption)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if start_scan:
        if _start_market_scan_job(
            market=market,
            max_scan=max_scan,
            scan_mode=scan_mode,
            engine_opt=engine_opt,
            is_advanced_engine=is_advanced_engine,
        ):
            st.toast(
                "스캐너를 백그라운드에서 시작했습니다. 다른 탭으로 이동해도 진행상태가 유지됩니다.",
                icon="🚀",
            )
            st.session_state["scan_nav_toast_key"] = None
            st.session_state["scan_status_toast_key"] = None
            st.rerun()

    snapshot = _get_scan_state_snapshot()
    if _scan_is_running(snapshot):
        st.info("스캔이 진행 중입니다. 다른 탭으로 이동해도 상태가 유지되고 완료 시 토스트로 알려드립니다.")
    elif snapshot and snapshot.get("status") == "completed":
        st.caption("이전 스캔 결과가 아래에 유지됩니다. 새 스캔을 시작하면 현재 결과를 교체합니다.")

    @st.fragment(run_every=2)
    def _render_scanner_job_panel_fragment():
        _render_scan_job_panel()

    if should_auto_refresh_scan_panel(snapshot.get("status") if snapshot else ""):
        _render_scanner_job_panel_fragment()
    else:
        _render_scan_job_panel()

    if ENABLE_ADVANCED_UI:
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
                                upload_payload = dict(eval_result["db_payload"] or {})
                                upload_payload.setdefault("scan_mode", "SWING")
                                upload_payload.setdefault("feature_origin", "app_excel_upload")
                                db.upsert_scan_result(upload_payload)
                            except Exception:
                                continue
                        if u_results:
                            st.success("✅ 파일 스캔 완료!")
                            st.dataframe(pd.DataFrame(u_results), width='stretch')
                except Exception as e:
                    st.error(f"파일 처리 중 오류 발생: {e}")

# TAB 3: SINGLE STOCK ANALYSIS (정밀분석)
if active_main_tab == "🔎 정밀분석":
    from modules import news_analysis, vision_analysis

    _render_section_intro(
        "Deep Dive",
        "종목 심층 분석",
        "단일 종목의 가격 보드, 리스크, 액션 플랜, 예측 결과를 한 흐름으로 읽을 수 있는 분석 화면입니다.",
        ["Single ticker", "Risk-aware", "Action plan"],
    )
    
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
                rt_price = resolve_display_price(qs.get_realtime_price(), latest.get('Close'))
                
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
                p5.metric("거래량 (Vol)", format_volume_display(latest.get('Volume')))
                
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

    # --- 보조 도구: 차트 이미지 Vision 분석 (정밀분석 탭 전용) ---
    with st.expander("🖼️ 보조 도구 · 차트 이미지 분석", expanded=False):
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            help="차트 이미지 Vision 분석을 사용할 때만 필요합니다.",
            key="main_openai_api_key",
        )
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        st.caption("이미지 기반 보조 분석 전용 설정입니다. 스캐너와 엔진 로직에는 영향을 주지 않습니다.")
        uploaded_file = st.file_uploader(
            "Upload Chart", type=["jpg", "png", "jpeg"], key="main_chart_upload"
        )
        if uploaded_file is not None and api_key:
            st.image(uploaded_file, caption="Uploaded Chart", width='stretch')
            if st.button("Analyze Image", key="main_image_analyze"):
                with st.spinner("AI is analyzing..."):
                    result = vision_analysis.analyze_chart_image(uploaded_file, api_key)
                    st.write(result)
        elif uploaded_file:
            st.warning("Enter API Key above.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: SCAN ARCHIVE (아카이브)
# ─────────────────────────────────────────────────────────────────────────────
if active_main_tab == "📚 아카이브":
    _render_section_intro(
        "Archive",
        "스캔 아카이브",
        "날짜별 스캔 결과를 복기하고 실제 수익률과 비교해 전략 품질을 점검하는 영역입니다. 같은 날 같은 티커는 최신 스캔 기준으로 정리됩니다.",
        ["Replay", "Outcome tracking", "Validation view"],
    )

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

                st.divider()
                # 스캐너 결과와 동일한 Stream A/B 8:2 분리. decision_score 정렬은 위에서 마침.
                _archive_records = _day_df.to_dict("records")
                _archive_streams = split_stream_records(_archive_records)
                _archive_stream_a = build_signal_display_rows(_archive_streams["stream_a"], limit=5)
                _archive_stream_b = build_signal_display_rows(_archive_streams["stream_b"], limit=5)

                st.markdown(f"### 🔥 Top 매수 신호 · Stream A (안전 매매, 자본 80%) — {_selected_date}")
                if _archive_stream_a:
                    _render_signal_card_list(_archive_stream_a, empty_text="Stream A 후보 없음.")
                else:
                    st.info("Stream A 후보 없음 — 게이트가 모두 demote.")

                st.markdown("### 🚨 Surge Capture · Stream B (급등 잡기, 자본 20%)")
                if _archive_stream_b:
                    _render_signal_card_list(_archive_stream_b, empty_text="Stream B 후보 없음.")
                else:
                    st.info("Stream B(EXCEPTION_LEADER) 후보 없음 — 시장에 surge 신호 부재.")

                st.divider()
                with st.expander("📋 기타 후보 (Top 5 외)", expanded=False):
                    _seen_tickers = {
                        str(r.get("ticker") or "") for r in (_archive_stream_a + _archive_stream_b)
                    }
                    _other_records = [
                        r for r in _archive_records
                        if str(r.get("ticker") or "") not in _seen_tickers
                    ]
                    _archive_other_rows = build_signal_display_rows(_other_records)
                    if _archive_other_rows:
                        _render_signal_card_list(_archive_other_rows)
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
