"""Scanner cockpit and signal-card Streamlit rendering.

Keep app.py as the page composition entrypoint; this module owns the scanner
candidate cockpit UI and reusable signal-card list.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

from modules.admission_metric_copy import metric_help, metric_label
from modules.scan_universe_admission import (
    admission_model_summary,
    admission_run_status,
    build_scan_universe_admission_records,
)
from modules.ui_helpers import (
    build_signal_display_rows,
    enrich_signal_rows_with_planner_trace,
    merge_profile_exception_leaders_into_planner,
)


def _load_json_safe(path_str: str | None) -> Dict[str, Any]:
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


def _fmt_score_or_dash(value: Any) -> str:
    if value is None or value == "":
        return "-"
    try:
        return f"{float(str(value).replace('%', '').replace(',', '').strip()):.1f}"
    except Exception:
        return str(value)


def _fmt_metric_pct_or_dash(value: Any) -> str:
    if value is None or value == "":
        return "-"
    try:
        return f"{float(str(value).replace('%', '').replace(',', '').strip()):.1f}%"
    except Exception:
        return str(value)


def _ticker_of(row: Dict[str, Any]) -> str:
    return str(row.get("ticker") or row.get("티커") or row.get("Ticker") or row.get("symbol") or "").strip()


def _name_of(row: Dict[str, Any]) -> str:
    return str(row.get("stock_name") or row.get("종목명") or row.get("Name") or row.get("name") or "").strip()


def _score_of(row: Dict[str, Any]) -> Any:
    return row.get("Decision Score") or row.get("decision_score") or row.get("score")


def render_signal_card_list(rows: List[Dict[str, Any]], *, empty_text: str = "표시할 후보가 없습니다.") -> None:
    if not rows:
        st.info(empty_text)
        return
    for row in rows:
        day_val = row.get("day_change_value")
        if day_val is None:
            day_delta = None
        elif float(day_val) > 0:
            day_delta = "상승"
        elif float(day_val) < 0:
            day_delta = "하락"
        else:
            day_delta = "보합"
        name = str(row.get("name") or "").strip()
        ticker = str(row.get("ticker") or "").strip()
        subtitle_parts = [part for part in (row.get("theme"), row.get("trend")) if part and part != "-"]
        subtitle = " · ".join(str(part) for part in subtitle_parts) or "-"
        exit_parts = []
        if row.get("entry") and row.get("entry") != "-":
            exit_parts.append(f"Entry {row.get('entry')}")
        if row.get("tp") and row.get("tp") != "-":
            exit_parts.append(f"TP {row.get('tp')}")
        if row.get("sl") and row.get("sl") != "-":
            exit_parts.append(f"SL {row.get('sl')}")
        buy_signal = str(row.get("buy_signal") or "-")
        action_label = str(row.get("action_label") or "-")
        action_condition = str(row.get("action_condition") or "")
        stop_condition = str(row.get("stop_condition") or "")
        action_reasons = [str(reason) for reason in (row.get("action_reasons") or []) if str(reason).strip()]
        risk_label = str(row.get("loss_risk") or "-")
        risk_level = str(row.get("loss_risk_level") or "")
        risk_flags = [str(flag) for flag in (row.get("risk_flags") or []) if str(flag).strip()]
        gate_label = str(row.get("practical_gate_label") or "")
        gate_level = str(row.get("practical_gate_level") or "")
        gate_reasons = [str(reason) for reason in (row.get("practical_gate_reasons") or []) if str(reason).strip()]
        gate_evidence = row.get("practical_gate_evidence") if isinstance(row.get("practical_gate_evidence"), dict) else {}
        shadow_gate_label = str(row.get("shadow_gate_label") or "")
        shadow_gate_profile = str(row.get("shadow_gate_profile") or "")
        shadow_gate_conditions = str(row.get("shadow_gate_conditions") or "")
        shadow_gate_metrics = str(row.get("shadow_gate_metrics") or "")
        shadow_gate_note = str(row.get("shadow_gate_note") or "")
        radar_score = row.get("next_day_radar_score")
        radar_plus5 = row.get("next_day_plus5_prob")
        radar_plus10 = row.get("next_day_plus10_prob")
        admission_model_name = str(row.get("admission_model_name") or "")
        admission_probability = row.get("admission_probability_pct")
        admission_threshold = row.get("admission_threshold_pct")
        admission_rule = str(row.get("admission_selection_rule") or "")
        admission_coverage = row.get("admission_feature_coverage")
        scan_model_decision = str(row.get("scan_model_decision") or "")
        scan_model_action = str(row.get("scan_model_action") or "")
        scan_threshold_gap = row.get("scan_threshold_gap_pct_points")
        scan_drivers = [str(item) for item in (row.get("scan_interpretation_drivers") or []) if str(item).strip()]
        scan_warnings = [str(item) for item in (row.get("scan_interpretation_warnings") or []) if str(item).strip()]
        candidate_5d_prob = row.get("realized_expectancy_5d_prob")
        base_ev_5d = row.get("base_expected_value_5d_pct")
        stress_ev_5d = row.get("stress_expected_value_5d_pct")
        radar_reasons = [str(reason) for reason in (row.get("next_day_radar_reasons") or []) if str(reason).strip()]
        radar_missing = [str(reason) for reason in (row.get("next_day_radar_unavailable") or []) if str(reason).strip()]
        stop_source = str(row.get("stop_display_source") or "")
        stop_conflict = bool(row.get("stop_conflict"))
        risk_line = ""
        if risk_label != "-":
            risk_line = f"손실위험 {risk_label}" + (f" ({risk_level})" if risk_level else "")
        if risk_flags:
            risk_line = (risk_line + " · " if risk_line else "") + " / ".join(risk_flags[:3])

        with st.container(border=True):
            cols = st.columns([1.2, 2.05, 0.85, 0.85, 0.85], vertical_alignment="center")
            with cols[0]:
                section = str(row.get("analysis_section") or "").strip()
                section_rank = row.get("analysis_section_rank") or row.get("rank") or "-"
                st.caption(f"#{section_rank}" + (f" · {section}" if section else ""))
                st.markdown(f"**{ticker or '-'}**")
                st.caption(name or subtitle)
            with cols[1]:
                st.markdown(f"**{buy_signal}**")
                if shadow_gate_label:
                    st.caption(f"{shadow_gate_label} · {shadow_gate_profile} · {shadow_gate_metrics}")
                    if shadow_gate_conditions:
                        st.caption(shadow_gate_conditions)
                    if shadow_gate_note:
                        st.caption(shadow_gate_note)
                if radar_score is not None:
                    st.caption(
                        f"별도 급등 레이더 · score {_fmt_score_or_dash(radar_score)} · "
                        f"+5확률 {_fmt_score_or_dash(radar_plus5)} · +10확률 {_fmt_score_or_dash(radar_plus10)}"
                    )
                    if radar_reasons:
                        st.caption("레이더 근거 " + " / ".join(radar_reasons[:4]))
                    if radar_missing:
                        st.caption("미확보 피처 " + " / ".join(radar_missing[:3]))
                if admission_model_name:
                    st.caption(
                        f"Admission 모델 {admission_model_name} · {metric_label('candidate_pass_prob_5d')} {_fmt_metric_pct_or_dash(admission_probability)} "
                        f"/ 기준 {_fmt_metric_pct_or_dash(admission_threshold)} · {admission_rule}"
                    )
                    if admission_coverage is not None:
                        st.caption(f"피처 커버리지 {_fmt_metric_pct_or_dash(float(admission_coverage) * 100.0)}")
                if scan_model_decision:
                    gap_text = ""
                    if scan_threshold_gap is not None:
                        gap_text = f" · 기준차 {_fmt_score_or_dash(scan_threshold_gap)}%p"
                    action_text = f" · {scan_model_action}" if scan_model_action else ""
                    st.caption(f"모델 해석 {scan_model_decision}{gap_text}{action_text}")
                if scan_drivers:
                    st.caption("상승/위험 근거 " + " / ".join(scan_drivers[:4]))
                if scan_warnings:
                    st.caption("데이터·리스크 경고 " + " / ".join(scan_warnings[:3]))
                if action_label != "-":
                    action_line = f"액션 {action_label}"
                    if action_condition:
                        action_line += f" · {action_condition}"
                    st.caption(action_line)
                if stop_condition:
                    st.caption(f"손절/제외 {stop_condition}")
                if action_reasons:
                    st.caption("판단 근거 " + " / ".join(action_reasons[:3]))
                if gate_level in {"pass", "near", "small_sample", "watch"}:
                    evidence = ""
                    if gate_evidence:
                        evidence = (
                            f" · 검증 n={gate_evidence.get('sample_n', '-')}, "
                            f"실전승률 {gate_evidence.get('practical_win_pct', '-')}%, "
                            f"bad {gate_evidence.get('bad_path_pct', '-')}%"
                        )
                    st.caption(f"{gate_label}{evidence}")
                    if gate_reasons:
                        st.caption("80% 피처 " + " / ".join(gate_reasons[:2]))
                if exit_parts:
                    st.caption(" · ".join(exit_parts))
                if stop_source:
                    label = "표시 손절"
                    if stop_conflict:
                        label += " 충돌: 더 엄격한 값 적용"
                    st.caption(f"{label} · {stop_source}")
                expectancy_parts = []
                if candidate_5d_prob is not None:
                    expectancy_parts.append(f"{metric_label('candidate_pass_prob_5d')} {_fmt_metric_pct_or_dash(candidate_5d_prob)}")
                if base_ev_5d is not None:
                    expectancy_parts.append(f"{metric_label('validation_avg_return_5d')} {_fmt_metric_pct_or_dash(base_ev_5d)}")
                if stress_ev_5d is not None:
                    expectancy_parts.append(f"{metric_label('validation_worst_return_5d')} {_fmt_metric_pct_or_dash(stress_ev_5d)}")
                if expectancy_parts:
                    st.caption(" / ".join(expectancy_parts))
                if risk_line:
                    st.caption(risk_line)
                if name and subtitle != "-":
                    st.caption(subtitle)
            with cols[2]:
                st.metric(
                    metric_label("cohort_win_5d"),
                    str(row.get("accuracy") or "-"),
                    help=(
                        metric_help("cohort_win_5d")
                        if admission_model_name
                        else "이 등급/시장/스캔모드의 historical OOS win rate (5d hold). 후보별 확률이 아니라 segment 단위 통계입니다."
                    ),
                )
            with cols[3]:
                st.metric(
                    metric_label("candidate_pass_prob_5d"),
                    _fmt_metric_pct_or_dash(candidate_5d_prob),
                    help=metric_help("candidate_pass_prob_5d"),
                )
            with cols[4]:
                st.metric("전일비", str(row.get("day_change") or "-"), day_delta)


def render_scan_top_candidates(results_df: Any, bridge_info: Dict[str, Any] | None, market: str) -> None:
    """Render production scan candidates with the scan-universe admission model.

    The previous Top5/Exception/Shadow sections remain in historical artifacts,
    but live operation now exposes only the promoted admission model plus
    threshold-near diagnostics.
    """
    planner_payload = _load_json_safe(bridge_info.get("planner_handoff")) if isinstance(bridge_info, dict) else {}
    profile_payload = _load_json_safe(bridge_info.get("profile_diagnostics")) if isinstance(bridge_info, dict) else {}
    planner_payload = merge_profile_exception_leaders_into_planner(planner_payload, profile_payload)
    raw_score_records = results_df.to_dict("records")
    enriched_records = enrich_signal_rows_with_planner_trace(raw_score_records, planner_payload)
    market_key = str(market or "").upper().strip()

    if market_key not in {"KOSPI", "KOSDAQ"}:
        st.markdown("### 스캔 후보")
        st.caption("국장 admission 모델은 KOSPI/KOSDAQ 전용입니다. 해외 시장은 원본 스캔 후보를 진단용으로 표시합니다.")
        render_signal_card_list(build_signal_display_rows(enriched_records[:5], limit=5), empty_text="표시할 후보 없음.")
        return

    try:
        admission = build_scan_universe_admission_records(
            enriched_records,
            market=market_key,
            limit=5,
            include_near_miss=True,
        )
        summary = admission.get("summary") if isinstance(admission.get("summary"), dict) else admission_model_summary(market_key)
    except Exception as exc:
        st.error(f"신규 admission 모델 로드/추론 실패: {exc}")
        return

    validation = summary.get("validation") if isinstance(summary.get("validation"), dict) else {}
    run_status = admission_run_status(admission)
    pass_rows = build_signal_display_rows(admission.get("passed", []), limit=summary.get("topn") or 1)
    near_rows = build_signal_display_rows(admission.get("near_miss", []), limit=5)
    all_rows = build_signal_display_rows(admission.get("all_records", []), limit=None)

    st.markdown("### 신규 운영 모델")
    cols = st.columns(6)
    gap = run_status.get("best_gap_pct_points")
    gap_text = "-" if gap is None else f"{float(gap):+.1f}%p"
    pass_count = int(run_status.get("passed_count") or 0)
    topn = int(run_status.get("topn") or 1)
    cols[0].metric(
        metric_label("admission_pass_count"),
        f"{pass_count}/{topn}",
        help=metric_help("admission_pass_count"),
    )
    cols[1].metric(
        metric_label("candidate_top_prob_5d"),
        _fmt_metric_pct_or_dash(run_status.get("best_probability_pct")),
        gap_text,
        help=metric_help("candidate_top_prob_5d"),
    )
    cols[2].metric(
        metric_label("admission_threshold"),
        _fmt_metric_pct_or_dash(run_status.get("threshold_pct")),
        help=metric_help("admission_threshold"),
    )
    cols[3].metric(
        metric_label("cohort_win_5d"),
        _fmt_metric_pct_or_dash(validation.get("win_5d_pct")),
        _fmt_metric_pct_or_dash(validation.get("avg_5d_pct")),
        help=metric_help("cohort_win_5d"),
    )
    cols[4].metric(
        metric_label("validation_worst_return_5d"),
        _fmt_metric_pct_or_dash(validation.get("min_5d_pct")),
        help=metric_help("validation_worst_return_5d"),
    )
    cols[5].metric("표본", f"n={validation.get('n') or '-'}", f"{validation.get('active_days') or '-'}일")
    st.caption(
        f"{summary.get('market')} · {summary.get('label')} · {summary.get('feature_set')} · "
        f"{summary.get('model_name')} · {summary.get('selection_rule')} · "
        f"최고5D {_fmt_metric_pct_or_dash(validation.get('max_5d_pct'))} / "
        f"bad-path {_fmt_metric_pct_or_dash(validation.get('bad_path_pct'))}"
    )
    if pass_rows:
        st.success(run_status.get("message") or "운영 통과 후보가 있습니다.")
    else:
        st.warning(
            (run_status.get("message") or "운영 통과 후보가 없습니다.")
            + " 이 상태는 내일 상승 종목이 없다는 확정이 아니라, 현재 운영 모델 기준으로 매수 승격할 만큼 강한 후보가 없다는 뜻입니다."
        )

    st.markdown("### 운영 통과 후보")
    st.caption("검증된 selection rule 기준으로 run당 최대 1개만 승격합니다. 이 섹션만 운영 후보로 봅니다.")
    if pass_rows:
        render_signal_card_list(pass_rows, empty_text="운영 통과 후보 없음.")
    else:
        st.warning("이번 스캔은 Admission 모델 운영 기준을 통과한 후보가 없습니다.")

    st.markdown("### 기준 미달 상위 후보")
    st.caption("매수 후보가 아니라 모델 확률 진단용입니다. 확률이 운영 기준을 넘기 전까지 승격하지 않습니다.")
    render_signal_card_list(near_rows, empty_text="기준 미달 상위 후보도 없습니다.")

    with st.expander("전체 스캔 결과 해석", expanded=False):
        st.caption("이번 스캔에서 올라온 모든 후보를 Admission 모델 확률순으로 해석합니다. 통과 여부, 기준차, 피처/수급/거래량 근거를 같이 봅니다.")
        table_rows = []
        for row in all_rows:
            table_rows.append(
                {
                    "순위": row.get("analysis_section_rank") or row.get("rank"),
                    "티커": row.get("ticker"),
                    "종목": row.get("name"),
                    "모델판정": row.get("scan_model_decision") or ("통과" if row.get("admission_passed") else "기준미달"),
                    "후보확률": _fmt_metric_pct_or_dash(row.get("admission_probability_pct")),
                    "기준": _fmt_metric_pct_or_dash(row.get("admission_threshold_pct")),
                    "기준차": (
                        f"{float(row.get('scan_threshold_gap_pct_points')):+.1f}%p"
                        if row.get("scan_threshold_gap_pct_points") is not None
                        else "-"
                    ),
                    "피처": _fmt_metric_pct_or_dash(
                        float(row.get("admission_feature_coverage")) * 100.0
                        if row.get("admission_feature_coverage") is not None
                        else None
                    ),
                    "전일비": row.get("day_change"),
                    "해석": row.get("scan_interpretation_text") or row.get("action_condition") or "-",
                }
            )
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

    with st.expander("보조 확인 · 원본 점수 상위와 Admission 모델 확률", expanded=False):
        st.caption("후보 선정은 신규 admission 모델 기준입니다. 원본 점수는 왜 후보가 달라졌는지 확인하기 위한 보조 지표입니다.")
        ranked_by_model = (admission.get("passed", []) or []) + (admission.get("near_miss", []) or [])
        model_by_ticker = {
            str(row.get("ticker") or row.get("Ticker") or row.get("티커") or "").upper(): row.get("scan_universe_admission") or {}
            for row in ranked_by_model
        }
        for idx, row in enumerate(raw_score_records[:5], start=1):
            ticker = _ticker_of(row).upper()
            model = model_by_ticker.get(ticker) or {}
            st.caption(
                f"#{idx} {ticker or '-'} {_name_of(row)} · 원본점수 {_fmt_score_or_dash(_score_of(row))} · "
                f"모델확률 {_fmt_metric_pct_or_dash(model.get('probability_pct'))} / 기준 {_fmt_metric_pct_or_dash(model.get('prob_threshold_pct'))}"
            )
