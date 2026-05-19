from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import streamlit as st

from modules import db_manager


TOP_DEEP_SECTION_ORDER = {
    "KOSDAQ Ordered Shadow": -30,
    "KOSDAQ Low-loss Shadow": -20,
    "KOSDAQ Shadow": -20,
    "KOSPI Shadow": -10,
    "Top5": 0,
    "Exception Leader": 1,
}


def load_top_deep_reports(limit: int = 500) -> Tuple[List[Dict[str, Any]], str]:
    db_rows: List[Dict[str, Any]] = []
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
            db_rows = list(res.data or [])
    except Exception as exc:
        warning = str(exc)

    local_rows: List[Dict[str, Any]] = []
    report_dir = Path("runtime_state/reports/top_deep")
    if report_dir.exists():
        for path in sorted(report_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:100]:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, list):
                    local_rows.extend([row for row in payload if isinstance(row, dict)])
            except Exception:
                continue
    merged_by_key: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for row in list(db_rows or []) + list(local_rows or []):
        if not isinstance(row, dict):
            continue
        key = str(row.get("report_id") or "")
        if not key:
            key = f"{row.get('run_id') or ''}:{row.get('ticker') or ''}:{row.get('report_version') or ''}"
        if key and key in merged_by_key:
            existing = merged_by_key[key]
            for item_key, value in row.items():
                if item_key not in existing or existing.get(item_key) in (None, "", [], {}):
                    existing[item_key] = value
            continue
        if key:
            merged_by_key[key] = dict(row)
            order.append(key)
        else:
            fallback_key = f"__row_{len(order)}"
            merged_by_key[fallback_key] = dict(row)
            order.append(fallback_key)
    merged = [merged_by_key[key] for key in order]
    merged = sorted(
        merged,
        key=lambda row: str(row.get("generated_at") or row.get("created_at") or ""),
        reverse=True,
    )
    return merged[: int(limit or 500)], warning


def fmt_metric_pct(value: Any) -> str:
    if value in (None, ""):
        return "-"
    try:
        return f"{float(value):+.2f}%"
    except Exception:
        return "-"


def fmt_metric_num(value: Any, digits: int = 1) -> str:
    if value in (None, ""):
        return "-"
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "-"


def fmt_krw(value: Any) -> str:
    if value in (None, ""):
        return "-"
    try:
        return f"{float(value):,.0f}원"
    except Exception:
        return "-"


def fmt_flow_oku(value: Any) -> str:
    if value in (None, ""):
        return "-"
    try:
        numeric = float(value)
        if abs(numeric) >= 100000000:
            return f"{numeric / 100000000:+.1f}억"
        return f"{numeric:+,.0f}"
    except Exception:
        return "-"


def fmt_flow_value(value: Any, unit: Any = None) -> str:
    if value in (None, ""):
        return "-"
    unit_key = str(unit or "").lower()
    if unit_key == "krw":
        return fmt_flow_oku(value)
    try:
        numeric = float(value)
        suffix = "주" if unit_key == "shares" else ""
        return f"{numeric:+,.0f}{suffix}"
    except Exception:
        return "-"


def fmt_flow_leader_caption(flow: Dict[str, Any]) -> str | None:
    if not isinstance(flow, dict):
        return None
    unit = flow.get("flow_unit")
    window = str(flow.get("flow_window") or "").lower()
    primary_label = "당일 외인+기관" if window in {"1d", "day"} else "외인+기관"
    parts: List[str] = []
    flow_asof = flow.get("flow_asof")
    if flow_asof:
        parts.append(f"기준일: {flow_asof}")
    if flow.get("whale_flow_1d") is not None or flow.get("whale_flow") is not None:
        parts.append(f"{primary_label}: {fmt_flow_value(flow.get('whale_flow_1d', flow.get('whale_flow')), unit)}")
    if flow.get("whale_flow_3d") is not None:
        parts.append(f"3일 외인+기관: {fmt_flow_value(flow.get('whale_flow_3d'), unit)}")
    if flow.get("whale_flow_10d") is not None:
        parts.append(f"10일 외인+기관: {fmt_flow_value(flow.get('whale_flow_10d'), unit)}")
    return " · ".join(parts) if parts else None


def infer_top_deep_market(row: Dict[str, Any]) -> str:
    market = str(row.get("market") or "").upper()
    if market:
        return market
    ticker = str(row.get("ticker") or "").upper()
    if ticker.endswith(".KQ"):
        return "KOSDAQ"
    if ticker.endswith(".KS"):
        return "KOSPI"
    return "UNKNOWN"


def scan_display_label(run_df: pd.DataFrame) -> str:
    if run_df is None or run_df.empty:
        return "-"
    run_id = str(run_df["run_id"].dropna().iloc[0]) if "run_id" in run_df and not run_df["run_id"].dropna().empty else "-"
    market = str(run_df["_market"].dropna().iloc[0]) if "_market" in run_df and not run_df["_market"].dropna().empty else "-"
    generated = pd.to_datetime(run_df.get("generated_at"), errors="coerce", utc=True)
    generated = generated.dropna()
    if not generated.empty:
        ts = generated.max().tz_convert("Asia/Seoul").strftime("%Y-%m-%d %H:%M")
        return f"{ts} · {market} · {len(run_df)}건 · {run_id}"
    return f"{market} · {len(run_df)}건 · {run_id}"


def top_deep_section_order(value: Dict[str, Any]) -> int:
    if isinstance(value, dict):
        return TOP_DEEP_SECTION_ORDER.get(str(value.get("analysis_section") or "Top5"), 0)
    return 0


def top_deep_section_rank(value: Dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return value.get("analysis_section_rank")
    return None


def top_deep_section_name(value: Dict[str, Any]) -> str:
    if isinstance(value, dict):
        return str(value.get("analysis_section") or "Top5")
    return "Top5"


def _readiness_score_card(title: str, block: Dict[str, Any]) -> None:
    block = block if isinstance(block, dict) else {}
    score = block.get("score")
    grade = str(block.get("grade") or "-")
    value = f"{grade} · {fmt_metric_num(score, 0)}"
    st.metric(title, value)
    try:
        st.progress(max(0, min(100, int(float(score)))))
    except Exception:
        st.progress(0)
    evidence = block.get("evidence") if isinstance(block.get("evidence"), list) else []
    if evidence:
        st.caption(" / ".join(str(x) for x in evidence[:2]))


def render_readiness_analysis(readiness: Dict[str, Any]) -> None:
    if not isinstance(readiness, dict) or not readiness:
        return
    judgment = readiness.get("final_buy_judgment") if isinstance(readiness.get("final_buy_judgment"), dict) else {}
    action = str(judgment.get("action") or "-")
    summary = str(judgment.get("summary") or "")
    tone = str(judgment.get("tone") or "neutral")
    if tone == "danger":
        st.error(f"매수 판단: {action} · {summary}")
    elif tone == "risk":
        st.warning(f"매수 판단: {action} · {summary}")
    elif tone in {"good", "focus"}:
        st.success(f"매수 판단: {action} · {summary}")
    else:
        st.info(f"매수 판단: {action} · {summary}")

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        _readiness_score_card("종목 품질", readiness.get("quality"))
    with s2:
        _readiness_score_card("상승 여력", readiness.get("upside"))
    with s3:
        _readiness_score_card("진입 타이밍", readiness.get("timing"))
    with s4:
        st.metric("추격 위험", str(readiness.get("chase_risk_level") or "-"))
        plan = readiness.get("trade_plan_summary") if isinstance(readiness.get("trade_plan_summary"), dict) else {}
        st.caption(
            f"Entry {plan.get('entry_policy') or '-'} · "
            f"TP {fmt_metric_pct(plan.get('target_tp_pct'))} · "
            f"SL {fmt_metric_pct(plan.get('stop_sl_pct'))}"
        )

    upside = readiness.get("upside") if isinstance(readiness.get("upside"), dict) else {}
    filters = upside.get("filters") if isinstance(upside.get("filters"), list) else []
    if filters:
        filter_rows = []
        for item in filters:
            if not isinstance(item, dict):
                continue
            filter_rows.append(
                {
                    "필터": item.get("label"),
                    "현재값": item.get("value"),
                    "판정": "위험" if item.get("triggered") else "통과",
                    "강도": item.get("severity"),
                }
            )
        if filter_rows:
            st.dataframe(pd.DataFrame(filter_rows), use_container_width=True, hide_index=True)

    warnings = readiness.get("warnings") if isinstance(readiness.get("warnings"), list) else []
    if warnings:
        st.caption("판정 경고: " + " / ".join(str(x) for x in warnings[:5]))


def render_data_backed_action_plan(trade_plan: Dict[str, Any], readiness: Dict[str, Any]) -> None:
    trade_plan = trade_plan if isinstance(trade_plan, dict) else {}
    readiness = readiness if isinstance(readiness, dict) else {}
    execution_stop = trade_plan.get("execution_stop") if isinstance(trade_plan.get("execution_stop"), dict) else {}
    entry = trade_plan.get("entry_strategy") if isinstance(trade_plan.get("entry_strategy"), dict) else {}
    if not entry:
        entry = readiness.get("entry_strategy") if isinstance(readiness.get("entry_strategy"), dict) else {}
    risk = trade_plan.get("risk_management") if isinstance(trade_plan.get("risk_management"), dict) else {}
    if not risk:
        risk = readiness.get("risk_management") if isinstance(readiness.get("risk_management"), dict) else {}
    coverage = trade_plan.get("data_coverage") if isinstance(trade_plan.get("data_coverage"), dict) else {}
    if not coverage:
        coverage = readiness.get("data_coverage") if isinstance(readiness.get("data_coverage"), dict) else {}
    if not entry and not risk:
        return

    st.markdown("**데이터 기반 액션 플랜**")
    a1, a2 = st.columns(2)
    with a1:
        st.info(str(entry.get("primary_condition") or "-"))
        st.caption("보조 조건: " + str(entry.get("secondary_condition") or "-"))
        if entry.get("blocked_reason"):
            st.caption("차단 사유: " + str(entry.get("blocked_reason")))
    with a2:
        stop_text = str(risk.get("stop_condition") or "-")
        target_text = fmt_krw(risk.get("target_price"))
        rr_text = fmt_metric_num(risk.get("risk_reward"), 2)
        st.warning(f"손절 조건: {stop_text}")
        st.caption(f"목표가 {target_text} · 손익비 {rr_text} · 손실위험 {fmt_metric_num(risk.get('loss_risk_score'), 1)}")

    l1, l2, l3, l4 = st.columns(4)
    l1.metric("눌림 지지", fmt_krw(entry.get("pullback_support_price")), str(entry.get("pullback_support_label") or "-"))
    l2.metric("돌파 확인", fmt_krw(entry.get("breakout_price")), str(entry.get("breakout_label") or "-"))
    l3.metric("무효화", fmt_krw(execution_stop.get("display_stop_price") or risk.get("stop_price")))
    l4.metric("데이터 커버리지", f"{fmt_metric_num(coverage.get('coverage_pct'), 0)}%")

    evidence = entry.get("evidence") if isinstance(entry.get("evidence"), list) else []
    if evidence:
        st.caption("액션 산출 근거: " + " / ".join(str(x) for x in evidence[:5]))
    risk_warnings = risk.get("warnings") if isinstance(risk.get("warnings"), list) else []
    if risk_warnings:
        st.caption("액션 플랜 경고: " + " / ".join(str(x) for x in risk_warnings[:4]))


def render_selection_thesis(row: Dict[str, Any], trade_plan: Dict[str, Any]) -> None:
    row = row if isinstance(row, dict) else {}
    trade_plan = trade_plan if isinstance(trade_plan, dict) else {}
    thesis = row.get("selection_thesis") if isinstance(row.get("selection_thesis"), dict) else {}
    if not thesis:
        thesis = trade_plan.get("selection_thesis") if isinstance(trade_plan.get("selection_thesis"), dict) else {}
    overrides = row.get("risk_overrides") if isinstance(row.get("risk_overrides"), dict) else {}
    if not overrides:
        overrides = trade_plan.get("risk_overrides") if isinstance(trade_plan.get("risk_overrides"), dict) else {}
    if not thesis and not overrides:
        return

    st.markdown("**스캔 선정 논리와 리스크 재판정**")
    left, right = st.columns(2)
    with left:
        st.success(str(thesis.get("summary") or "-"))
        basis = thesis.get("scanner_basis") if isinstance(thesis.get("scanner_basis"), dict) else {}
        b1, b2, b3 = st.columns(3)
        b1.metric("원본 점수", fmt_metric_num(basis.get("raw_decision_score"), 1))
        b2.metric("상대순위", fmt_metric_num(basis.get("relative_rank_score"), 1))
        b3.metric("기대엣지", fmt_metric_num(basis.get("expected_edge_score"), 1))
        reasons = thesis.get("selection_reasons") if isinstance(thesis.get("selection_reasons"), list) else []
        if reasons:
            st.caption("선정 근거: " + " / ".join(str(x) for x in reasons[:5]))
    with right:
        severity = str(overrides.get("severity") or "none")
        if severity == "hard":
            st.error("리스크 재판정: hard override")
        elif severity == "soft":
            st.warning("리스크 재판정: soft override")
        else:
            st.info("리스크 재판정: override 없음")
        flags = overrides.get("planner_risk_flags") if isinstance(overrides.get("planner_risk_flags"), list) else []
        triggered = overrides.get("triggered_chase_filters") if isinstance(overrides.get("triggered_chase_filters"), list) else []
        if triggered:
            labels = [str(item.get("label") or item.get("code")) for item in triggered if isinstance(item, dict)]
            st.caption("추격 필터: " + " / ".join(labels[:4]))
        if flags:
            st.caption("플래너 리스크: " + " / ".join(str(x) for x in flags[:5]))


__all__ = [
    "TOP_DEEP_SECTION_ORDER",
    "fmt_flow_leader_caption",
    "fmt_flow_oku",
    "fmt_flow_value",
    "fmt_krw",
    "fmt_metric_num",
    "fmt_metric_pct",
    "infer_top_deep_market",
    "load_top_deep_reports",
    "render_data_backed_action_plan",
    "render_readiness_analysis",
    "render_selection_thesis",
    "scan_display_label",
    "top_deep_section_name",
    "top_deep_section_order",
    "top_deep_section_rank",
]
