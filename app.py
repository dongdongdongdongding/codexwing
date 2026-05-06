import warnings
# Suppress Google Auth Python 3.9 Deprecation & urllib3 LibreSSL warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.auth")
warnings.filterwarnings("ignore", category=FutureWarning, module="google.oauth2")
warnings.filterwarnings("ignore", module="urllib3")

import concurrent.futures
import html
import json
import threading
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
from modules.macro_scheduler import get_macro_context
from modules.scanner_bridge import run_legacy_agent_bridge
from modules.scanner_runtime import SharedBackoffState, run_parallel_scan, scan_symbol_with_retry
from modules.scanner_services import evaluate_uploaded_candidate, normalize_uploaded_ticker
from modules.scan_policy import (
    compute_market_gate as compute_market_gate_live,
    compute_rank_adjustment as shared_compute_rank_adjustment,
)
from modules.theme_data_pipeline import build_theme_distribution_summary
from modules.ui_helpers import (
    BackgroundScanState,
    build_top_candidate_rows,
    build_watchlist_display_rows,
    compute_progress_fraction,
    format_volume_display,
    resolve_display_price,
    should_auto_refresh_scan_panel,
)
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import traceback

# [Phase 8] Global Backoff Synchronization for Rate Limits
_SCAN_BACKOFF_STATE = SharedBackoffState()

st.set_page_config(
    page_title="스윙 트레이딩 AI",
    layout="wide",
    page_icon="📈",
    initial_sidebar_state="collapsed",
)

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


def _inject_toss_theme():
    st.markdown(
        """
        <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

        :root {
          --bg: #f2f4f6;
          --surface: rgba(255, 255, 255, 0.94);
          --surface-strong: #ffffff;
          --surface-soft: #f8fafc;
          --line: #e5e8eb;
          --text: #191f28;
          --muted: #8b95a1;
          --primary: #3182f6;
          --primary-deep: #1b64da;
          --primary-soft: #eaf2ff;
          --good: #17b26a;
          --warn: #ffb020;
          --danger: #f04452;
          --shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
        }

        html, body, [class*="css"] {
          font-family: "Pretendard", "SUIT Variable", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
        }

        .stApp {
          background:
            radial-gradient(circle at top left, rgba(49, 130, 246, 0.10), transparent 28%),
            radial-gradient(circle at top right, rgba(35, 180, 120, 0.08), transparent 24%),
            linear-gradient(180deg, #f8fbff 0%, var(--bg) 18%, #eef2f6 100%);
          color: var(--text);
        }

        [data-testid="stHeader"] {
          background: rgba(248, 251, 255, 0.75);
          backdrop-filter: blur(14px);
        }

        .block-container {
          max-width: 1380px;
          padding-top: 1.6rem;
          padding-bottom: 3rem;
        }

        [data-testid="stSidebar"] {
          background: linear-gradient(180deg, #fbfdff 0%, #f4f7fb 100%);
          border-right: 1px solid rgba(229, 232, 235, 0.9);
        }

        [data-testid="collapsedControl"] {
          display: none;
        }

        h1, h2, h3, h4 {
          color: var(--text);
          letter-spacing: -0.03em;
        }

        p, li, label, .stCaption, .stMarkdown {
          color: var(--text);
        }

        div[data-testid="stMetric"] {
          background: var(--surface);
          border: 1px solid rgba(229, 232, 235, 0.92);
          border-radius: 22px;
          padding: 1rem 1.05rem;
          box-shadow: var(--shadow);
        }

        div[data-testid="stMetricLabel"] {
          color: var(--muted);
          font-weight: 600;
        }

        div[data-testid="stMetricValue"] {
          color: var(--text);
          letter-spacing: -0.03em;
        }

        div[data-baseweb="select"] > div,
        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input {
          background: rgba(255, 255, 255, 0.96);
          border: 1px solid var(--line);
          border-radius: 16px;
          min-height: 3rem;
        }

        div[data-baseweb="select"] > div:focus-within,
        .stTextInput input:focus,
        .stTextArea textarea:focus,
        .stNumberInput input:focus {
          border-color: rgba(49, 130, 246, 0.9);
          box-shadow: 0 0 0 4px rgba(49, 130, 246, 0.14);
        }

        .stButton > button,
        button[kind="primary"] {
          border-radius: 16px;
          min-height: 3rem;
          font-weight: 700;
          letter-spacing: -0.02em;
          transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
        }

        .stButton > button:hover,
        button[kind="primary"]:hover {
          transform: translateY(-1px);
          box-shadow: 0 14px 30px rgba(49, 130, 246, 0.18);
        }

        button[kind="primary"] {
          background: linear-gradient(135deg, var(--primary) 0%, var(--primary-deep) 100%);
          border: 0;
        }

        .stButton > button {
          background: rgba(255, 255, 255, 0.98);
          border: 1px solid var(--line);
          color: var(--text);
        }

        .stButton > button:hover {
          border-color: rgba(49, 130, 246, 0.45);
          color: var(--primary-deep);
        }

        div[data-testid="stTabs"] {
          margin-top: 0.75rem;
        }

        div[data-testid="stTabs"] button[role="tab"] {
          border-radius: 999px;
          border: 1px solid transparent;
          background: rgba(255, 255, 255, 0.72);
          color: var(--muted);
          font-weight: 700;
          padding: 0.8rem 1.15rem;
        }

        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
          background: #ffffff;
          color: var(--primary-deep);
          border-color: rgba(49, 130, 246, 0.18);
          box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
        }

        div[data-testid="stExpander"] {
          border: 1px solid var(--line);
          border-radius: 22px;
          background: var(--surface);
          box-shadow: var(--shadow);
          overflow: hidden;
        }

        div[data-testid="stDataFrame"],
        div[data-testid="stTable"] {
          border: 1px solid var(--line);
          border-radius: 22px;
          overflow: hidden;
          background: var(--surface-strong);
          box-shadow: var(--shadow);
        }

        .section-intro,
        .status-banner,
        .control-note {
          border: 1px solid rgba(229, 232, 235, 0.92);
          box-shadow: var(--shadow);
        }

        .section-kicker {
          color: var(--primary-deep);
          font-weight: 800;
          font-size: 0.82rem;
          letter-spacing: 0.06em;
          text-transform: uppercase;
        }

        .section-title {
          color: var(--text);
          font-weight: 800;
          letter-spacing: -0.04em;
          line-height: 1.08;
        }

        .section-title {
          margin: 0.28rem 0 0.55rem;
          font-size: clamp(1.45rem, 1.8vw, 2rem);
        }

        .section-body,
        .status-body,
        .status-caption {
          color: var(--muted);
          line-height: 1.65;
        }

        .section-chip-row {
          display: flex;
          flex-wrap: wrap;
          gap: 0.55rem;
          margin-top: 1rem;
        }

        .section-chip {
          padding: 0.5rem 0.82rem;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.88);
          border: 1px solid rgba(49, 130, 246, 0.12);
          color: var(--primary-deep);
          font-size: 0.88rem;
          font-weight: 700;
        }

        .section-intro {
          padding: 1.2rem 1.25rem;
          margin: 0.35rem 0 1rem;
          border-radius: 26px;
          background: rgba(255, 255, 255, 0.9);
        }

        .status-banner {
          padding: 1rem 1.15rem;
          margin: 0.5rem 0 0.85rem;
          border-radius: 24px;
          background: rgba(255, 255, 255, 0.92);
        }

        .status-banner.good {
          background: linear-gradient(135deg, rgba(236, 251, 243, 0.96), rgba(255, 255, 255, 0.95));
          border-color: rgba(23, 178, 106, 0.2);
        }

        .status-banner.caution {
          background: linear-gradient(135deg, rgba(255, 248, 230, 0.96), rgba(255, 255, 255, 0.95));
          border-color: rgba(255, 176, 32, 0.24);
        }

        .status-banner.risk,
        .status-banner.danger {
          background: linear-gradient(135deg, rgba(255, 241, 242, 0.97), rgba(255, 255, 255, 0.95));
          border-color: rgba(240, 68, 82, 0.2);
        }

        .status-title {
          color: var(--text);
          font-size: 1rem;
          font-weight: 800;
          letter-spacing: -0.03em;
          margin-bottom: 0.25rem;
        }

        .control-note {
          padding: 0.95rem 1.1rem;
          margin: 0.2rem 0 1rem;
          border-radius: 22px;
          background: rgba(255, 255, 255, 0.84);
        }

        .control-note strong {
          display: block;
          color: var(--text);
          margin-bottom: 0.2rem;
        }

        .control-note span {
          color: var(--muted);
          line-height: 1.6;
        }

        .intel-highlight-list {
          display: grid;
          gap: 0.7rem;
          margin: 0.55rem 0 1rem;
        }

        .intel-highlight-item {
          display: flex;
          gap: 0.7rem;
          align-items: flex-start;
          padding: 0.9rem 1rem;
          border-radius: 20px;
          background: rgba(255, 255, 255, 0.88);
          border: 1px solid rgba(229, 232, 235, 0.9);
          box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
        }

        .intel-highlight-badge {
          flex-shrink: 0;
          min-width: 4.1rem;
          padding: 0.25rem 0.6rem;
          border-radius: 999px;
          background: rgba(49, 130, 246, 0.1);
          color: var(--primary-deep);
          font-size: 0.78rem;
          font-weight: 700;
          text-align: center;
        }

        .intel-highlight-text {
          color: var(--text);
          line-height: 1.55;
          font-size: 0.95rem;
        }

        .intel-theme-card {
          padding: 1rem 1.05rem;
          margin-bottom: 0.8rem;
          border-radius: 22px;
          background: rgba(255, 255, 255, 0.92);
          border: 1px solid rgba(229, 232, 235, 0.92);
          box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
        }

        .intel-theme-card.good {
          background: linear-gradient(135deg, rgba(236, 251, 243, 0.98), rgba(255, 255, 255, 0.96));
          border-color: rgba(23, 178, 106, 0.18);
        }

        .intel-theme-card.risk {
          background: linear-gradient(135deg, rgba(255, 241, 242, 0.98), rgba(255, 255, 255, 0.96));
          border-color: rgba(240, 68, 82, 0.18);
        }

        .intel-theme-card.neutral {
          background: linear-gradient(135deg, rgba(246, 248, 251, 0.98), rgba(255, 255, 255, 0.96));
          border-color: rgba(139, 149, 161, 0.18);
        }

        .intel-theme-head {
          display: flex;
          justify-content: space-between;
          gap: 0.8rem;
          align-items: center;
          margin-bottom: 0.45rem;
        }

        .intel-theme-name {
          color: var(--text);
          font-size: 1rem;
          font-weight: 800;
          letter-spacing: -0.03em;
        }

        .intel-theme-badge {
          flex-shrink: 0;
          border-radius: 999px;
          padding: 0.28rem 0.7rem;
          font-size: 0.78rem;
          font-weight: 800;
        }

        .intel-theme-badge.good {
          background: rgba(23, 178, 106, 0.12);
          color: #118653;
        }

        .intel-theme-badge.risk {
          background: rgba(240, 68, 82, 0.12);
          color: #c2313d;
        }

        .intel-theme-badge.neutral {
          background: rgba(139, 149, 161, 0.14);
          color: #5f6b76;
        }

        .intel-theme-meta {
          color: var(--muted);
          font-size: 0.88rem;
          line-height: 1.55;
        }

        .intel-theme-evidence {
          margin-top: 0.65rem;
          color: var(--text);
          font-size: 0.9rem;
          line-height: 1.55;
        }

        .intel-theme-evidence strong {
          color: var(--primary-deep);
          margin-right: 0.3rem;
        }

        .intel-subtle-card {
          padding: 0.95rem 1rem;
          margin-bottom: 0.75rem;
          border-radius: 20px;
          background: rgba(255, 255, 255, 0.84);
          border: 1px solid rgba(229, 232, 235, 0.92);
        }

        .intel-subtle-card strong {
          display: block;
          color: var(--text);
          margin-bottom: 0.3rem;
        }

        .intel-subtle-card span {
          color: var(--muted);
          line-height: 1.55;
        }

        .top-intel-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 0.9rem;
          margin: 0.45rem 0 1rem;
        }

        .top-intel-card {
          padding: 1rem 1.05rem;
          border-radius: 22px;
          background: rgba(255, 255, 255, 0.9);
          border: 1px solid rgba(229, 232, 235, 0.92);
          box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
        }

        .top-intel-kicker {
          color: var(--muted);
          font-size: 0.78rem;
          font-weight: 700;
          margin-bottom: 0.3rem;
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }

        .top-intel-title {
          color: var(--text);
          font-size: 1.02rem;
          font-weight: 800;
          letter-spacing: -0.03em;
          margin-bottom: 0.35rem;
        }

        .top-intel-body {
          color: var(--text);
          font-size: 0.94rem;
          line-height: 1.6;
        }

        .top-intel-meta {
          color: var(--muted);
          font-size: 0.84rem;
          line-height: 1.55;
          margin-top: 0.5rem;
        }

        .intel-overview-shell {
          margin: 0.55rem 0 1rem;
        }

        .intel-scoreline {
          color: var(--text);
          font-size: 1.05rem;
          font-weight: 800;
          letter-spacing: -0.03em;
          margin-bottom: 0.7rem;
        }

        .intel-scoreline .muted {
          color: var(--muted);
          font-weight: 700;
        }

        .intel-insight-box {
          padding: 1rem 1.1rem;
          margin-bottom: 0.9rem;
          border-radius: 22px;
          background: rgba(255, 255, 255, 0.92);
          border: 1px solid rgba(229, 232, 235, 0.92);
          box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
          color: var(--text);
          line-height: 1.65;
        }

        .intel-signal-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 0.9rem;
          margin: 0.6rem 0 1rem;
        }

        .intel-signal-card {
          padding: 1rem 1.05rem;
          border-radius: 22px;
          border: 1px solid rgba(229, 232, 235, 0.92);
          box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
        }

        .intel-signal-card.good {
          background: linear-gradient(135deg, rgba(236, 251, 243, 0.98), rgba(255, 255, 255, 0.96));
          border-color: rgba(23, 178, 106, 0.18);
        }

        .intel-signal-card.risk {
          background: linear-gradient(135deg, rgba(255, 241, 242, 0.98), rgba(255, 255, 255, 0.96));
          border-color: rgba(240, 68, 82, 0.18);
        }

        .intel-signal-card.focus {
          background: linear-gradient(135deg, rgba(239, 246, 255, 0.98), rgba(255, 255, 255, 0.96));
          border-color: rgba(49, 130, 246, 0.18);
        }

        .intel-signal-title {
          color: var(--muted);
          font-size: 0.8rem;
          font-weight: 700;
          margin-bottom: 0.35rem;
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }

        .intel-signal-body {
          color: var(--text);
          font-size: 1rem;
          font-weight: 800;
          line-height: 1.55;
        }

        .intel-signal-meta {
          margin-top: 0.35rem;
          color: var(--muted);
          font-size: 0.86rem;
          line-height: 1.55;
        }

        .intel-momentum-grid {
          display: grid;
          grid-template-columns: repeat(5, minmax(0, 1fr));
          gap: 0.9rem;
          margin: 0.85rem 0 1rem;
        }

        .intel-momentum-card {
          padding: 1rem 1.05rem;
          border-radius: 22px;
          background: rgba(255, 255, 255, 0.92);
          border: 1px solid rgba(229, 232, 235, 0.92);
          box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
        }

        .intel-momentum-rank {
          color: var(--muted);
          font-size: 0.86rem;
          font-weight: 700;
          margin-bottom: 0.35rem;
        }

        .intel-momentum-theme {
          color: var(--text);
          font-size: 0.98rem;
          font-weight: 800;
          letter-spacing: -0.03em;
          min-height: 2.4rem;
        }

        .intel-momentum-return {
          color: var(--text);
          font-size: 1.85rem;
          font-weight: 800;
          letter-spacing: -0.05em;
          margin: 0.35rem 0 0.55rem;
        }

        .intel-momentum-return.pos { color: #118653; }
        .intel-momentum-return.neg { color: #c2313d; }
        .intel-momentum-return.neu { color: var(--text); }

        .intel-momentum-chip {
          display: inline-flex;
          align-items: center;
          padding: 0.28rem 0.7rem;
          border-radius: 999px;
          background: rgba(23, 178, 106, 0.1);
          color: #118653;
          font-size: 0.82rem;
          font-weight: 700;
        }

        .intel-momentum-meta {
          margin-top: 0.55rem;
          color: var(--muted);
          font-size: 0.85rem;
          line-height: 1.55;
        }

        .intel-catalyst-list {
          display: grid;
          gap: 0.7rem;
          margin: 0.65rem 0 0.9rem;
        }

        .intel-catalyst-item {
          padding: 0.95rem 1rem;
          border-radius: 20px;
          background: rgba(255, 255, 255, 0.88);
          border: 1px solid rgba(229, 232, 235, 0.92);
          color: var(--text);
          line-height: 1.6;
        }

        .intel-headline-list {
          display: grid;
          gap: 0.7rem;
          margin: 0.65rem 0 0.8rem;
        }

        .intel-headline-item {
          padding: 0.95rem 1rem;
          border-radius: 18px;
          background: rgba(255, 255, 255, 0.84);
          border: 1px solid rgba(229, 232, 235, 0.92);
          color: var(--text);
          line-height: 1.6;
        }

        @media (max-width: 980px) {
          .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
          }

          .section-intro,
          .status-banner,
          .control-note,
          .top-intel-card,
          div[data-testid="stMetric"],
          div[data-testid="stExpander"],
          div[data-testid="stDataFrame"],
          div[data-testid="stTable"] {
            border-radius: 20px;
          }

          .top-intel-grid {
            grid-template-columns: 1fr;
          }

          .intel-signal-grid,
          .intel-momentum-grid {
            grid-template-columns: 1fr;
          }

          div[data-testid="stTabs"] button[role="tab"] {
            padding: 0.72rem 0.92rem;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
        "시장별 운영 상태와 수익률 측정값을 카드로 빠르게 훑을 수 있게 정리한 영역입니다.",
        ["KOSPI", "KOSDAQ", "NASDAQ", "AMEX"],
    )
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


def _render_scan_top_candidates(results_df, bridge_info, market):
    planner_payload = _load_json_safe(bridge_info.get("planner_handoff")) if isinstance(bridge_info, dict) else {}
    top_rows = build_top_candidate_rows(planner_payload, limit=5)

    st.markdown("### 🔥 Top 5 매수 신호")
    if top_rows:
        st.caption(
            "BUY/WATCHLIST 등급만 표시합니다. OBSERVE/AVOID는 매매 신호가 아니므로 제외됩니다. "
            "Entry/TP/SL은 시장별 정책 (KOSPI 시가/+20/-5, KOSDAQ -2%limit/+10/-10) 입니다."
        )
        top_df = _coerce_numeric_display(
            pd.DataFrame(top_rows),
            ["Model Prob", "Gate Thr", "OOS Win %", "OOS Ret %"],
        )
        st.dataframe(top_df, use_container_width=True, hide_index=True)
        return

    st.info(
        "현재 매수 신호 없음 — 시장 관망. 모든 후보가 OBSERVE/AVOID로 강등되었거나 "
        "OOS 검증을 통과하지 못했습니다. Watchlist 표에서 감시 종목을 확인하세요."
    )


def _get_scan_state_snapshot():
    state = st.session_state.get("scan_job_state")
    if state is None:
        return None
    return state.snapshot()


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
            st.dataframe(df_results.iloc[5:], use_container_width=True, hide_index=True)
    else:
        st.dataframe(df_results, use_container_width=True, hide_index=True)
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
refresh_macro_clicked, refresh_gate_clicked = _render_main_controls()
st.markdown("---")

with st.expander("보조 도구 · 차트 이미지 분석", expanded=False):
    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        help="차트 이미지 Vision 분석을 사용할 때만 필요합니다.",
        key="main_openai_api_key",
    )
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    st.caption("이미지 기반 보조 분석 전용 설정입니다. 스캐너와 엔진 로직에는 영향을 주지 않습니다.")
    uploaded_file = st.file_uploader("Upload Chart", type=["jpg", "png", "jpeg"], key="main_chart_upload")
    if uploaded_file is not None and api_key:
        st.image(uploaded_file, caption="Uploaded Chart", width='stretch')
        if st.button("Analyze Image", key="main_image_analyze"):
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
if 'macro_ctx' not in st.session_state or refresh_macro_clicked:
    with st.spinner("📡 실시간 매크로 지표 수집 중..."):
        try:
            st.session_state['macro_ctx'] = get_macro_context(force_refresh=True)
        except Exception as _e:
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
_render_status_banner(f"{_ico} Macro Weather · {macro_state}", macro_body, tone=macro_tone, caption=macro_note)

# --- Phase 25: Market Gate (KOSPI/KOSDAQ Daily Gate) ---
# Backtest proved: bad market days have 3~33% win rate → must warn users
_selected_gate_market = st.session_state.get("selected_scan_market", "KOSPI")
if (
    'market_gate' not in st.session_state
    or str(st.session_state.get('market_gate', {}).get('selected_market', '')).upper() != str(_selected_gate_market).upper()
):
    st.session_state['market_gate'] = compute_market_gate(_selected_gate_market)
_gate_info = st.session_state['market_gate']
if refresh_gate_clicked:
    st.session_state['market_gate'] = compute_market_gate(st.session_state.get("selected_scan_market", "KOSPI"))
    _gate_info = st.session_state['market_gate']
_render_status_banner(
    f"📡 Market Gate · {_gate_info['gate']}",
    _gate_info['msg'],
    tone={"GREEN": "good", "YELLOW": "caution", "RED": "danger"}.get(_gate_info["gate"], "good"),
    caption=f"선택 시장: {_selected_gate_market}",
)

_top_summary_market = st.session_state.get("selected_scan_market", "KOSPI")
_top_snapshot = _get_scan_state_snapshot()
if (
    _top_snapshot
    and _scan_is_running(_top_snapshot)
    and str(_top_snapshot.get("market", "") or "").upper() == str(_top_summary_market).upper()
    and isinstance(_top_snapshot.get("intel_data"), dict)
    and _top_snapshot.get("intel_data")
):
    _top_intel_data = dict(_top_snapshot.get("intel_data", {}))
    _top_intel_data["_display_origin"] = "scan_snapshot"
else:
    _top_intel_data = market_intelligence.get_market_intelligence(
        _top_summary_market,
        os.environ.get("GEMINI_API_KEY", ""),
        force_refresh=False,
    )
_render_top_intelligence_summary(_top_summary_market, _top_intel_data)

MAIN_TABS = ["🚀 스캐너", "🧠 인텔리전스", "📈 성과", "📚 아카이브", "🔎 정밀분석"]
if "active_main_tab" not in st.session_state:
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

if active_main_tab == "🧠 인텔리전스":
    _render_intelligence_workspace()

# --- Strategy Lab (removed from UI) ---
if active_main_tab == "🚀 스캐너":  # dummy context reuse — strategy lab content removed
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
if active_main_tab == "🚀 스캐너":
    _render_section_intro(
        "Scanner",
        "전종목 자동 스캔",
        "시장, 스캔 모드, 엔진을 빠르게 고른 뒤 상위 후보를 바로 읽을 수 있도록 진입 화면을 단순화했습니다.",
        ["Top 5 focus", "Market-aware gate", "Shared trace output"],
    )
    st.markdown(
        """
        <div class="control-note">
          <strong>빠른 사용 흐름</strong>
          <span>시장과 모드를 먼저 고르고, 엔진을 확인한 뒤 스캔을 실행하세요. 결과는 Top 5 후보와 추가 후보로 바로 나뉘어 보여집니다.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
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
    
    start_scan = st.button(
        "시장 스캔 시작",
        type="primary",
        disabled=_scan_is_running(),
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
