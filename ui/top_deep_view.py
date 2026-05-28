from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import streamlit as st

from modules import db_manager
from modules.portfolio_exposure import build_portfolio_exposure_summary, render_portfolio_exposure_lines
from ui.scan_integrity_view import (
    load_scan_context_for_run,
    render_scan_integrity_panel,
    scan_integrity_report_for_context,
)
from ui.view_chrome import render_section_intro


TOP_DEEP_SECTION_ORDER = {
    "KOSPI Operating Challenger": -150,
    "KOSDAQ Operating Challenger": -140,
    "Practical 80 Gate": -100,
    "KOSDAQ Ordered Shadow": -30,
    "KOSDAQ Theme Rank Shadow": -25,
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


def render_top_deep_reports_page() -> None:
    render_section_intro(
        "Top Deep Reports",
        "Challenger + Practical + Shadow + Top5 + Exception 자동 정밀분석",
        "운영 챌린저와 Practical 80 Gate 후보를 최상단에 분리하고, Shadow/Top5/Exception을 같은 기준으로 분석합니다.",
        ["Challenger first", "Practical next", "Shadow watch", "Top5 audit", "Real data only"],
    )
    rows, warning = load_top_deep_reports()
    if warning:
        st.warning(f"Supabase 조회 실패 또는 제한: {warning}. 로컬 리포트가 있으면 대체 표시합니다.")
    if not rows:
        st.info("아직 생성된 Top 정밀분석 리포트가 없습니다. 스캔을 1회 완료하면 자동 생성됩니다.")
        return

    df = pd.DataFrame(rows)
    df["generated_at_dt"] = pd.to_datetime(df.get("generated_at"), errors="coerce", utc=True)
    df["report_date"] = df["generated_at_dt"].dt.tz_convert("Asia/Seoul").dt.date
    df["_market"] = df.apply(infer_top_deep_market, axis=1)
    market_options = [m for m in ["KOSPI", "KOSDAQ"] if m in set(df["_market"].dropna().astype(str))]
    extra_markets = sorted([m for m in set(df["_market"].dropna().astype(str)) if m not in {"KOSPI", "KOSDAQ"}])
    market_options.extend(extra_markets)
    if not market_options:
        market_options = ["전체"]
    col_market, col_date, col_run, col_size = st.columns([1.2, 1.3, 2.8, 1])
    selected_market = col_market.selectbox("시장", market_options, index=0)
    market_df = df if selected_market == "전체" else df[df["_market"] == selected_market].copy()
    dates = sorted([d for d in market_df["report_date"].dropna().unique()], reverse=True)
    if not dates:
        st.info(f"{selected_market} 정밀분석 리포트가 없습니다.")
        return
    selected_date = col_date.selectbox("날짜", dates, index=0)
    day_df = market_df[market_df["report_date"] == selected_date].copy()
    run_summaries = []
    for run_id, group in day_df.groupby("run_id", dropna=True):
        run_summaries.append((str(run_id), scan_display_label(group), group["generated_at_dt"].max()))
    run_summaries = sorted(run_summaries, key=lambda item: item[2], reverse=True)
    runs = [item[0] for item in run_summaries]
    run_labels = {item[0]: item[1] for item in run_summaries}
    selected_run = col_run.selectbox("스캔", runs, index=0, format_func=lambda rid: run_labels.get(str(rid), str(rid)))
    page_size = col_size.selectbox("페이지 크기", [1, 3, 5, 10], index=3)
    run_df = day_df[day_df["run_id"] == selected_run].copy()
    run_df["rank"] = pd.to_numeric(run_df.get("rank"), errors="coerce")
    run_df["_analysis_section_order"] = run_df["selection_alignment"].apply(top_deep_section_order)
    run_df["_analysis_section_rank"] = run_df["selection_alignment"].apply(top_deep_section_rank)
    run_df["_analysis_section_rank"] = pd.to_numeric(run_df["_analysis_section_rank"], errors="coerce")
    run_df = run_df.sort_values(["_analysis_section_order", "_analysis_section_rank", "rank", "generated_at_dt"], ascending=[True, True, True, False])
    total = len(run_df)
    max_page = max(1, math.ceil(total / int(page_size)))
    page = st.number_input("페이지", min_value=1, max_value=max_page, value=1, step=1)
    page_df = run_df.iloc[(int(page) - 1) * int(page_size): int(page) * int(page_size)]
    st.caption(f"{selected_market} · {selected_date} · {run_labels.get(str(selected_run), selected_run)} · {page}/{max_page} 페이지")
    section_counts = run_df["selection_alignment"].apply(top_deep_section_name).value_counts().to_dict()
    operating_count = sum(
        int(section_counts.get(section, 0) or 0)
        for section in ("KOSPI Operating Challenger", "KOSDAQ Operating Challenger")
    )
    st.caption(
        f"섹션: Challenger {operating_count} / "
        f"Practical {section_counts.get('Practical 80 Gate', 0)} / "
        f"Shadow {sum(int(section_counts.get(section, 0) or 0) for section in TOP_DEEP_SECTION_ORDER if 'Shadow' in section)} / "
        f"Top5 {section_counts.get('Top5', 0)} / Exception {section_counts.get('Exception Leader', 0)}"
    )
    scan_context = load_scan_context_for_run(str(selected_run))
    scan_summary = scan_context.get("summary") if isinstance(scan_context.get("summary"), dict) else {}
    market_gate = scan_context.get("market_gate") if isinstance(scan_context.get("market_gate"), dict) else {}
    integrity_report = scan_integrity_report_for_context(scan_context)
    result_count = int(scan_summary.get("result_count") or section_counts.get("Top5", 0) or 0)
    filtered_count = int(scan_summary.get("filtered_count") or 0)
    gate_msg = str(market_gate.get("msg") or "")
    if result_count == 0 and section_counts.get("Exception Leader", 0):
        st.warning(
            "원본 Top5 통과 후보 0개입니다. "
            f"필터 {filtered_count}개 · Exception Leader {section_counts.get('Exception Leader', 0)}개는 추가 관찰 후보로만 표시됩니다."
        )
    if gate_msg:
        gate = str(market_gate.get("gate") or "-").upper()
        if gate == "RED":
            st.error(f"시장 게이트: {gate_msg}")
        elif gate == "YELLOW":
            st.warning(f"시장 게이트: {gate_msg}")
        else:
            st.info(f"시장 게이트: {gate_msg}")
    render_scan_integrity_panel(integrity_report, compact=True)
    exposure_summary = scan_summary.get("portfolio_exposure_summary") if isinstance(scan_summary.get("portfolio_exposure_summary"), dict) else {}
    if not exposure_summary:
        exposure_summary = build_portfolio_exposure_summary(run_df.to_dict("records"), run_id=str(selected_run))
    exposure_flags = exposure_summary.get("risk_flags") if isinstance(exposure_summary.get("risk_flags"), list) else []
    if exposure_flags:
        st.warning("포트폴리오 노출: " + " / ".join(render_portfolio_exposure_lines(exposure_summary)[:3]))
    else:
        st.info("포트폴리오 노출: " + " / ".join(render_portfolio_exposure_lines(exposure_summary)[:3]))

    for row in page_df.to_dict("records"):
        price = row.get("price") if isinstance(row.get("price"), dict) else {}
        news = row.get("news") if isinstance(row.get("news"), dict) else {}
        prediction = row.get("prediction") if isinstance(row.get("prediction"), dict) else {}
        trade_plan = row.get("trade_plan") if isinstance(row.get("trade_plan"), dict) else {}
        execution_stop = row.get("execution_stop") if isinstance(row.get("execution_stop"), dict) else {}
        if not execution_stop and isinstance(trade_plan.get("execution_stop"), dict):
            execution_stop = trade_plan["execution_stop"]
        readiness = trade_plan.get("readiness_analysis") if isinstance(trade_plan.get("readiness_analysis"), dict) else {}
        theme = row.get("theme") if isinstance(row.get("theme"), dict) else {}
        flow = row.get("flow") if isinstance(row.get("flow"), dict) else {}
        alignment = row.get("selection_alignment") if isinstance(row.get("selection_alignment"), dict) else {}
        display_contract = row.get("display_contract") if isinstance(row.get("display_contract"), dict) else {}
        policy_metadata = row.get("policy_metadata") if isinstance(row.get("policy_metadata"), dict) else {}
        admission = row.get("realized_expectancy_admission") if isinstance(row.get("realized_expectancy_admission"), dict) else {}
        candidate_data_quality = row.get("candidate_data_quality") if isinstance(row.get("candidate_data_quality"), dict) else {}
        section = alignment.get("analysis_section") or "Top5"
        section_rank = alignment.get("analysis_section_rank") or row.get("rank") or 0
        title = f"{section} #{int(section_rank or 0)} {row.get('stock_name') or row.get('ticker')} ({row.get('ticker')})"
        with st.container(border=True):
            st.markdown(f"### {title}")
            st.caption(
                f"{row.get('signal_label') or '-'} · {row.get('decision') or '-'} · {theme.get('primary_theme') or '-'} · "
                f"원본스캔 #{alignment.get('raw_scan_rank') or '-'} / 플래너 #{alignment.get('planner_priority_rank') or row.get('rank') or '-'}"
            )
            st.caption(
                f"표시계약 {display_contract.get('display_status') or 'VISIBLE'} · "
                f"숨김허용 {display_contract.get('suppression_allowed', False)} · "
                f"표시사유 {display_contract.get('display_reason') or 'scanner_emitted_candidate'}"
            )
            st.caption(
                f"정책 {policy_metadata.get('active_policy_version') or '-'} · "
                f"상태 {policy_metadata.get('promotion_status') or '-'} · "
                f"롤백 {policy_metadata.get('rollback_active', False)}"
            )
            if candidate_data_quality:
                st.caption(
                    f"데이터 품질 {candidate_data_quality.get('display_warning_level') or '-'} · "
                    f"필수필드 {candidate_data_quality.get('required_present_pct', '-')}% · "
                    f"경고 {', '.join((candidate_data_quality.get('visible_warnings') or [])[:4]) or '-'}"
                )
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("매수점수", fmt_metric_num(row.get("buy_score"), 1))
            c2.metric("구간 적중률", fmt_metric_pct(row.get("accuracy")), help="후보 개별 확률이 아니라 같은 시장/섹션의 과거 5D 실현 승률입니다.")
            c3.metric("전일비", fmt_metric_pct(row.get("day_change_pct")))
            c4.metric("손실위험", fmt_metric_num(row.get("loss_risk_score"), 1))
            c5.metric("뉴스감성", fmt_metric_num(news.get("sentiment_score"), 2))
            c6.metric("예상순수익 3D", fmt_metric_pct(prediction.get("expected_net_return_3d_pct")))

            a1, a2, a3, a4, a5 = st.columns(5)
            a1.metric("후보 5D확률", fmt_metric_pct(admission.get("5d_prob")), help="구간 승률, 후보 점수, 모멘텀, 손실위험을 반영한 후보별 5D 확률입니다.")
            a2.metric("기본기대 5D", fmt_metric_pct(admission.get("base_expected_value_5d_pct", admission.get("expected_value_5d_pct"))), help="승리 시 평균수익, 실패 시 평균손실을 쓴 기본 기대값입니다.")
            a3.metric("꼬리위험 5D", fmt_metric_pct(admission.get("stress_expected_value_5d_pct", admission.get("expected_value_5d_pct"))), help="실패 시 역사적 최악 손실을 쓴 스트레스 기대값입니다.")
            a4.metric("5D 랭킹", fmt_metric_num(admission.get("ranking_score_5d"), 1))
            a5.metric("Stop-first", fmt_metric_pct(admission.get("stop_first_risk_pct")))
            st.caption(
                "정확도 분리: 구간 적중률은 과거 섹션 통계, 후보 5D확률은 후보별 보정값, "
                "기본기대는 평균손실 기준, 꼬리위험은 최악손실 기준입니다."
            )
            regime_theme_adjustment = admission.get("regime_theme_adjustment") if isinstance(admission.get("regime_theme_adjustment"), dict) else {}
            if regime_theme_adjustment:
                warnings = regime_theme_adjustment.get("warnings") if isinstance(regime_theme_adjustment.get("warnings"), list) else []
                st.caption(
                    "국면/테마 보정 "
                    f"확률x{fmt_metric_num(regime_theme_adjustment.get('prob_multiplier'), 2)} · "
                    f"수익x{fmt_metric_num(regime_theme_adjustment.get('return_multiplier'), 2)} · "
                    f"손절위험x{fmt_metric_num(regime_theme_adjustment.get('stop_risk_multiplier'), 2)} · "
                    f"신뢰도 {fmt_metric_pct((regime_theme_adjustment.get('confidence') or 0) * 100)}"
                    + (f" · 경고 {', '.join(str(item) for item in warnings[:3])}" if warnings else "")
                )

            render_selection_thesis(row, trade_plan)

            p1, p2, p3, p4 = st.columns(4)
            p1.metric("현재가", fmt_metric_num(price.get("current_price"), 2))
            p2.metric("거래량", f"{int(price.get('volume')):,}" if price.get("volume") is not None else "-")
            p3.metric("거래량/20D", fmt_metric_num(price.get("volume_ratio_20d"), 2))
            p4.metric("차트추세", str(price.get("trend") or "-"))

            e1, e2, e3, e4, e5 = st.columns(5)
            e1.metric("1D 기대", fmt_metric_pct(prediction.get("expected_return_1d_pct")))
            e2.metric("3D 기대", fmt_metric_pct(prediction.get("expected_return_3d_pct")))
            e3.metric("진입가", fmt_krw(trade_plan.get("entry_reference_price")), str(trade_plan.get("entry_policy") or "-"))
            e4.metric("목표가", fmt_krw(trade_plan.get("target_price")), fmt_metric_pct(trade_plan.get("target_tp_pct")))
            e5.metric(
                "표시 손절가",
                fmt_krw(execution_stop.get("display_stop_price") or trade_plan.get("stop_price")),
                fmt_metric_pct(execution_stop.get("display_stop_sl_pct") or trade_plan.get("stop_sl_pct")),
                delta_color="inverse",
            )
            if execution_stop.get("display_stop_source"):
                msg = f"손절 기준: {execution_stop.get('display_stop_source')}"
                if execution_stop.get("stop_conflict"):
                    msg += " · raw/dynamic 충돌, 더 엄격한 값 표시"
                st.caption(msg)

            z1, z2, z3, z4 = st.columns(4)
            z1.metric("진입 하단", fmt_krw(trade_plan.get("entry_zone_low")))
            z2.metric("진입 상단", fmt_krw(trade_plan.get("entry_zone_high")))
            z3.metric("손익비", fmt_metric_num(trade_plan.get("risk_reward"), 2))
            z4.metric("보유일", f"{trade_plan.get('hold_days') or '-'}일")

            st.markdown("**수급**")
            f1, f2, f3, f4 = st.columns(4)
            flow_unit = flow.get("flow_unit")
            flow_window_key = str(flow.get("flow_window") or "").lower()
            flow_metric_prefix = "당일 " if flow_window_key in {"1d", "day"} else ""
            f1.metric(f"{flow_metric_prefix}외인", fmt_flow_value(flow.get("foreigner_1d", flow.get("foreigner")), flow_unit))
            f2.metric(f"{flow_metric_prefix}기관", fmt_flow_value(flow.get("institution_1d", flow.get("institution")), flow_unit))
            f3.metric(f"{flow_metric_prefix}개인", fmt_flow_value(flow.get("retail_1d", flow.get("retail")), flow_unit), help="개인 순매수가 과도하면 단기 수급 품질이 낮을 수 있습니다.")
            f4.metric("수급점수", fmt_metric_num(flow.get("whale_score"), 0), str(flow.get("whale_trend") or "-"))
            flow_warnings = flow.get("warnings") if isinstance(flow.get("warnings"), list) else []
            flow_source = str(flow.get("source") or "-")
            flow_unit_label = {"krw": "원", "shares": "주"}.get(str(flow_unit or "").lower(), str(flow_unit or "-"))
            st.caption(f"수급 기준: {flow_source} · 단위: {flow_unit_label}")
            flow_leader_caption = fmt_flow_leader_caption(flow)
            if flow_leader_caption:
                st.caption(flow_leader_caption)
            if flow.get("scan_whale_score") is not None and flow.get("scan_whale_score") != flow.get("whale_score"):
                st.caption(f"스캔 당시 수급점수: {fmt_metric_num(flow.get('scan_whale_score'), 0)} / 현재 보강 수급점수: {fmt_metric_num(flow.get('whale_score'), 0)}")
            if flow_warnings:
                st.caption("수급 데이터 참고: " + " / ".join(str(x) for x in flow_warnings[:3]))
            if not flow.get("valid"):
                st.caption("수급 데이터 경고: " + " / ".join(str(x) for x in flow_warnings[:3]) if flow_warnings else "수급 데이터 미확보")

            render_readiness_analysis(readiness)
            render_data_backed_action_plan(trade_plan, readiness)

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
                        st.caption(f"{fmt_metric_num(item.get('score'), 2)} · {item.get('title')}")
            warnings = row.get("data_warnings") if isinstance(row.get("data_warnings"), list) else []
            if warnings:
                st.caption("데이터 경고: " + " / ".join(str(x) for x in warnings[:5]))


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
    "render_top_deep_reports_page",
    "scan_display_label",
    "top_deep_section_name",
    "top_deep_section_order",
    "top_deep_section_rank",
]
