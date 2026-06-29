from __future__ import annotations

import math
from typing import Any, Dict, List

from modules.operational_candidate_scoring import (
    DEFAULT_BUY_PREMIUM_PCT,
    MODEL_VALIDATED_LANES,
    build_operational_candidate_score,
)
from modules.ticker_names import resolve_name


INTERPRETATION_VERSION = "candidate_interpretation_v2"
BUY_PREMIUM_EXECUTION_GATE_VERSION = "buy_premium_execution_gate_v1"
BUY_READY_TARGET_PROFIT_PCT = 5.0
STOP_FIRST_MAX_DRAWDOWN_PCT = -10.0

# Model-validated lanes are scored by backtested forward touch-probability + walk-forward
# OOS, NOT by the legacy chart/non-chart operational gate (flow/theme/news axes). Those axes
# are structurally absent for these price/intraday-only models, so the legacy gate would
# demote every pick to "운용 보류 / AVOID_WEAK_SUPPORT" even though the model says BUY. These
# lanes therefore get a dedicated, honest interpretation that surfaces the model's own buy
# contract (entry=close, +5% target, hold N days, no tight stop). Only these exact buckets
# branch — planner picks are untouched. MODEL_VALIDATED_LANES is imported from
# operational_candidate_scoring (canonical home) so both gates agree.
LANE_PROFILE = {
    "swing_ensemble": {
        "label": "스윙 앙상블 매수",
        "operational_label": "모델 매수 · 가격앙상블",
        "scan_mode": "SWING",
        "lane_badge": "가격앙상블",
        "entry_label": "종가",
        "horizon_days": 5,
        "prob_label": "5일내 +5% 선터치(ft_5_5) 확률",
        "hold_note": "5거래일 종가 보유 · 분산(타이트 손절 X)",
    },
    "nasdaq_session_edge": {
        "label": "나스닥 세션 엣지 매수",
        "operational_label": "모델 매수 · 나스닥 정규장마감 세션",
        "scan_mode": "SWING",
        "lane_badge": "나스닥 정규장마감",
        "entry_label": "정규장 종가",
        "horizon_days": 5,
        "prob_label": "5일내 +5% 선터치(ft_5_5) 확률",
        "hold_note": "5거래일 보유 · 정규장마감 세션 기준 · 분산(타이트 손절 X)",
    },
    "kospi_intraday": {
        "label": "코스피 인트라데이 매수",
        "operational_label": "모델 매수 · 일중+컨텍스트",
        "scan_mode": "INTRADAY",
        "lane_badge": "코스피 인트라데이",
        "entry_label": "종가",
        "horizon_days": 3,
        "prob_label": "3일내 +5% 터치 확률",
        "hold_note": "3거래일 종가 보유 · 분산(타이트 손절 X)",
    },
    "kosdaq_intraday_3d_t5_vwap_guard": {
        "label": "코스닥 인트라데이 매수",
        "operational_label": "모델 매수 · 15:00 VWAP가드",
        "scan_mode": "INTRADAY",
        "lane_badge": "코스닥 인트라데이",
        "entry_label": "15:00",
        "horizon_days": 3,
        "prob_label": "3일내 +5% 터치 확률(15:00 진입·VWAP가드)",
        "hold_note": "3거래일 보유 · 분산(타이트 손절 X) · ≥30억 유동성",
    },
}


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        text = value.strip()
        return bool(text) and text.lower() not in {"none", "nan", "null"}
    return True


def _first(*values: Any) -> Any:
    for value in values:
        if _present(value):
            return value
    return None


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
        numeric = float(value)
        if math.isnan(numeric) or math.isinf(numeric):
            return None
        return numeric
    except Exception:
        return None


def _to_int(value: Any) -> int | None:
    numeric = _to_float(value)
    return int(numeric) if numeric is not None else None


def _to_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if math.isnan(float(value)) or math.isinf(float(value)):
            return None
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "t", "1", "yes", "y", "승", "성공", "hit", "target_before_stop"}:
            return True
        if text in {"false", "f", "0", "no", "n", "패", "실패", "none", "nan", "null", "stop_before_target"}:
            return False
    return None


def _text_list(value: Any, *, limit: int = 5) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        source = value
    else:
        source = [value]
    out: List[str] = []
    for item in source:
        text = str(item or "").strip()
        if text and text.lower() not in {"none", "nan", "null"} and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _action_label(row: Dict[str, Any], trade_plan: Dict[str, Any]) -> str:
    readiness = trade_plan.get("readiness_analysis") if isinstance(trade_plan.get("readiness_analysis"), dict) else {}
    judgment = readiness.get("final_buy_judgment") if isinstance(readiness.get("final_buy_judgment"), dict) else {}
    return str(
        _first(
            judgment.get("action"),
            row.get("final_action"),
            row.get("signal_label"),
            row.get("decision"),
            row.get("Decision"),
            row.get("decision_bucket"),
        )
        or "-"
    )


def _buy_premium_execution_gate(
    row: Dict[str, Any],
    admission: Dict[str, Any],
    operational_score: Dict[str, Any],
    premium_returns: Dict[str, Any],
) -> Dict[str, Any]:
    buy_premium_pct = _to_float(operational_score.get("buy_premium_pct"))
    exact_return_1d = _to_float(_first(row.get("buy_premium_return_1d_pct"), premium_returns.get("return_1d_pct")))
    exact_return_3d = _to_float(_first(row.get("buy_premium_return_3d_pct"), premium_returns.get("return_3d_pct")))
    exact_return_5d = _to_float(_first(row.get("buy_premium_return_5d_pct"), premium_returns.get("return_5d_pct")))
    exact_max_high_5d = _to_float(
        _first(
            row.get("buy_premium_max_high_return_5d_pct"),
            row.get("buy_premium_max_return_5d_pct"),
            row.get("max_high_return_5d_pct"),
        )
    )
    exact_min_low_5d = _to_float(
        _first(
            row.get("buy_premium_min_low_return_5d_pct"),
            row.get("buy_premium_min_return_5d_pct"),
            row.get("min_low_return_5d_pct"),
        )
    )
    target_hit_5d = _to_bool(_first(row.get("buy_premium_target_hit_5d"), row.get("target_hit_5d")))
    target_before_stop_5d = _to_bool(
        _first(row.get("buy_premium_target_before_stop_5d"), row.get("target_before_stop_5d"))
    )
    stop_hit_5d = _to_bool(_first(row.get("buy_premium_stop_hit_5d"), row.get("stop_hit_5d")))
    stop_before_target_5d = _to_bool(
        _first(row.get("buy_premium_stop_before_target_5d"), row.get("stop_before_target_5d"))
    )
    exact_available = any(
        value is not None
        for value in (
            exact_return_1d,
            exact_return_3d,
            exact_return_5d,
            exact_max_high_5d,
            exact_min_low_5d,
            target_hit_5d,
            target_before_stop_5d,
            stop_hit_5d,
            stop_before_target_5d,
        )
    )

    touch_rate_pct = _to_float(
        _first(
            admission.get("target_touch_win_pct"),
            admission.get("hit5_5d_pct"),
            admission.get("5d_prob"),
        )
    )
    hit10_rate_pct = _to_float(admission.get("hit10_5d_pct"))
    close_defense_5d_pct = _to_float(admission.get("close_defense_5d_pct"))
    avg_5d_pct = _to_float(
        _first(
            row.get("buy_premium_avg_5d_pct"),
            admission.get("dynamic_expected_net_avg_5d_pct"),
            premium_returns.get("base_expected_value_5d_pct"),
            admission.get("base_expected_value_5d_pct"),
            admission.get("expected_value_5d_pct"),
        )
    )
    stress_5d_pct = _to_float(
        _first(
            premium_returns.get("stress_expected_value_5d_pct"),
            admission.get("stress_expected_value_5d_pct"),
        )
    )
    stop_first_risk_pct = _to_float(admission.get("stop_first_risk_pct"))
    stop5_pct = _to_float(admission.get("stop5_pct"))
    bad_path_pct = _to_float(admission.get("bad_path_pct"))
    validation_metrics_available = any(
        value is not None
        for value in (
            touch_rate_pct,
            hit10_rate_pct,
            close_defense_5d_pct,
            avg_5d_pct,
            stress_5d_pct,
            stop_first_risk_pct,
            stop5_pct,
            bad_path_pct,
        )
    )

    touch_observed = bool(
        target_hit_5d is True
        or target_before_stop_5d is True
        or (exact_max_high_5d is not None and exact_max_high_5d >= 5.0)
    )
    touch_model_found = bool(touch_observed or (touch_rate_pct is not None and touch_rate_pct >= 55.0))
    profit_touch_5d_after_buy_premium = bool(
        target_hit_5d is True
        or (exact_max_high_5d is not None and exact_max_high_5d >= BUY_READY_TARGET_PROFIT_PCT)
        or (exact_return_5d is not None and exact_return_5d >= BUY_READY_TARGET_PROFIT_PCT)
    )
    stop_first_drawdown_within_limit = bool(
        exact_min_low_5d is not None and exact_min_low_5d >= STOP_FIRST_MAX_DRAWDOWN_PCT
    )
    bounded_stop_first_allowed = bool(
        stop_before_target_5d is True
        and profit_touch_5d_after_buy_premium
        and stop_first_drawdown_within_limit
    )

    block_reasons: List[str] = []
    scout_reasons: List[str] = []
    if touch_observed:
        scout_reasons.append("5D 안에 +5% 터치 근거가 있습니다.")
    elif touch_rate_pct is not None and touch_rate_pct >= 55.0:
        scout_reasons.append(f"과거 검증 터치율 {touch_rate_pct:.1f}% 구간입니다.")
    if hit10_rate_pct is not None and hit10_rate_pct >= 20.0:
        scout_reasons.append(f"+10% 터치율도 {hit10_rate_pct:.1f}%로 관찰됩니다.")

    if stop_before_target_5d is True and not bounded_stop_first_allowed:
        if exact_min_low_5d is None or (
            target_hit_5d is None and exact_max_high_5d is None and exact_return_5d is None
        ):
            block_reasons.append("손절 선행 허용 여부를 판단할 5D +5% 수익/최대하락 라벨이 부족합니다.")
        elif exact_min_low_5d < STOP_FIRST_MAX_DRAWDOWN_PCT:
            block_reasons.append("손절 선행 허용 범위(-10%)를 넘었습니다.")
        elif not profit_touch_5d_after_buy_premium:
            block_reasons.append("손절 선행 후 +2% 매수 기준 5D 안에 +5% 수익권에 도달하지 못했습니다.")
    if target_before_stop_5d is False and target_hit_5d is not True and exact_available and not bounded_stop_first_allowed:
        block_reasons.append("목표가가 손절보다 먼저 온 근거가 없습니다.")
    if stop_hit_5d is True and target_before_stop_5d is not True and not bounded_stop_first_allowed:
        block_reasons.append("5D 안에 손절 터치가 먼저 확인됩니다.")
    if exact_return_5d is not None and exact_return_5d < 0.0 and not profit_touch_5d_after_buy_premium:
        block_reasons.append(f"+{buy_premium_pct or DEFAULT_BUY_PREMIUM_PCT:.1f}% 매수 기준 5D 종가수익률이 음수입니다.")
    if exact_min_low_5d is not None and exact_min_low_5d < STOP_FIRST_MAX_DRAWDOWN_PCT and target_before_stop_5d is not True:
        block_reasons.append("5D 경로의 최대하락폭이 -10%보다 깊습니다.")
    if stop_first_risk_pct is not None and stop_first_risk_pct >= 30.0 and not bounded_stop_first_allowed:
        block_reasons.append(f"검증 stop-first 위험이 {stop_first_risk_pct:.1f}%로 높습니다.")
    if stop5_pct is not None and stop5_pct >= 35.0:
        block_reasons.append(f"검증 5D 손절 터치율이 {stop5_pct:.1f}%로 높습니다.")
    if bad_path_pct is not None and bad_path_pct >= 35.0:
        block_reasons.append(f"검증 bad-path 비율이 {bad_path_pct:.1f}%로 높습니다.")
    if avg_5d_pct is not None and avg_5d_pct < 0.0:
        block_reasons.append("검증 평균 기대수익이 음수입니다.")
    if close_defense_5d_pct is not None and close_defense_5d_pct < 50.0:
        block_reasons.append(f"5D 종가 방어율이 {close_defense_5d_pct:.1f}%로 낮습니다.")
    if operational_score.get("chart_only"):
        block_reasons.append("차트 편중 후보라 수급/테마/뉴스 확인이 부족합니다.")
    non_chart_avg = _to_float(operational_score.get("non_chart_avg_score"))
    if non_chart_avg is not None and non_chart_avg < 35.0:
        block_reasons.append("차트 외 근거 점수가 낮습니다.")

    has_path_success = target_before_stop_5d is True or bounded_stop_first_allowed or (
        not exact_available
        and touch_rate_pct is not None
        and touch_rate_pct >= 70.0
        and (stop_first_risk_pct is None or stop_first_risk_pct <= 20.0)
        and (stop5_pct is None or stop5_pct <= 25.0)
        and (avg_5d_pct is None or avg_5d_pct >= 0.0)
    )
    buy_ready = bool(has_path_success and not block_reasons)
    touch_scout = bool(touch_model_found and not buy_ready)
    if buy_ready:
        lane = "BUY_READY"
        label = "실매수 후보"
    elif touch_scout:
        lane = "TOUCH_SCOUT"
        label = "터치 스카우트 - 매수대기"
    elif block_reasons:
        lane = "BLOCKED_RISK"
        label = "매수 차단"
    elif validation_metrics_available or exact_available:
        lane = "NO_TOUCH_EVIDENCE"
        label = "터치 근거 부족"
    else:
        lane = "INSUFFICIENT_EVIDENCE"
        label = "근거 부족"

    why_not_buy_ready = list(block_reasons[:8])
    if not why_not_buy_ready and not buy_ready:
        why_not_buy_ready.append("상승 터치와 실매수 승격을 분리해서 추가 검증이 필요합니다.")

    return {
        "version": BUY_PREMIUM_EXECUTION_GATE_VERSION,
        "buy_premium_pct": buy_premium_pct or DEFAULT_BUY_PREMIUM_PCT,
        "lane": lane,
        "label": label,
        "buy_ready": buy_ready,
        "buy_ready_blocked": not buy_ready,
        "touch_model_found": touch_model_found,
        "touch_scout_candidate": touch_scout,
        "bounded_stop_first_allowed": bounded_stop_first_allowed,
        "profit_touch_5d_after_buy_premium": profit_touch_5d_after_buy_premium,
        "profitable_5d_after_buy_premium": profit_touch_5d_after_buy_premium,
        "stop_first_drawdown_within_limit": stop_first_drawdown_within_limit,
        "buy_ready_target_profit_pct": BUY_READY_TARGET_PROFIT_PCT,
        "stop_first_max_drawdown_pct": STOP_FIRST_MAX_DRAWDOWN_PCT,
        "exact_labels_available": exact_available,
        "validation_metrics_available": validation_metrics_available,
        "target_hit_5d": target_hit_5d,
        "target_before_stop_5d": target_before_stop_5d,
        "stop_hit_5d": stop_hit_5d,
        "stop_before_target_5d": stop_before_target_5d,
        "return_1d_pct": exact_return_1d,
        "return_3d_pct": exact_return_3d,
        "return_5d_pct": exact_return_5d,
        "max_high_return_5d_pct": exact_max_high_5d,
        "min_low_return_5d_pct": exact_min_low_5d,
        "touch_rate_pct": touch_rate_pct,
        "hit10_rate_pct": hit10_rate_pct,
        "close_defense_5d_pct": close_defense_5d_pct,
        "avg_5d_pct": avg_5d_pct,
        "stress_5d_pct": stress_5d_pct,
        "stop_first_risk_pct": stop_first_risk_pct,
        "stop5_pct": stop5_pct,
        "bad_path_pct": bad_path_pct,
        "scout_reasons": scout_reasons[:6],
        "block_reasons": block_reasons[:8],
        "why_not_buy_ready": why_not_buy_ready[:8],
        "semantics": (
            "터치 스카우트는 상승 포착용입니다. 실매수 후보는 +2% 진입가 기준 목표 선행이거나, "
            "손절 선행이 있더라도 5D 최대하락이 -10% 안쪽이고 5D 안에 +5% 이상 수익권에 도달한 경우만 의미합니다."
        ),
    }


def build_model_lane_interpretation(row: Dict[str, Any], bucket: str) -> Dict[str, Any]:
    """Interpretation for model-validated lanes (price-ML ensemble / KOSPI intraday).

    The pick IS the model's buy call (top ~1-2% per market by backtested forward
    touch-probability). It surfaces as a model BUY with an explicit entry/+5%/hold contract
    instead of being demoted to "운용 보류" for lacking the legacy flow/theme/news axes."""
    profile = LANE_PROFILE.get(bucket, LANE_PROFILE["swing_ensemble"])
    trade_plan = row.get("trade_plan") if isinstance(row.get("trade_plan"), dict) else {}
    admission = row.get("realized_expectancy_admission") if isinstance(row.get("realized_expectancy_admission"), dict) else {}
    price = row.get("price") if isinstance(row.get("price"), dict) else {}
    theme = row.get("theme") if isinstance(row.get("theme"), dict) else {}
    alignment = row.get("selection_alignment") if isinstance(row.get("selection_alignment"), dict) else {}

    entry = _to_float(_first(trade_plan.get("entry_reference_price"), row.get("entry_reference_price")))
    target = _to_float(_first(trade_plan.get("target_price"), row.get("target_price")))
    if target is None and entry is not None:
        target = round(entry * 1.05, 2)
    target_tp = _to_float(_first(trade_plan.get("target_tp_pct"), row.get("target_tp_pct"))) or 5.0
    hd = profile["horizon_days"]
    prob = _to_float(_first(admission.get(f"{hd}d_prob"), admission.get("3d_prob"), admission.get("5d_prob"),
                            row.get("model_hit_prob"), row.get("buy_score")))
    prob01 = prob if (prob is not None and prob <= 1.0) else (prob / 100.0 if prob is not None else None)
    prob_pct = round(prob01 * 100, 1) if prob01 is not None else None
    hold_days = _to_int(_first(trade_plan.get("hold_days"), hd))
    thesis = _first(row.get("selection_thesis"), trade_plan.get("hold_note"))
    section = str(_first(alignment.get("analysis_section"), row.get("analysis_section"), "Top5"))
    section_rank = _to_int(_first(alignment.get("analysis_section_rank"), row.get("analysis_section_rank"), row.get("rank")))

    return {
        "version": INTERPRETATION_VERSION,
        "model_lane": bucket,
        "run_id": row.get("run_id"),
        "ticker": _first(row.get("ticker"), row.get("Ticker"), row.get("symbol")),
        "stock_name": _first(row.get("stock_name"), row.get("Name"), row.get("name"),
                             resolve_name(_first(row.get("ticker"), row.get("Ticker"), row.get("symbol")))),
        "market": _first(row.get("market"), row.get("Market")),
        "section": section,
        "section_rank": section_rank,
        "display_status": "VISIBLE",
        "action_label": profile["label"],
        "scan_mode": _first(profile.get("scan_mode"), row.get("scan_mode")),
        "lane_badge": profile.get("lane_badge"),
        "entry_label": profile.get("entry_label"),
        "signal_label": row.get("signal_label"),
        "decision": _first(row.get("decision"), row.get("decision_bucket")),
        "entry_reference_price": entry,
        "target_price": target,
        "stop_price": None,
        "target_tp_pct": target_tp,
        "stop_sl_pct": None,
        "stop_display_source": "model_lane_no_tight_stop",
        "hold_days": hold_days,
        "hold_note": profile["hold_note"],
        "model_prob_label": profile["prob_label"],
        "model_hit_prob_pct": prob_pct,
        "realized_expectancy_3d_prob": prob01 if hd == 3 else None,
        "realized_expectancy_5d_prob": prob01 if hd == 5 else None,
        "selection_thesis": thesis,
        "primary_theme": _first(theme.get("primary_theme"), row.get("primary_theme")),
        "day_change_pct": _to_float(_first(row.get("day_change_pct"), price.get("day_change_pct"))),
        "buy_score": _to_float(_first(row.get("buy_score"), row.get("decision_score"))),
        "operational_action_level": "MODEL_BUY",
        "operational_action_label": profile["operational_label"],
        "operational_total_score": prob_pct,
        "operational_non_chart_avg_score": None,
        "chart_only_candidate": False,
        "buy_ready": True,
        "buy_ready_blocked": False,
        "buy_ready_block_reasons": [],
        "touch_model_found": True,
        "touch_scout_candidate": False,
        "touch_vs_buy_ready_explanation": (
            f"{profile['prob_label']} 기준 모델 매수 후보입니다. 진입=종가, 목표 +{target_tp:.0f}%, "
            f"{profile['hold_note']}. 차트외 수급/테마 점수 게이트는 이 모델 레인에 적용하지 않습니다."
        ),
    }


def build_candidate_interpretation(row: Dict[str, Any]) -> Dict[str, Any]:
    row = row if isinstance(row, dict) else {}
    _bucket = str(_first(row.get("decision_bucket"), row.get("bucket"), "") or "").strip()
    if _bucket in MODEL_VALIDATED_LANES:
        return build_model_lane_interpretation(row, _bucket)
    alignment = row.get("selection_alignment") if isinstance(row.get("selection_alignment"), dict) else {}
    display_contract = row.get("display_contract") if isinstance(row.get("display_contract"), dict) else {}
    admission = row.get("realized_expectancy_admission") if isinstance(row.get("realized_expectancy_admission"), dict) else {}
    prediction = row.get("prediction") if isinstance(row.get("prediction"), dict) else {}
    trade_plan = row.get("trade_plan") if isinstance(row.get("trade_plan"), dict) else {}
    readiness_contract = row.get("entry_readiness_contract") if isinstance(row.get("entry_readiness_contract"), dict) else {}
    if not readiness_contract and isinstance(trade_plan.get("readiness_analysis"), dict):
        nested_readiness = trade_plan["readiness_analysis"]
        readiness_contract = nested_readiness.get("contract") if isinstance(nested_readiness.get("contract"), dict) else {}
    execution_stop = row.get("execution_stop") if isinstance(row.get("execution_stop"), dict) else {}
    if not execution_stop and isinstance(trade_plan.get("execution_stop"), dict):
        execution_stop = trade_plan["execution_stop"]
    policy_metadata = row.get("policy_metadata") if isinstance(row.get("policy_metadata"), dict) else {}
    theme = row.get("theme") if isinstance(row.get("theme"), dict) else {}
    price = row.get("price") if isinstance(row.get("price"), dict) else {}
    data_quality = row.get("candidate_data_quality") if isinstance(row.get("candidate_data_quality"), dict) else {}
    operational_score = (
        row.get("operational_score_axes")
        if isinstance(row.get("operational_score_axes"), dict)
        else build_operational_candidate_score(row, buy_premium_pct=DEFAULT_BUY_PREMIUM_PCT)
    )
    premium_returns = (
        operational_score.get("return_after_buy_premium_pct")
        if isinstance(operational_score.get("return_after_buy_premium_pct"), dict)
        else {}
    )
    execution_gate = _buy_premium_execution_gate(row, admission, operational_score, premium_returns)

    section = str(_first(alignment.get("analysis_section"), row.get("_analysis_section"), row.get("section"), "Top5"))
    section_rank = _to_int(_first(alignment.get("analysis_section_rank"), row.get("_analysis_section_rank"), row.get("section_rank"), row.get("rank")))
    original_rank = _to_int(_first(display_contract.get("original_scan_rank"), alignment.get("raw_scan_rank"), row.get("_raw_scan_rank"), row.get("Rank"), row.get("rank")))
    planner_rank = _to_int(_first(display_contract.get("planner_priority_rank"), alignment.get("planner_priority_rank"), row.get("priority_rank"), row.get("rank")))

    warnings = _text_list(row.get("data_warnings"), limit=6)
    warnings.extend(item for item in _text_list(data_quality.get("visible_warnings"), limit=6) if item not in warnings)
    warnings.extend(item for item in _text_list(row.get("quality_flags"), limit=6) if item not in warnings)
    risk_reasons = _text_list(row.get("risk_flags"), limit=6)
    risk_reasons.extend(item for item in _text_list(row.get("rationale"), limit=6) if item not in risk_reasons)

    return {
        "version": INTERPRETATION_VERSION,
        "run_id": row.get("run_id"),
        "ticker": _first(row.get("ticker"), row.get("Ticker"), row.get("티커"), row.get("symbol")),
        "stock_name": _first(row.get("stock_name"), row.get("Name"), row.get("종목명"), row.get("name")),
        "market": _first(row.get("market"), row.get("Market")),
        "section": section,
        "section_rank": section_rank,
        "original_rank": original_rank,
        "planner_rank": planner_rank,
        "source_order": _first(alignment.get("source_order"), row.get("_source_order")),
        "display_status": _first(display_contract.get("display_status"), "VISIBLE"),
        "action_label": _action_label(row, trade_plan),
        "signal_label": row.get("signal_label"),
        "decision": _first(row.get("decision"), row.get("Decision"), row.get("decision_bucket")),
        "entry_reference_price": _to_float(_first(trade_plan.get("entry_reference_price"), row.get("entry_reference_price"), row.get("Entry"), row.get("매수가(-2%)"))),
        "target_price": _to_float(_first(trade_plan.get("target_price"), row.get("target_price"))),
        "stop_price": _to_float(_first(execution_stop.get("display_stop_price"), trade_plan.get("stop_price"), row.get("stop_price"))),
        "target_tp_pct": _to_float(_first(trade_plan.get("target_tp_pct"), row.get("target_tp_pct"), row.get("TP"))),
        "stop_sl_pct": _to_float(_first(execution_stop.get("display_stop_sl_pct"), trade_plan.get("stop_sl_pct"), row.get("stop_sl_pct"), row.get("SL"))),
        "stop_display_source": execution_stop.get("display_stop_source"),
        "stop_conflict": execution_stop.get("stop_conflict"),
        "realized_expectancy_3d_prob": _to_float(_first(admission.get("3d_prob"), prediction.get("realized_expectancy_3d_prob"))),
        "realized_expectancy_5d_prob": _to_float(_first(admission.get("5d_prob"), prediction.get("realized_expectancy_5d_prob"))),
        "expected_value_3d_pct": _to_float(admission.get("expected_value_3d_pct")),
        "expected_value_5d_pct": _to_float(admission.get("expected_value_5d_pct")),
        "base_expected_value_3d_pct": _to_float(_first(admission.get("base_expected_value_3d_pct"), admission.get("expected_value_3d_pct"))),
        "base_expected_value_5d_pct": _to_float(_first(admission.get("base_expected_value_5d_pct"), admission.get("expected_value_5d_pct"))),
        "stress_expected_value_3d_pct": _to_float(admission.get("stress_expected_value_3d_pct")),
        "stress_expected_value_5d_pct": _to_float(admission.get("stress_expected_value_5d_pct")),
        "ranking_score_5d": _to_float(_first(admission.get("ranking_score_5d"), prediction.get("ranking_score_5d"))),
        "stop_first_risk_pct": _to_float(admission.get("stop_first_risk_pct")),
        "policy_version": _first(admission.get("policy_version"), prediction.get("admission_policy_version"), policy_metadata.get("active_policy_version")),
        "data_warning_count": len(warnings),
        "data_warnings": warnings,
        "data_quality_level": data_quality.get("display_warning_level"),
        "data_required_present_pct": data_quality.get("required_present_pct"),
        "risk_reasons": risk_reasons,
        "primary_theme": _first(theme.get("primary_theme"), row.get("primary_theme"), row.get("테마"), row.get("Theme")),
        "day_change_pct": _to_float(_first(row.get("day_change_pct"), row.get("day_return_pct"), row.get("전일비"), price.get("day_change_pct"))),
        "loss_risk_score": _to_float(_first(row.get("loss_risk_score"), row.get("Loss Risk"))),
        "buy_score": _to_float(_first(row.get("buy_score"), row.get("decision_score"), row.get("Decision Score"), row.get("score"))),
        "stock_quality_grade": _first(readiness_contract.get("stock_quality_grade"), row.get("stock_quality_grade")),
        "upside_room_grade": _first(readiness_contract.get("upside_room_grade"), row.get("upside_room_grade")),
        "entry_timing_grade": _first(readiness_contract.get("entry_timing_grade"), row.get("entry_timing_grade")),
        "chase_risk_level": _first(readiness_contract.get("chase_risk_level"), row.get("chase_risk_level")),
        "chase_risk_reasons": _text_list(_first(readiness_contract.get("chase_risk_reasons"), row.get("chase_risk_reasons")), limit=10),
        "exclusion_risk_level": _first(readiness_contract.get("exclusion_risk_level"), row.get("exclusion_risk_level")),
        "entry_readiness_action": _first(readiness_contract.get("final_action"), row.get("final_action")),
        "entry_readiness_reason_codes": _text_list(readiness_contract.get("action_reason_codes"), limit=10),
        "operational_score_axes": operational_score,
        "operational_action_level": operational_score.get("action_level"),
        "operational_action_label": operational_score.get("action_label"),
        "operational_total_score": _to_float(operational_score.get("total_score")),
        "operational_non_chart_avg_score": _to_float(operational_score.get("non_chart_avg_score")),
        "chart_dominance_pct": _to_float(operational_score.get("chart_dominance_pct")),
        "chart_only_candidate": bool(operational_score.get("chart_only")),
        "buy_premium_pct": _to_float(operational_score.get("buy_premium_pct")),
        "buy_premium_return_1d_pct": _to_float(premium_returns.get("return_1d_pct")),
        "buy_premium_return_3d_pct": _to_float(premium_returns.get("return_3d_pct")),
        "buy_premium_return_5d_pct": _to_float(premium_returns.get("return_5d_pct")),
        "buy_premium_base_expected_value_5d_pct": _to_float(premium_returns.get("base_expected_value_5d_pct")),
        "buy_premium_stress_expected_value_5d_pct": _to_float(premium_returns.get("stress_expected_value_5d_pct")),
        "buy_premium_execution_gate": execution_gate,
        "touch_model_found": bool(execution_gate.get("touch_model_found")),
        "touch_scout_candidate": bool(execution_gate.get("touch_scout_candidate")),
        "buy_ready": bool(execution_gate.get("buy_ready")),
        "buy_ready_blocked": bool(execution_gate.get("buy_ready_blocked")),
        "buy_ready_block_reasons": execution_gate.get("block_reasons") or [],
        "touch_vs_buy_ready_explanation": execution_gate.get("semantics"),
    }


def build_candidate_interpretations(rows: List[Dict[str, Any]], *, limit: int | None = None) -> List[Dict[str, Any]]:
    source = [row for row in rows or [] if isinstance(row, dict)]
    if limit is not None:
        source = source[: max(int(limit or 0), 0)]
    return [build_candidate_interpretation(row) for row in source]
