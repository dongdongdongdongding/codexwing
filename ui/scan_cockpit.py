"""Scanner cockpit and signal-card Streamlit rendering.

Keep app.py as the page composition entrypoint; this module owns the scanner
candidate cockpit UI and reusable signal-card list.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

from modules.ui_helpers import (
    build_live_cockpit_summary,
    build_signal_display_rows,
    build_top5_plus_exception_records,
    build_top_candidate_compact_view,
    enrich_signal_rows_with_planner_trace,
    merge_profile_exception_leaders_into_planner,
    sort_signal_rows_by_planner_rank,
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


def _fmt_pct_or_dash(value: Any) -> str:
    if value is None or value == "":
        return "-"
    try:
        return f"{float(value):.1f}"
    except Exception:
        return "-"


def _fmt_score_or_dash(value: Any) -> str:
    if value is None or value == "":
        return "-"
    try:
        return f"{float(str(value).replace('%', '').replace(',', '').strip()):.1f}"
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
        risk_line = ""
        if risk_label != "-":
            risk_line = f"손실위험 {risk_label}" + (f" ({risk_level})" if risk_level else "")
        if risk_flags:
            risk_line = (risk_line + " · " if risk_line else "") + " / ".join(risk_flags[:3])

        with st.container(border=True):
            cols = st.columns([1.25, 2.3, 0.9, 0.9], vertical_alignment="center")
            with cols[0]:
                section = str(row.get("analysis_section") or "").strip()
                section_rank = row.get("analysis_section_rank") or row.get("rank") or "-"
                st.caption(f"#{section_rank}" + (f" · {section}" if section else ""))
                st.markdown(f"**{ticker or '-'}**")
                st.caption(name or subtitle)
            with cols[1]:
                st.markdown(f"**{buy_signal}**")
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
                if risk_line:
                    st.caption(risk_line)
                if name and subtitle != "-":
                    st.caption(subtitle)
            with cols[2]:
                st.metric(
                    "적중률(OOS)",
                    str(row.get("accuracy") or "-"),
                    help=(
                        "이 등급/시장의 historical OOS win rate (5d hold). "
                        "후보별 변동값이 아니라 segment 단위 invariant. "
                        "raw 모델 score가 아닌 dedup 측정 win rate."
                    ),
                )
            with cols[3]:
                st.metric("전일비", str(row.get("day_change") or "-"), day_delta)


def render_scan_top_candidates(results_df: Any, bridge_info: Dict[str, Any] | None, market: str) -> None:
    # 2026-05-09: 8:2 자본 배분에 따라 카드를 두 섹션으로 분리.
    # Stream A (안전 80%) = PRIORITY/WATCHLIST/OBSERVE 위주
    # Stream B (급등 20%) = EXCEPTION_LEADER만
    planner_payload = _load_json_safe(bridge_info.get("planner_handoff")) if isinstance(bridge_info, dict) else {}
    profile_payload = _load_json_safe(bridge_info.get("profile_diagnostics")) if isinstance(bridge_info, dict) else {}
    planner_payload = merge_profile_exception_leaders_into_planner(planner_payload, profile_payload)
    raw_score_records = results_df.to_dict("records")
    enriched_records = enrich_signal_rows_with_planner_trace(
        raw_score_records,
        planner_payload,
    )
    raw_records = sort_signal_rows_by_planner_rank(enriched_records, planner_payload)
    groups = build_top5_plus_exception_records(
        raw_score_records,
        planner_payload,
        top_limit=5,
        exception_limit=5,
    )
    stream_a_records = groups["top5"]
    stream_b_records = groups["exception_leaders"]
    display_records = groups["combined"]

    stream_a_rows = build_signal_display_rows(stream_a_records, limit=5)
    stream_b_rows = build_signal_display_rows(stream_b_records, limit=5)
    cockpit = build_live_cockpit_summary(
        stream_a_rows,
        stream_b_rows,
        market=market,
        strict_quality_gate=str(os.getenv("AG_STRICT_SCAN_QUALITY_GATE", "1")).strip().lower()
        not in {"0", "", "false", "no", "off"},
    )

    st.markdown("### 운영 콕핏")
    cockpit_cols = st.columns(5)
    cockpit_cols[0].metric("실행 후보", f"{cockpit['actionable_count']}")
    cockpit_cols[1].metric("Stream A", f"{cockpit['stream_a_count']}")
    cockpit_cols[2].metric("Stream B", f"{cockpit['stream_b_count']}")
    cockpit_cols[3].metric("데이터 게이트", cockpit["quality_gate"])
    cockpit_cols[4].metric("검증 승률", cockpit["validated_win"])
    st.caption(
        f"{cockpit['market']} live policy: {cockpit['policy']} | "
        f"5D target return: {cockpit['validated_return']} | {cockpit['sample']}"
    )

    gate_order = {"pass": 0, "near": 1, "small_sample": 2, "watch": 3}
    practical_rows = sorted(
        [
            row for row in (stream_a_rows + stream_b_rows)
            if row.get("practical_gate_promote")
        ],
        key=lambda row: (
            gate_order.get(str(row.get("practical_gate_level") or ""), 9),
            int(row.get("analysis_section_rank") or row.get("rank") or 9999),
        ),
    )[:5]
    st.markdown("### 80% 실전 필터 후보")
    st.caption(
        "사후 수익률을 쓰지 않고 스캔 시점 피처만으로 검증된 조합입니다. "
        "KOSPI 통과는 30개 이상 표본, KOSDAQ은 표본 부족 시 경고로 표시합니다."
    )
    if practical_rows:
        render_signal_card_list(practical_rows, empty_text="80% 실전 필터 후보 없음.")
    else:
        st.info("80% 실전 필터 후보 없음 - 이번 스캔은 Top5/Exception을 조건부로만 확인하세요.")

    st.markdown("### 메인 Top 5")
    st.caption(
        "서비스의 기본 메인 후보입니다. 기존 Top5 성과 기준으로 먼저 확인하고, "
        "Exception Leader는 아래 별도 카드에서 추가 확인합니다."
    )
    if stream_a_rows:
        render_signal_card_list(stream_a_rows, empty_text="Top5 후보 없음.")
    else:
        st.info("Top5 후보 없음 - 게이트가 모두 demote.")

    st.markdown("### Exception Leader 추가 후보")
    st.caption(
        "Top5를 대체하지 않는 별도 고변동 후보입니다. 있으면 Top5 아래에서 같은 카드 형식으로 확인하고, "
        "자동 정밀분석도 함께 생성됩니다."
    )
    if stream_b_rows:
        render_signal_card_list(stream_b_rows, empty_text="Exception Leader 후보 없음.")
    else:
        st.info("Exception Leader 후보 없음 - 이번 스캔에는 별도 급등 후보가 없습니다.")

    planner_top = [_ticker_of(row) for row in display_records[:5]]
    raw_top = [_ticker_of(row) for row in raw_score_records[:5]]
    overlap = len(set(planner_top).intersection(raw_top)) if planner_top and raw_top else 0
    with st.expander("보조 확인 · 원본 Top5 vs 플래너 후보", expanded=False):
        st.caption(
            "원본 스캔 상위는 Decision Score 기준 참고 목록입니다. 메인은 기존 Top5이고, "
            "Exception Leader는 별도 추가 후보입니다."
        )
        c_raw, c_plan = st.columns(2)
        with c_raw:
            st.markdown("**원본 스캔 상위 5 · Decision Score**")
            for idx, row in enumerate(raw_score_records[:5], start=1):
                ticker = _ticker_of(row)
                st.caption(
                    f"#{idx} {ticker} {_name_of(row)} · Score {_fmt_score_or_dash(_score_of(row))} · "
                    f"{row.get('전략') or row.get('strategy') or '-'}"
                )
        with c_plan:
            st.markdown("**플래너 실행 후보 5 · 정밀분석 기준**")
            for idx, row in enumerate(display_records[:5], start=1):
                ticker = _ticker_of(row)
                decision = row.get("decision") or row.get("Decision") or "-"
                rel = row.get("relative_rank_score")
                loss = row.get("loss_risk_score")
                st.caption(
                    f"#{idx} {ticker} {_name_of(row)} · {decision} · "
                    f"Rel {_fmt_score_or_dash(rel)} · Loss {_fmt_score_or_dash(loss)}"
                )
        if overlap < min(len(raw_top), len(planner_top), 5):
            st.warning(
                "두 목록이 다릅니다. 이는 정밀분석이 원본 점수 상위가 아니라 플래너 실행 후보를 분석한다는 뜻입니다."
            )

    if not stream_a_rows and not stream_b_rows:
        st.markdown("### 🔥 매수 신호")
        st.info(
            "현재 매수 신호 없음 - 시장 관망. 모든 후보가 OBSERVE/AVOID로 강등되었거나 "
            "OOS 검증을 통과하지 못했습니다. Watchlist 표에서 감시 종목을 확인하세요."
        )
        return

    st.markdown("### 보조 설명 · Top5 운용 기준")
    st.caption(
        "**자본 배분**: 1억이면 8,000만 → 종목당 약 1,600만. "
        "**정확성** = 이 등급/시장의 historical OOS win rate (5d hold 기준, dedup 측정). "
        "엔트리/TP/SL은 시장별 기본 정책 (KOSPI 시가/+20/-5, KOSDAQ -2%지정/+10/-10)."
    )
    st.markdown("### 보조 설명 · Exception Leader 운용 기준")
    st.caption(
        "**자본 배분**: 1억이면 2,000만 → 2-3종목 분산해서 종목당 약 700~1,000만. "
        "EXCEPTION_LEADER는 일반 게이트에 거부됐으나 alpha/conviction 매우 높아 surge 가능성 표시된 픽. "
        "**변동성 큼** - 손실 한도(SL) 엄수, 이 자본 안에서 큰 손실 났어도 Stream A는 안전."
    )

    view = build_top_candidate_compact_view(planner_payload, limit=5)
    detail_by_ticker = view.get("detail_by_ticker", {})
    all_signal_rows = stream_a_rows + stream_b_rows
    ticker_options = [str(r.get("ticker", "") or "") for r in all_signal_rows if r.get("ticker")]
    if not ticker_options:
        return

    detail_key = f"top_n_detail_select_{market}_{planner_payload.get('produced_at', '')}"
    selected = st.selectbox(
        "종목 상세 보기",
        options=ticker_options,
        key=detail_key,
    )
    detail = detail_by_ticker.get(str(selected) or "")
    if not detail:
        return

    with st.expander(f"📊 {detail.get('Name','') or selected} ({selected}) 상세", expanded=True):
        cols = st.columns(4)
        cols[0].metric("Decision", str(detail.get("Decision", "") or "-"))
        cols[1].metric("Theme", str(detail.get("Theme", "") or "-"))
        cols[2].metric("Trend", str(detail.get("Trend", "") or "-"))
        cols[3].metric("SigDir", str(detail.get("SigDir", "") or "-"))

        cols2 = st.columns(4)
        cols2[0].metric("Model Prob", _fmt_pct_or_dash(detail.get("Model Prob")))
        cols2[1].metric("Gate Thr", _fmt_pct_or_dash(detail.get("Gate Thr")))
        cols2[2].metric("OOS Win %", _fmt_pct_or_dash(detail.get("OOS Win %")))
        cols2[3].metric("OOS Ret %", _fmt_pct_or_dash(detail.get("OOS Ret %")))

        cols3 = st.columns(4)
        cols3[0].metric("Entry", str(detail.get("Entry", "") or "-"))
        cols3[1].metric("TP", str(detail.get("TP", "") or "-"))
        cols3[2].metric("SL", str(detail.get("SL", "") or "-"))
        cols3[3].metric("Hold", str(detail.get("Hold", "") or "-"))

        cols4 = st.columns(2)
        cols4[0].metric("손실위험", _fmt_pct_or_dash(detail.get("Loss Risk")))
        cols4[1].metric("리스크 플래그", str(detail.get("Risk Flags", "") or "-"))

        action_text = str(detail.get("Action", "") or "-")
        entry_condition = str(detail.get("Entry Condition", "") or "-")
        stop_condition = str(detail.get("Stop Condition", "") or "-")
        st.markdown(f"**최종 액션:** {action_text}")
        st.caption(f"매수 조건: {entry_condition}")
        st.caption(f"손절/제외 조건: {stop_condition}")
