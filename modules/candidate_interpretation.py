from __future__ import annotations

import math
from typing import Any, Dict, List


INTERPRETATION_VERSION = "candidate_interpretation_v1"


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


def build_candidate_interpretation(row: Dict[str, Any]) -> Dict[str, Any]:
    row = row if isinstance(row, dict) else {}
    alignment = row.get("selection_alignment") if isinstance(row.get("selection_alignment"), dict) else {}
    display_contract = row.get("display_contract") if isinstance(row.get("display_contract"), dict) else {}
    admission = row.get("realized_expectancy_admission") if isinstance(row.get("realized_expectancy_admission"), dict) else {}
    prediction = row.get("prediction") if isinstance(row.get("prediction"), dict) else {}
    trade_plan = row.get("trade_plan") if isinstance(row.get("trade_plan"), dict) else {}
    policy_metadata = row.get("policy_metadata") if isinstance(row.get("policy_metadata"), dict) else {}
    theme = row.get("theme") if isinstance(row.get("theme"), dict) else {}
    price = row.get("price") if isinstance(row.get("price"), dict) else {}
    data_quality = row.get("candidate_data_quality") if isinstance(row.get("candidate_data_quality"), dict) else {}

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
        "stop_price": _to_float(_first(trade_plan.get("stop_price"), row.get("stop_price"))),
        "target_tp_pct": _to_float(_first(trade_plan.get("target_tp_pct"), row.get("target_tp_pct"), row.get("TP"))),
        "stop_sl_pct": _to_float(_first(trade_plan.get("stop_sl_pct"), row.get("stop_sl_pct"), row.get("SL"))),
        "realized_expectancy_3d_prob": _to_float(_first(admission.get("3d_prob"), prediction.get("realized_expectancy_3d_prob"))),
        "realized_expectancy_5d_prob": _to_float(_first(admission.get("5d_prob"), prediction.get("realized_expectancy_5d_prob"))),
        "expected_value_3d_pct": _to_float(admission.get("expected_value_3d_pct")),
        "expected_value_5d_pct": _to_float(admission.get("expected_value_5d_pct")),
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
    }


def build_candidate_interpretations(rows: List[Dict[str, Any]], *, limit: int | None = None) -> List[Dict[str, Any]]:
    source = [row for row in rows or [] if isinstance(row, dict)]
    if limit is not None:
        source = source[: max(int(limit or 0), 0)]
    return [build_candidate_interpretation(row) for row in source]
