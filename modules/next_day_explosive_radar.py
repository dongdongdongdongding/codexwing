from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List


RADAR_VERSION = "kr_next_day_explosive_radar_v1"


def _num(value: Any) -> float | None:
    try:
        if value in (None, "", "nan", "None"):
            return None
        result = float(str(value).replace("%", "").replace(",", "").strip())
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except Exception:
        return None


def _market(row: Dict[str, Any]) -> str:
    market = str(row.get("market") or "").upper()
    ticker = str(row.get("ticker") or "").upper()
    if market in {"KOSPI", "KOSDAQ"}:
        return market
    if ticker.endswith(".KS"):
        return "KOSPI"
    if ticker.endswith(".KQ"):
        return "KOSDAQ"
    return market or "-"


def build_next_day_radar_candidate(row: Dict[str, Any]) -> Dict[str, Any]:
    row = row if isinstance(row, dict) else {}
    score = 0.0
    reasons: List[str] = []
    unavailable: List[str] = []

    volume_ratio = _num(row.get("volume_ratio") or row.get("volume_ratio_20d"))
    if volume_ratio is None:
        unavailable.append("volume_ratio")
    elif volume_ratio >= 2.5:
        score += 18
        reasons.append("volume_acceleration")
    elif volume_ratio >= 1.5:
        score += 10
        reasons.append("volume_reaccumulation")

    day_change = _num(row.get("day_change_pct") or row.get("day_return_pct"))
    if day_change is None:
        unavailable.append("close_location_proxy")
    elif 0 <= day_change <= 6:
        score += 12
        reasons.append("constructive_close")
    elif day_change > 12:
        score -= 10
        reasons.append("overextended_close")

    expected_1d = _num(row.get("expected_return_1d_pct"))
    if expected_1d is None:
        unavailable.append("expected_return_1d_pct")
    elif expected_1d >= 3:
        score += 14
        reasons.append("positive_1d_model_edge")

    prob_clean = _num(row.get("prob_clean") or row.get("_prob_clean"))
    if prob_clean is None:
        unavailable.append("prob_clean")
    elif prob_clean >= 45:
        score += 10
        reasons.append("clean_probability_support")

    theme_avg = _num(row.get("theme_day_avg_decision_score") or row.get("_theme_day_avg_decision_score"))
    if theme_avg is None:
        unavailable.append("same_scan_theme_strength")
    elif theme_avg >= 70:
        score += 8
        reasons.append("theme_strength")
    elif theme_avg <= 55:
        score -= 6
        reasons.append("weak_theme_tape")

    gate = str(row.get("market_gate") or "").upper()
    if gate == "RED":
        score -= 12
        reasons.append("market_gate_red")
    elif gate == "GREEN":
        score += 5
        reasons.append("market_gate_green")
    elif not gate:
        unavailable.append("market_gate")

    score = max(0.0, min(100.0, 45.0 + score))
    prob_5 = max(1.0, min(85.0, score * 0.72))
    prob_10 = max(0.5, min(55.0, (score - 15.0) * 0.42))
    return {
        "version": RADAR_VERSION,
        "ticker": row.get("ticker"),
        "market": _market(row),
        "radar_score": round(score, 6),
        "next_day_plus5_prob": round(prob_5, 6),
        "next_day_plus10_prob": round(prob_10, 6),
        "feature_reasons": reasons,
        "unavailable_features": sorted(set(unavailable)),
        "production_enabled": False,
    }


def select_radar_candidates(rows: Iterable[Dict[str, Any]], *, limit: int = 5) -> List[Dict[str, Any]]:
    scored = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        radar = build_next_day_radar_candidate(row)
        scored.append({**row, "next_day_radar": radar})
    return sorted(scored, key=lambda row: (row["next_day_radar"]["radar_score"], _num(row.get("relative_rank_score")) or 0), reverse=True)[: int(limit)]


def build_next_day_radar_records(rows: Iterable[Dict[str, Any]], *, limit: int = 5) -> List[Dict[str, Any]]:
    """Build display-only next-day explosive radar records.

    The radar is intentionally shadow-only. It gives operators a separate
    short-horizon surge watchlist without replacing Top5/Exception output.
    """
    records: List[Dict[str, Any]] = []
    for rank, row in enumerate(select_radar_candidates(rows, limit=limit), start=1):
        radar = row.get("next_day_radar") if isinstance(row.get("next_day_radar"), dict) else build_next_day_radar_candidate(row)
        display_row = {
            **row,
            "next_day_radar": radar,
            "_analysis_section": "별도 급등 레이더",
            "_analysis_section_rank": rank,
            "decision": "NEXT_DAY_RADAR",
            "final_action": "별도 급등 관찰",
            "entry_condition_text": "익일 장초반 거래량 유지와 당일 저점 이탈 없음 확인",
            "stop_condition_text": "장초반 거래량 꺼짐 또는 전일 기준가 이탈",
        }
        records.append(display_row)
    return records


def backtest_next_day_radar(rows: Iterable[Dict[str, Any]], *, top_n: int = 5) -> Dict[str, Any]:
    row_list = [row for row in rows or [] if isinstance(row, dict)]
    groups: Dict[tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in row_list:
        groups[(str(row.get("run_id") or "ALL"), _market(row))].append(row)

    selected: List[Dict[str, Any]] = []
    baseline: List[Dict[str, Any]] = []
    for _, group in groups.items():
        selected.extend(select_radar_candidates(group, limit=top_n))
        baseline.extend(sorted(group, key=lambda row: _num(row.get("priority_rank")) or 9999)[:top_n])

    def metrics(rows_: List[Dict[str, Any]]) -> Dict[str, Any]:
        returns = [_num(row.get("return_1d_pct")) for row in rows_]
        clean = [value for value in returns if value is not None]
        if not clean:
            return {"rows": len(rows_), "n": 0, "plus5_precision_pct": None, "plus10_precision_pct": None, "avg_return_1d_pct": None, "worst_return_1d_pct": None, "false_positive_pct": None}
        plus5 = sum(1 for value in clean if value >= 5)
        plus10 = sum(1 for value in clean if value >= 10)
        false_pos = sum(1 for value in clean if value < 0)
        return {
            "rows": len(rows_),
            "n": len(clean),
            "plus5_precision_pct": round(plus5 / len(clean) * 100.0, 4),
            "plus10_precision_pct": round(plus10 / len(clean) * 100.0, 4),
            "avg_return_1d_pct": round(sum(clean) / len(clean), 6),
            "worst_return_1d_pct": round(min(clean), 6),
            "false_positive_pct": round(false_pos / len(clean) * 100.0, 4),
        }

    return {
        "version": RADAR_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_rows": len(row_list),
        "top_n": int(top_n),
        "radar": metrics(selected),
        "baseline_priority": metrics(baseline),
        "promotion_status": "shadow_only",
        "promotion_rule": "Promote only after out-of-sample radar precision/avg/worst materially beats baseline priority.",
        "sample_candidates": [row.get("next_day_radar") for row in selected[:20]],
    }


__all__ = [
    "RADAR_VERSION",
    "backtest_next_day_radar",
    "build_next_day_radar_candidate",
    "build_next_day_radar_records",
    "select_radar_candidates",
]
