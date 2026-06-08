from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


REGIME_THEME_CALIBRATION_VERSION = "kr_regime_theme_calibration_v1"
DEFAULT_THEME_CACHE_PATH = Path("runtime_state/long_term/theme_cache/KR.json")


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


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def _row_value(row: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row and row.get(key) not in (None, ""):
            return row.get(key)
    snapshot = row.get("feature_snapshot") if isinstance(row.get("feature_snapshot"), dict) else {}
    for key in keys:
        if key in snapshot and snapshot.get(key) not in (None, ""):
            return snapshot.get(key)
    return None


def _row_dict(row: Dict[str, Any], *keys: str) -> Dict[str, Any]:
    for key in keys:
        value = _row_value(row, key)
        if isinstance(value, dict):
            return value
    return {}


def load_theme_cache(path: Path = DEFAULT_THEME_CACHE_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _theme_lookup(cache: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in cache.get("theme_states") or []:
        if not isinstance(row, dict):
            continue
        for key in (row.get("theme_id"), row.get("theme_name")):
            text = _text(key)
            if text:
                out[text.lower()] = row
    return out


def _age_hours(value: Any, now: datetime) -> Optional[float]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return max(0.0, (now - parsed.astimezone(timezone.utc)).total_seconds() / 3600.0)
    except Exception:
        return None


def build_regime_theme_adjustment(
    row: Dict[str, Any],
    *,
    theme_cache: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    row = row if isinstance(row, dict) else {}
    now = now or datetime.now(timezone.utc)
    cache = theme_cache if isinstance(theme_cache, dict) else load_theme_cache()
    market_gate_raw = _row_value(row, "market_gate")
    if isinstance(market_gate_raw, dict):
        market_gate = _upper(market_gate_raw.get("gate"))
    else:
        market_gate = _upper(market_gate_raw)
    primary_theme = _text(_row_value(row, "primary_theme", "테마", "Theme"))
    theme_avg = _safe_float(_row_value(row, "theme_day_avg_decision_score", "_theme_day_avg_decision_score", "display_theme_day_avg_decision_score"))
    theme_count = _safe_float(_row_value(row, "theme_day_symbol_count", "_theme_day_symbol_count", "display_theme_day_symbol_count"))
    theme_score_adj = _safe_float(_row_value(row, "theme_score_adjustment"), 0.0) or 0.0
    breadth = _safe_float(_row_value(row, "regime_breadth_pct"))
    regime_avg_chg = _safe_float(_row_value(row, "regime_avg_chg"))
    kis_industry_regime = _row_dict(row, "kis_industry_regime", "kis_industry_regime_overlay")

    warnings = []
    confidence_parts = []
    prob_multiplier = 1.0
    return_multiplier = 1.0
    stop_risk_multiplier = 1.0

    if market_gate == "GREEN":
        prob_multiplier *= 1.04
        return_multiplier *= 1.04
        stop_risk_multiplier *= 0.96
        confidence_parts.append("market_gate")
    elif market_gate == "YELLOW":
        prob_multiplier *= 0.98
        return_multiplier *= 0.98
        stop_risk_multiplier *= 1.04
        confidence_parts.append("market_gate")
    elif market_gate == "RED":
        prob_multiplier *= 0.90
        return_multiplier *= 0.90
        stop_risk_multiplier *= 1.14
        confidence_parts.append("market_gate")
    else:
        warnings.append("missing_market_gate")

    if breadth is not None:
        confidence_parts.append("breadth")
        if breadth >= 58:
            prob_multiplier *= 1.03
            return_multiplier *= 1.03
        elif breadth <= 42:
            prob_multiplier *= 0.94
            return_multiplier *= 0.94
            stop_risk_multiplier *= 1.08
    if regime_avg_chg is not None:
        confidence_parts.append("regime_avg_chg")
        if regime_avg_chg >= 1.0:
            prob_multiplier *= 1.02
        elif regime_avg_chg <= -1.0:
            prob_multiplier *= 0.96
            stop_risk_multiplier *= 1.05

    if theme_count is None or theme_count < 3:
        warnings.append("small_theme_sample")
    else:
        confidence_parts.append("same_scan_theme")
        if theme_avg is not None and theme_avg >= 70:
            prob_multiplier *= 1.05
            return_multiplier *= 1.06
        elif theme_avg is not None and theme_avg <= 55:
            prob_multiplier *= 0.95
            return_multiplier *= 0.96
        if theme_count >= 8:
            prob_multiplier *= 1.02

    lookup = _theme_lookup(cache)
    theme_state = lookup.get(primary_theme.lower()) if primary_theme else None
    theme_momentum = None
    if theme_state:
        confidence_parts.append("theme_cache")
        theme_momentum = _safe_float(theme_state.get("avg_change_pct") or theme_state.get("strength_score"))
        if theme_momentum is not None:
            if theme_momentum >= 2.0:
                prob_multiplier *= 1.05
                return_multiplier *= 1.07
            elif theme_momentum <= -1.0:
                prob_multiplier *= 0.93
                return_multiplier *= 0.93
                stop_risk_multiplier *= 1.08
    elif primary_theme:
        warnings.append("theme_cache_miss")

    if kis_industry_regime:
        if kis_industry_regime.get("source_ok"):
            confidence_parts.append("kis_industry_regime")
            trend = _upper(kis_industry_regime.get("trend"))
            industry_return_5d = _safe_float(kis_industry_regime.get("return_5d_pct"))
            industry_return_20d = _safe_float(kis_industry_regime.get("return_20d_pct"))
            if trend == "STRONG_POSITIVE" or (industry_return_5d is not None and industry_return_5d >= 3.0):
                prob_multiplier *= 1.04
                return_multiplier *= 1.05
                stop_risk_multiplier *= 0.97
            elif trend == "POSITIVE" or (industry_return_5d is not None and industry_return_5d >= 1.0):
                prob_multiplier *= 1.02
                return_multiplier *= 1.025
            elif trend == "STRONG_NEGATIVE" or (industry_return_20d is not None and industry_return_20d <= -5.0):
                prob_multiplier *= 0.92
                return_multiplier *= 0.92
                stop_risk_multiplier *= 1.1
            elif trend == "NEGATIVE" or (industry_return_5d is not None and industry_return_5d <= -1.5):
                prob_multiplier *= 0.96
                return_multiplier *= 0.96
                stop_risk_multiplier *= 1.05
        else:
            warnings.append("kis_industry_regime_not_source_ok")

    cache_age = _age_hours(cache.get("theme_momentum_updated_at") or cache.get("generated_at"), now)
    if cache and cache_age is not None and cache_age > 24:
        warnings.append("stale_theme_cache")
        prob_multiplier = 1.0 + (prob_multiplier - 1.0) * 0.5
        return_multiplier = 1.0 + (return_multiplier - 1.0) * 0.5
    elif not cache:
        warnings.append("missing_theme_cache")

    confidence = _clamp(len(set(confidence_parts)) / 5.0, 0.0, 1.0)
    if warnings:
        confidence = _clamp(confidence - 0.12, 0.0, 1.0)
    return {
        "version": REGIME_THEME_CALIBRATION_VERSION,
        "prob_multiplier": round(_clamp(prob_multiplier, 0.78, 1.22), 6),
        "return_multiplier": round(_clamp(return_multiplier, 0.78, 1.25), 6),
        "stop_risk_multiplier": round(_clamp(stop_risk_multiplier, 0.75, 1.35), 6),
        "confidence": round(confidence, 6),
        "market_gate": market_gate or None,
        "primary_theme": primary_theme or None,
        "theme_day_avg_decision_score": theme_avg,
        "theme_day_symbol_count": theme_count,
        "theme_score_adjustment": theme_score_adj,
        "regime_breadth_pct": breadth,
        "regime_avg_chg": regime_avg_chg,
        "theme_momentum": theme_momentum,
        "kis_industry_regime": kis_industry_regime or None,
        "theme_cache_age_hours": round(cache_age, 3) if cache_age is not None else None,
        "warnings": warnings,
        "evidence": sorted(set(confidence_parts)),
    }
