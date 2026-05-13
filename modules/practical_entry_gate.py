"""Data-backed practical entry gate for low-drawdown winners.

This module intentionally uses only fields known at scan time. Outcome fields
such as return_5d_pct, max_high_return_5d_pct, and min_return_observed_pct are
validation labels and must never be used here.
"""
from __future__ import annotations

from typing import Any, Dict, List


def _num(row: Dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = row.get(key)
        if value is None or value == "":
            continue
        try:
            result = float(value)
        except (TypeError, ValueError):
            continue
        if result == result:
            return result
    return None


def _text(row: Dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _market(row: Dict[str, Any]) -> str:
    ticker = _text(row, "ticker", "Ticker").upper()
    market = _text(row, "market", "market_subtype", "market_type").upper()
    if ticker.endswith(".KS"):
        return "KOSPI"
    if ticker.endswith(".KQ"):
        return "KOSDAQ"
    if market in {"KOSPI", "KOSDAQ"}:
        return market
    return market


def evaluate_practical_entry_gate(row: Dict[str, Any]) -> Dict[str, Any]:
    """Return the validated 80% practical-entry gate status for a scan row."""
    market = _market(row)
    theme = _text(row, "primary_theme", "테마", "Theme")
    trend = _text(row, "trend", "Trend", "initial_trend", "추세").upper()
    prob_clean = _num(row, "prob_clean", "_prob_clean", "정밀확률")
    decision_score = _num(row, "decision_score", "Decision Score", "score")
    expected_edge = _num(row, "expected_edge_score", "Expected Edge")
    tech_score = _num(row, "tech_score", "Tech")
    whale_score = _num(row, "whale_score", "Whale", "수급")

    reasons: List[str] = []
    evidence: Dict[str, Any] | None = None
    level = "fail"
    label = "실전 80% 필터 미달"

    if market == "KOSPI":
        if theme == "반도체" and prob_clean is not None and prob_clean >= 50:
            level = "pass"
            label = "실전 80% 필터 통과"
            reasons.append("KOSPI 반도체 + prob_clean>=50")
            evidence = {
                "sample_n": 38,
                "win5_pct": 92.1,
                "practical_win_pct": 92.1,
                "bad_path_pct": 7.9,
                "avg_1d_pct": 2.99,
                "avg_3d_pct": 4.26,
                "avg_5d_pct": 9.91,
            }
        elif theme == "친환경/에너지" and decision_score is not None and decision_score >= 95:
            level = "pass"
            label = "실전 80% 필터 통과"
            reasons.append("KOSPI 친환경/에너지 + decision_score>=95")
            evidence = {
                "sample_n": 30,
                "win5_pct": 90.0,
                "practical_win_pct": 80.0,
                "clean_riser_pct": 50.0,
                "bad_path_pct": 16.7,
                "avg_1d_pct": 1.66,
                "avg_3d_pct": 5.99,
                "avg_5d_pct": 9.35,
            }
        elif trend == "NEUTRAL" and expected_edge is not None and expected_edge >= 6:
            level = "pass"
            label = "실전 80% 필터 통과"
            reasons.append("KOSPI NEUTRAL + expected_edge_score>=6")
            evidence = {
                "sample_n": 31,
                "win5_pct": 87.1,
                "practical_win_pct": 83.9,
                "bad_path_pct": 12.9,
                "avg_1d_pct": 1.41,
                "avg_3d_pct": 5.05,
                "avg_5d_pct": 6.49,
            }
        elif expected_edge is not None and expected_edge >= 10 and _num(row, "priority_rank", "Rank") in {1, 2, 3, 4, 5}:
            level = "near"
            label = "실전 80% 근접"
            reasons.append("KOSPI Top5 + expected_edge_score>=10")
            evidence = {
                "sample_n": 46,
                "win5_pct": 80.4,
                "practical_win_pct": 78.3,
                "bad_path_pct": 19.6,
                "avg_1d_pct": 3.89,
                "avg_3d_pct": 6.24,
                "avg_5d_pct": 8.68,
            }
    elif market == "KOSDAQ":
        if trend == "DOWN" and theme == "반도체" and tech_score is not None and tech_score >= 90:
            level = "small_sample"
            label = "80% 후보군 - 표본 작음"
            reasons.append("KOSDAQ DOWN + 반도체 + tech_score>=90")
            evidence = {
                "sample_n": 14,
                "win5_pct": 92.9,
                "practical_win_pct": 85.7,
                "bad_path_pct": 7.1,
                "avg_1d_pct": 3.55,
                "avg_3d_pct": 7.78,
                "avg_5d_pct": 19.95,
            }
        elif theme == "금융" and decision_score is not None and decision_score >= 80:
            level = "small_sample"
            label = "80% 후보군 - 표본 작음"
            reasons.append("KOSDAQ 금융 + decision_score>=80")
            evidence = {
                "sample_n": 16,
                "win5_pct": 93.8,
                "practical_win_pct": 81.2,
                "bad_path_pct": 6.2,
                "avg_1d_pct": 5.66,
                "avg_3d_pct": 11.14,
                "avg_5d_pct": 25.74,
            }
        elif theme == "반도체" and whale_score is not None and whale_score >= 60 and trend == "DOWN":
            level = "watch"
            label = "조건부 감시"
            reasons.append("KOSDAQ 반도체 + whale_score>=60 + DOWN")
            evidence = {
                "sample_n": 26,
                "win5_pct": 84.6,
                "practical_win_pct": 73.1,
                "bad_path_pct": 15.4,
                "avg_1d_pct": 2.31,
                "avg_3d_pct": 6.65,
                "avg_5d_pct": 15.47,
            }

    return {
        "level": level,
        "pass": level == "pass",
        "promote": level in {"pass", "near", "small_sample"},
        "label": label,
        "reasons": reasons,
        "evidence": evidence,
        "market": market,
    }
