"""Data-backed practical entry gate for low-drawdown winners.

This module intentionally uses only fields known at scan time. Outcome fields
such as return_5d_pct, max_high_return_5d_pct, and min_return_observed_pct are
validation labels and must never be used here.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DYNAMIC_PROFILE_PATH = PROJECT_ROOT / "runtime_state/reports/validation/dynamic_theme_entry_profiles.json"
_PROFILE_CACHE: Tuple[float | None, Dict[str, Any] | None] = (None, None)


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


def _load_profile_payload() -> Dict[str, Any] | None:
    global _PROFILE_CACHE
    try:
        stat = DYNAMIC_PROFILE_PATH.stat()
    except OSError:
        _PROFILE_CACHE = (None, None)
        return None

    mtime = stat.st_mtime
    if _PROFILE_CACHE[0] == mtime:
        return _PROFILE_CACHE[1]
    try:
        payload = json.loads(DYNAMIC_PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        payload = None
    _PROFILE_CACHE = (mtime, payload)
    return payload


def _find_theme_profile(payload: Dict[str, Any] | None, market: str, theme: str) -> Dict[str, Any] | None:
    if not payload or not market or not theme:
        return None
    markets = payload.get("markets") or {}
    market_payload = markets.get(market) or {}
    themes = market_payload.get("themes") or {}
    return themes.get(theme)


def _threshold_hits(row: Dict[str, Any], profile: Dict[str, Any]) -> tuple[int, int, List[str]]:
    thresholds = profile.get("thresholds") or {}
    checks = [
        ("prob_clean", "prob_clean", "prob_clean"),
        ("expected_edge_score", "expected_edge_score", "expected_edge"),
        ("decision_score", "decision_score", "decision_score"),
        ("tech_score", "tech_score", "tech_score"),
        ("whale_score", "whale_score", "whale_score"),
    ]
    hits = 0
    required = 0
    reasons: List[str] = []
    for metric, threshold_key, row_key in checks:
        threshold = thresholds.get(f"min_{threshold_key}")
        if threshold is None:
            continue
        required += 1
        value = _num(row, row_key, metric)
        if value is not None and value >= float(threshold):
            hits += 1
            reasons.append(f"{metric}>={float(threshold):g}")

    max_rank = thresholds.get("max_priority_rank")
    rank = _num(row, "priority_rank", "Rank")
    if max_rank is not None:
        required += 1
    if max_rank is not None and rank is not None and 1 <= rank <= float(max_rank):
        hits += 1
        reasons.append(f"priority_rank<={float(max_rank):g}")
    return hits, required, reasons


def _required_fields_match(row: Dict[str, Any], profile: Dict[str, Any]) -> tuple[bool, List[str]]:
    required = profile.get("required") or {}
    misses: List[str] = []
    expected_trend = required.get("trend")
    if expected_trend:
        trend = _text(row, "trend", "Trend", "initial_trend", "추세").upper()
        if trend != str(expected_trend).upper():
            misses.append(f"trend!={expected_trend}")
    return not misses, misses


def evaluate_practical_entry_gate(
    row: Dict[str, Any],
    *,
    profile_payload: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return the current dynamic practical-entry gate status for a scan row."""
    market = _market(row)
    theme = _text(row, "primary_theme", "테마", "Theme")
    profile = _find_theme_profile(profile_payload or _load_profile_payload(), market, theme)

    reasons: List[str] = ["동적 테마 프로필 없음"]
    evidence: Dict[str, Any] | None = None
    level = "fail"
    label = "실전 80% 필터 미달"
    if profile:
        profile_level = str(profile.get("level") or "fail")
        hits, required_hits, hit_reasons = _threshold_hits(row, profile)
        fields_ok, field_misses = _required_fields_match(row, profile)
        loss_risk = _num(row, "loss_risk_score")
        max_loss_risk = (profile.get("thresholds") or {}).get("max_loss_risk_score")
        high_loss_risk = max_loss_risk is not None and loss_risk is not None and loss_risk > float(max_loss_risk)
        evidence = profile.get("evidence")
        reasons = [f"동적 테마 프로필: {market}/{theme}"] + hit_reasons
        reasons.extend(field_misses)
        if high_loss_risk:
            reasons.append("loss_risk_score 과다")

        if hits >= required_hits and fields_ok and not high_loss_risk:
            level = profile_level
            if level == "pass":
                label = "실전 80% 필터 통과"
            elif level == "near":
                label = "실전 80% 근접"
            elif level == "small_sample":
                label = "80% 후보군 - 표본 작음"
            elif level == "watch":
                label = "조건부 감시"
        else:
            reasons.append(f"스캔 시점 강도 부족({hits}/{required_hits})")

    return {
        "level": level,
        "pass": level == "pass",
        "promote": level in {"pass", "near", "small_sample"},
        "label": label,
        "reasons": reasons,
        "evidence": evidence,
        "market": market,
    }
