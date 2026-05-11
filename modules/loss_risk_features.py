from __future__ import annotations

from typing import Any, Dict


LOSS_RISK_GATE_THRESHOLDS: Dict[str, Dict[str, float]] = {
    "KOSPI": {"soft": 50.0, "hard": 65.0},
    "KOSDAQ": {"soft": 45.0, "hard": 65.0},
}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return float(default)
        f = float(value)
        if f != f:
            return float(default)
        return f
    except Exception:
        return float(default)


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "nan", "none", "null", "unknown", "?", "na", "n/a"}
    try:
        f = float(value)
        return f == f
    except Exception:
        return True


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if float(value) != float(value):
            return False
        return bool(value)
    return str(value or "").strip().lower() in {"true", "1", "yes", "y", "✅"}


def get_loss_risk_gate_thresholds(market_subtype: Any) -> Dict[str, float]:
    market = str(market_subtype or "").upper()
    if market.endswith(".KS"):
        market = "KOSPI"
    elif market.endswith(".KQ"):
        market = "KOSDAQ"
    return LOSS_RISK_GATE_THRESHOLDS.get(market, {"soft": 58.0, "hard": 75.0})


def get_loss_risk_soft_cap_decision(market_subtype: Any) -> str:
    market = str(market_subtype or "").upper()
    if market.endswith(".KQ"):
        market = "KOSDAQ"
    # KOSDAQ soft-risk watchlist/picked rows showed negative 5d expectancy
    # and severe drawdown above 40% on realized history. Keep the candidate
    # visible for audit, but do not surface it as a buy-grade signal.
    if market == "KOSDAQ":
        return "OBSERVE"
    return "WATCHLIST"


def compute_loss_risk_features(
    *,
    market_subtype: Any = "",
    alpha_score: Any = None,
    tech_score: Any = None,
    whale_score: Any = None,
    ml_prob: Any = None,
    prob_clean: Any = None,
    volume_ratio: Any = None,
    volume_confirmed: Any = None,
    position: Any = "",
    tier: Any = "",
    trend: Any = "",
) -> Dict[str, float]:
    """Pre-scan loss-risk features shared by training and inference.

    These features intentionally use only scan-time values. They encode the
    failure pattern observed in KR SWING archive losses: high alpha/tech scores
    without probability support, weak volume confirmation, and KOSDAQ chase
    setups in Rising/Peak/Resting states.
    """
    market = str(market_subtype or "").upper()
    position_text = str(position or "")
    tier_text = str(tier or "")
    trend_text = str(trend or "").upper()

    alpha = _to_float(alpha_score)
    tech = _to_float(tech_score, alpha)
    whale = _to_float(whale_score)
    ml = _to_float(ml_prob)
    clean = _to_float(prob_clean, ml)
    prob_support = max(ml, clean)
    prob_floor = min(ml, clean)
    prob_disagreement = abs(ml - clean)
    vol = _to_float(volume_ratio, 0.0)
    vol_ok = _truthy(volume_confirmed) or vol >= 1.2

    is_kosdaq = market == "KOSDAQ" or str(market_subtype or "").upper().endswith(".KQ")
    is_rising = "Rising" in position_text or "상승" in position_text
    is_peak = "Peak" in position_text or "고점" in position_text
    is_resting = "Resting" in position_text or "조정" in position_text
    is_chase_position = is_rising or is_peak or is_resting
    is_t1_t2 = "T1" in tier_text or "T2" in tier_text or "🏆" in tier_text or "⭐" in tier_text

    alpha_prob_gap = max(0.0, alpha - prob_support)
    tech_prob_gap = max(0.0, tech - prob_support)
    whale_prob_gap = max(0.0, whale - prob_support)

    missing_count = 0
    for value in (tech_score, whale_score, volume_ratio, position):
        if not _has_value(value):
            missing_count += 1

    low_prob_high_alpha = float(alpha >= 75.0 and prob_support < 38.0)
    clean_prob_high_alpha = float(alpha >= 70.0 and clean < 35.0)
    model_prob_disagreement = float(alpha >= 70.0 and prob_disagreement >= 15.0 and prob_floor < 38.0)
    weak_volume_high_alpha = float(alpha >= 75.0 and (not vol_ok or vol < 0.8))
    chase_low_prob = float(is_chase_position and prob_support < 42.0)
    kosdaq_tier_chase = float(is_kosdaq and is_t1_t2 and is_chase_position and prob_support < 45.0)
    kosdaq_clean_chase = float(is_kosdaq and is_t1_t2 and is_chase_position and clean < 35.0)
    uptrend_low_support = float(trend_text == "UP" and prob_support < 35.0)
    missing_core_trace = float(missing_count >= 2)

    loss_risk_score = (
        min(alpha_prob_gap, 60.0) * 0.42
        + min(tech_prob_gap, 60.0) * 0.16
        + min(whale_prob_gap, 60.0) * 0.08
        + min(prob_disagreement, 40.0) * 0.18
        + low_prob_high_alpha * 14.0
        + clean_prob_high_alpha * 16.0
        + model_prob_disagreement * 12.0
        + weak_volume_high_alpha * 12.0
        + chase_low_prob * 10.0
        + kosdaq_tier_chase * 16.0
        + kosdaq_clean_chase * 14.0
        + uptrend_low_support * 8.0
        + missing_core_trace * 10.0
    )

    return {
        "alpha_prob_gap": round(alpha_prob_gap, 4),
        "tech_prob_gap": round(tech_prob_gap, 4),
        "whale_prob_gap": round(whale_prob_gap, 4),
        "model_prob_disagreement": round(prob_disagreement, 4),
        "low_prob_high_alpha_risk": low_prob_high_alpha,
        "clean_prob_high_alpha_risk": clean_prob_high_alpha,
        "model_prob_disagreement_risk": model_prob_disagreement,
        "weak_volume_high_alpha_risk": weak_volume_high_alpha,
        "chase_low_prob_risk": chase_low_prob,
        "kosdaq_tier_chase_risk": kosdaq_tier_chase,
        "kosdaq_clean_chase_risk": kosdaq_clean_chase,
        "uptrend_low_support_risk": uptrend_low_support,
        "missing_core_trace_risk": missing_core_trace,
        "loss_risk_score": round(float(loss_risk_score), 4),
    }


def compute_entry_timing_risk_features(
    *,
    market_subtype: Any = "",
    expected_return_1d_pct: Any = None,
    expected_return_3d_pct: Any = None,
    expected_edge_score: Any = None,
    prev_pct_change_1d: Any = None,
    prev_pct_change_5d: Any = None,
    volume_ratio: Any = None,
    prob_clean: Any = None,
    loss_risk_score: Any = None,
    position: Any = "",
    tier: Any = "",
    trend: Any = "",
) -> Dict[str, float]:
    """Scan-time entry timing risk used to rank, not delete, KR swing names.

    The score targets the KOSDAQ pattern seen in validation: good 5-7d swing
    upside but weak next-day behavior. It only uses features available at scan
    time, so it remains auditable and safe for production ranking.
    """
    market = str(market_subtype or "").upper()
    is_kosdaq = market == "KOSDAQ" or market.endswith(".KQ")
    expected_1d = _to_float(expected_return_1d_pct, 0.0)
    expected_3d = _to_float(expected_return_3d_pct, expected_1d)
    edge = _to_float(expected_edge_score, 0.0)
    prev_1d = _to_float(prev_pct_change_1d, 0.0)
    prev_5d = _to_float(prev_pct_change_5d, prev_1d)
    volume = _to_float(volume_ratio, 0.0)
    clean = _to_float(prob_clean, 50.0)
    loss_risk = _to_float(loss_risk_score, 0.0)
    position_text = str(position or "")
    tier_text = str(tier or "")
    trend_text = str(trend or "").upper()

    is_rising = "Rising" in position_text or "상승" in position_text
    is_peak = "Peak" in position_text or "고점" in position_text
    is_resting = "Resting" in position_text or "조정" in position_text
    is_t1_t2 = "T1" in tier_text or "T2" in tier_text or "🏆" in tier_text or "⭐" in tier_text

    negative_1d_edge = max(0.0, 1.0 - expected_1d)
    delayed_swing_gap = max(0.0, expected_3d - expected_1d - 2.5)
    chase_extension = max(0.0, prev_1d - 4.0) + max(0.0, prev_5d - 12.0) * 0.35
    weak_volume = max(0.0, 1.2 - volume)
    weak_probability = max(0.0, 42.0 - clean)
    negative_edge = max(0.0, -edge)

    kosdaq_multiplier = 1.25 if is_kosdaq else 0.85
    timing_risk_score = (
        negative_1d_edge * 10.0
        + delayed_swing_gap * 4.0
        + chase_extension * 2.2
        + weak_volume * 8.0
        + weak_probability * 0.45
        + negative_edge * 3.0
        + min(loss_risk, 80.0) * 0.22
    ) * kosdaq_multiplier

    if is_kosdaq and is_t1_t2 and (is_rising or is_peak) and expected_1d < 1.0:
        timing_risk_score += 12.0
    if is_kosdaq and is_peak and volume < 1.0:
        timing_risk_score += 10.0
    if trend_text == "DOWN" and expected_1d < 1.5:
        timing_risk_score += 8.0
    if is_resting and expected_3d > expected_1d + 4.0:
        timing_risk_score += 4.0

    return {
        "entry_timing_risk_score": round(float(timing_risk_score), 4),
        "negative_1d_edge_risk": round(float(negative_1d_edge), 4),
        "delayed_swing_gap_risk": round(float(delayed_swing_gap), 4),
        "chase_extension_risk": round(float(chase_extension), 4),
        "weak_entry_volume_risk": round(float(weak_volume), 4),
    }
