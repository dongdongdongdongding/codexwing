from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import streamlit as st

from ui.components import section_intro


def load_latest_daily_summary(market: str) -> Dict[str, Any]:
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


def render_daily_ops_overview() -> None:
    section_intro(
        "Daily Pulse",
        "일일 성과 요약",
        "시장별 운영 상태와 수익률을 시장당 한 카드에 모아 빠르게 훑을 수 있게 정리했습니다. 전체 표는 아래 ‘성과측정 상세’ 에서 확인하세요.",
        ["KOSPI", "KOSDAQ", "NASDAQ", "AMEX"],
    )
    markets = ["KOSPI", "KOSDAQ", "NASDAQ", "AMEX"]
    cols = st.columns(len(markets))
    has_any = False
    for col, market in zip(cols, markets):
        payload = load_latest_daily_summary(market)
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
            picked_30m = return_metric(return_buckets, "picked", "30m")
            picked_1h = return_metric(return_buckets, "picked", "1h")
            picked_close = return_metric(return_buckets, "picked", "close")
            picked_close_n = int(return_metric(return_buckets, "picked", "close", field="samples"))
            picked_3d_win = return_metric(return_buckets, "picked", "3d", field="win_rate_pct")
            pending = int(outcomes.get("pending", 0) or 0)
            resolved = int(outcomes.get("resolved", 0) or 0)

            st.metric(
                "Runs",
                int(payload.get("total_runs", 0) or 0),
                delta=f"3D 승률 {picked_3d_win:+.0f}%" if picked_3d_win else None,
            )
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
                payload = load_latest_daily_summary(market)
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
                st.dataframe(pd.DataFrame(rows), width="stretch")
    else:
        st.caption("아직 시장별 일일 성과 요약이 생성되지 않았습니다.")


def return_metric(return_buckets: Dict[str, Any], bucket: str, horizon: str, field: str = "avg_return_pct") -> float:
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


def _load_json_safe(path_str: str) -> Dict[str, Any]:
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


__all__ = [
    "load_latest_daily_summary",
    "render_daily_ops_overview",
    "return_metric",
]
