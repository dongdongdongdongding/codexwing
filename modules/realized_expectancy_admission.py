from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


ADMISSION_POLICY_VERSION = "kr_realized_expectancy_admission_v1"
ADMISSION_HORIZONS = (3, 5)


@dataclass(frozen=True)
class SectionCalibration:
    market: str
    section: str
    source: str
    sample_size: int
    section_win_3d_pct: float
    section_win_5d_pct: float
    avg_return_3d_pct: float
    avg_return_5d_pct: float
    min_return_3d_pct: float
    min_return_5d_pct: float
    max_return_3d_pct: float
    max_return_5d_pct: float
    stop_first_risk_pct: float


DEFAULT_CALIBRATIONS: Dict[tuple, SectionCalibration] = {
    ("KOSPI", "Top5"): SectionCalibration("KOSPI", "Top5", "validated_profile_default", 55, 62.0, 80.0, 4.2, 8.99, -6.0, -8.0, 18.0, 29.0, 22.0),
    ("KOSPI", "Exception Leader"): SectionCalibration("KOSPI", "Exception Leader", "validated_profile_default", 45, 66.0, 86.7, 4.8, 8.88, -5.5, -7.0, 20.0, 31.0, 18.0),
    ("KOSPI", "Shadow"): SectionCalibration("KOSPI", "Shadow", "shadow_observation_default", 30, 58.0, 72.0, 3.2, 6.4, -6.5, -8.5, 15.0, 24.0, 25.0),
    ("KOSDAQ", "Top5"): SectionCalibration("KOSDAQ", "Top5", "validated_profile_default", 29, 56.0, 65.5, 3.4, 7.35, -8.0, -10.0, 19.0, 35.0, 30.0),
    ("KOSDAQ", "Exception Leader"): SectionCalibration("KOSDAQ", "Exception Leader", "validated_profile_default", 13, 55.0, 69.2, 2.6, 3.04, -10.0, -12.0, 16.0, 25.0, 34.0),
    ("KOSDAQ", "Shadow"): SectionCalibration("KOSDAQ", "Shadow", "shadow_observation_default", 20, 54.0, 63.0, 2.8, 5.2, -8.5, -11.0, 17.0, 27.0, 32.0),
}


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value in (None, "", "nan", "None"):
            return default
        result = float(str(value).replace("%", "").replace(",", "").strip())
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except Exception:
        return default


def _text(value: Any) -> str:
    return str(value or "").strip()


def _upper(value: Any) -> str:
    return _text(value).upper()


def normalize_market(value: Any, ticker: Any = "") -> str:
    market = _upper(value)
    symbol = _upper(ticker)
    if market in {"KOSPI", "KOSDAQ"}:
        return market
    if symbol.endswith(".KS"):
        return "KOSPI"
    if symbol.endswith(".KQ"):
        return "KOSDAQ"
    return market


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def normalize_section(value: Any) -> str:
    text = _text(value)
    upper = text.upper()
    if "EXCEPTION" in upper or "익셉션" in text:
        return "Exception Leader"
    if "SHADOW" in upper or "쉐도우" in text:
        return "Shadow"
    return "Top5"


def _row_value(row: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row and row.get(key) not in (None, ""):
            return row.get(key)
    snapshot = row.get("feature_snapshot") if isinstance(row.get("feature_snapshot"), dict) else {}
    for key in keys:
        if key in snapshot and snapshot.get(key) not in (None, ""):
            return snapshot.get(key)
    return None


def calibration_for(market: Any, section: Any, calibrations: Optional[Dict[tuple, SectionCalibration]] = None) -> Optional[SectionCalibration]:
    market_key = normalize_market(market)
    section_key = normalize_section(section)
    table = calibrations or DEFAULT_CALIBRATIONS
    return table.get((market_key, section_key))


def _candidate_probability_anchor(row: Dict[str, Any], fallback: float) -> float:
    values = [
        _safe_float(_row_value(row, "prob_clean", "_prob_clean")),
        _safe_float(_row_value(row, "phase25_prob")),
        _safe_float(_row_value(row, "phase25_shadow_prob")),
        _safe_float(_row_value(row, "ml_prob", "prob_5")),
    ]
    clean = [value for value in values if value is not None and value > 0.0]
    if not clean:
        return float(fallback)
    return sum(clean) / len(clean)


def _momentum_score(row: Dict[str, Any]) -> float:
    trend = _upper(_row_value(row, "trend", "real_trend", "Trend", "추세"))
    volume = _safe_float(_row_value(row, "volume_ratio", "volume_ratio_20d", "volume", "Volume"), 1.0) or 1.0
    day_change = _safe_float(_row_value(row, "day_change_pct", "day_return_pct", "전일비"), 0.0) or 0.0
    position = _upper(_row_value(row, "position", "Position"))
    score = 0.0
    if trend == "UP":
        score += 8.0
    elif trend == "DOWN":
        score -= 8.0
    if volume >= 2.0:
        score += 7.0
    elif volume >= 1.2:
        score += 4.0
    elif volume < 0.6:
        score -= 4.0
    if 0.0 < day_change <= 8.0:
        score += 3.0
    elif day_change > 12.0:
        score -= 5.0
    elif day_change < -4.0:
        score -= 4.0
    if "RISING" in position:
        score += 3.0
    if "PEAK" in position:
        score -= 5.0
    return _clamp(score, -15.0, 20.0)


def build_realized_expectancy_admission(
    row: Dict[str, Any],
    *,
    market: Any = "",
    section: Any = "",
    calibrations: Optional[Dict[tuple, SectionCalibration]] = None,
) -> Dict[str, Any]:
    row = row if isinstance(row, dict) else {}
    market_key = normalize_market(market or _row_value(row, "market", "Market"), _row_value(row, "ticker", "Ticker", "티커"))
    section_key = normalize_section(section or _row_value(row, "_analysis_section", "analysis_section", "section"))
    calibration = calibration_for(market_key, section_key, calibrations)
    if calibration is None:
        return {
            "policy_version": ADMISSION_POLICY_VERSION,
            "available": False,
            "unavailable_reason": f"missing_calibration:{market_key or '-'}:{section_key}",
            "market": market_key,
            "section": section_key,
        }

    expected_edge = _safe_float(_row_value(row, "expected_edge_score"), 0.0) or 0.0
    expected_3d = _safe_float(_row_value(row, "expected_return_3d_pct"), 0.0) or 0.0
    expected_5d = _safe_float(_row_value(row, "expected_return_5d_pct"), expected_3d) or expected_3d
    decision_score = _safe_float(_row_value(row, "decision_score", "Decision Score", "score"), 50.0) or 50.0
    loss_risk = _safe_float(_row_value(row, "loss_risk_score"), 50.0) or 50.0
    section_rank = _safe_float(_row_value(row, "_analysis_section_rank", "section_rank", "priority_rank", "rank"), 999.0) or 999.0
    rank_prior = _clamp((6.0 - section_rank) * 2.2, -4.0, 11.0)
    feature_evidence_count = sum(
        1
        for value in [
            _row_value(row, "prob_clean", "_prob_clean", "phase25_prob", "phase25_shadow_prob", "ml_prob", "prob_5"),
            _row_value(row, "expected_edge_score"),
            _row_value(row, "loss_risk_score"),
            _row_value(row, "trend", "real_trend", "Trend", "추세"),
            _row_value(row, "volume_ratio", "volume_ratio_20d", "volume", "Volume"),
        ]
        if value not in (None, "", "nan", "None")
    )
    momentum = _momentum_score(row)
    anchor3 = _candidate_probability_anchor(row, calibration.section_win_3d_pct)
    anchor5 = _candidate_probability_anchor(row, calibration.section_win_5d_pct)
    edge_adjust = _clamp(expected_edge * 1.1, -12.0, 14.0)
    score_adjust = _clamp((decision_score - 70.0) * 0.12, -6.0, 6.0)
    loss_adjust = _clamp((loss_risk - 45.0) * 0.20, -5.0, 12.0)
    stop_first_risk = _clamp(calibration.stop_first_risk_pct + loss_adjust * 1.8 - momentum * 0.25, 5.0, 85.0)
    prob3 = _clamp(calibration.section_win_3d_pct * 0.45 + anchor3 * 0.35 + momentum * 0.65 + edge_adjust + score_adjust - loss_adjust, 1.0, 99.0)
    prob5 = _clamp(calibration.section_win_5d_pct * 0.45 + anchor5 * 0.35 + momentum * 0.55 + edge_adjust + score_adjust - loss_adjust, 1.0, 99.0)
    avg3 = calibration.avg_return_3d_pct + expected_3d * 0.35 + momentum * 0.08 + expected_edge * 0.18 - loss_adjust * 0.08
    avg5 = calibration.avg_return_5d_pct + expected_5d * 0.35 + momentum * 0.10 + expected_edge * 0.20 - loss_adjust * 0.10
    ev3 = prob3 / 100.0 * avg3 + (1.0 - prob3 / 100.0) * calibration.min_return_3d_pct
    ev5 = prob5 / 100.0 * avg5 + (1.0 - prob5 / 100.0) * calibration.min_return_5d_pct
    ranking3 = _clamp(prob3 * 0.48 + ev3 * 5.0 + momentum * 0.8 + rank_prior - stop_first_risk * 0.30, 0.0, 100.0)
    ranking5 = _clamp(prob5 * 0.48 + ev5 * 5.0 + momentum * 0.8 + rank_prior - stop_first_risk * 0.30, 0.0, 100.0)
    if feature_evidence_count < 2:
        rank_fallback_score = _clamp(100.0 - section_rank, 0.0, 100.0)
        ranking3 = rank_fallback_score
        ranking5 = rank_fallback_score
    if ranking5 >= 70.0 and stop_first_risk <= 28.0:
        action = "realized_expectancy_leader"
    elif ranking5 >= 58.0:
        action = "realized_expectancy_watch"
    elif stop_first_risk >= 45.0 or ev5 < 0.0:
        action = "realized_expectancy_risk"
    else:
        action = "realized_expectancy_neutral"
    return {
        "policy_version": ADMISSION_POLICY_VERSION,
        "available": True,
        "market": market_key,
        "section": section_key,
        "calibration": asdict(calibration),
        "calibration_source": calibration.source,
        "sample_size": calibration.sample_size,
        "section_win_3d_pct": calibration.section_win_3d_pct,
        "section_win_5d_pct": calibration.section_win_5d_pct,
        "avg_return_3d_pct": round(avg3, 6),
        "avg_return_5d_pct": round(avg5, 6),
        "min_return_3d_pct": calibration.min_return_3d_pct,
        "min_return_5d_pct": calibration.min_return_5d_pct,
        "max_return_3d_pct": calibration.max_return_3d_pct,
        "max_return_5d_pct": calibration.max_return_5d_pct,
        "stop_first_risk_pct": round(stop_first_risk, 6),
        "3d_prob": round(prob3, 6),
        "5d_prob": round(prob5, 6),
        "ranking_score_3d": round(ranking3, 6),
        "ranking_score_5d": round(ranking5, 6),
        "expected_value_3d_pct": round(ev3, 6),
        "expected_value_5d_pct": round(ev5, 6),
        "expected_value_band": {
            "low_3d_pct": calibration.min_return_3d_pct,
            "base_3d_pct": round(ev3, 6),
            "high_3d_pct": calibration.max_return_3d_pct,
            "low_5d_pct": calibration.min_return_5d_pct,
            "base_5d_pct": round(ev5, 6),
            "high_5d_pct": calibration.max_return_5d_pct,
        },
        "action_label_input": action,
        "trace": {
            "probability_anchor_3d": round(anchor3, 6),
            "probability_anchor_5d": round(anchor5, 6),
            "expected_edge_score": round(expected_edge, 6),
            "expected_return_3d_pct": round(expected_3d, 6),
            "expected_return_5d_pct": round(expected_5d, 6),
            "decision_score": round(decision_score, 6),
            "loss_risk_score": round(loss_risk, 6),
            "feature_evidence_count": feature_evidence_count,
            "section_rank": round(section_rank, 6),
            "rank_prior": round(rank_prior, 6),
            "momentum_score": round(momentum, 6),
        },
    }


def enrich_rows_with_realized_expectancy(
    rows: Iterable[Dict[str, Any]],
    *,
    market: Any = "",
    calibrations: Optional[Dict[tuple, SectionCalibration]] = None,
) -> List[Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        copy = dict(row)
        section = copy.get("_analysis_section") or copy.get("analysis_section") or copy.get("section")
        copy["realized_expectancy_admission"] = build_realized_expectancy_admission(
            copy,
            market=market or copy.get("market"),
            section=section,
            calibrations=calibrations,
        )
        enriched.append(copy)
    return enriched


def sort_by_realized_expectancy(rows: Iterable[Dict[str, Any]], horizon: int = 5) -> List[Dict[str, Any]]:
    key_name = f"ranking_score_{int(horizon)}d"
    return sorted(
        [row for row in rows or [] if isinstance(row, dict)],
        key=lambda row: (
            _safe_float((row.get("realized_expectancy_admission") or {}).get(key_name), -1.0) or -1.0,
            -(_safe_float(row.get("_analysis_section_rank") or row.get("rank") or row.get("priority_rank"), 9999.0) or 9999.0),
        ),
        reverse=True,
    )


def _metrics(values: List[float]) -> Dict[str, Any]:
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not clean:
        return {"n": 0, "win_pct": None, "avg_pct": None, "min_pct": None, "max_pct": None}
    return {
        "n": len(clean),
        "win_pct": round(sum(1 for value in clean if value > 0.0) / len(clean) * 100.0, 4),
        "avg_pct": round(sum(clean) / len(clean), 6),
        "min_pct": round(min(clean), 6),
        "max_pct": round(max(clean), 6),
    }


def compare_original_vs_expectancy_order(rows: Iterable[Dict[str, Any]], *, top_n: int = 5) -> Dict[str, Any]:
    row_list = [row for row in rows or [] if isinstance(row, dict)]
    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for row in row_list:
        key = (
            str(row.get("run_id") or "ALL"),
            normalize_market(row.get("market") or "-", row.get("ticker")),
            normalize_section(row.get("section") or row.get("_analysis_section") or "Top5"),
        )
        groups.setdefault(key, []).append(row)
    original: List[Dict[str, Any]] = []
    by_expectancy: List[Dict[str, Any]] = []
    for _, group in sorted(groups.items()):
        original.extend(sorted(group, key=lambda row: _safe_float(row.get("section_rank") or row.get("priority_rank"), 9999.0) or 9999.0)[:top_n])
        by_expectancy.extend(sort_by_realized_expectancy(enrich_rows_with_realized_expectancy(group), horizon=5)[:top_n])

    def summarize(selected: List[Dict[str, Any]], label: str) -> Dict[str, Any]:
        ret3 = _metrics([_safe_float(row.get("return_3d_pct")) for row in selected])
        ret5 = _metrics([_safe_float(row.get("return_5d_pct")) for row in selected])
        stop_labels = [row.get("stop_before_target_5d") for row in selected if isinstance(row.get("stop_before_target_5d"), bool)]
        return {
            "order": label,
            "rows": len(selected),
            "tickers": [row.get("ticker") for row in selected],
            "return_3d": ret3,
            "return_5d": ret5,
            "stop_first_5d_pct": round(sum(1 for value in stop_labels if value) / len(stop_labels) * 100.0, 4) if stop_labels else None,
        }

    return {
        "policy_version": ADMISSION_POLICY_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "top_n": int(top_n),
        "comparison_groups": len(groups),
        "original_order": summarize(original, "original"),
        "expectancy_order": summarize(by_expectancy, "realized_expectancy"),
    }


def load_post_scan_ledger_rows(shared_dir: Path, limit_runs: int = 200) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    run_dirs = sorted(
        [path for path in shared_dir.glob("RUN-*") if (path / "post_scan_outcome_ledger.json").exists()],
        key=lambda path: (path / "post_scan_outcome_ledger.json").stat().st_mtime,
        reverse=True,
    )[: int(limit_runs)]
    for run_dir in run_dirs:
        try:
            payload = json.loads((run_dir / "post_scan_outcome_ledger.json").read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
            rows.extend([row for row in payload["rows"] if isinstance(row, dict)])
    return rows
