from __future__ import annotations

import math
from typing import Any, Dict, List

from modules.kr_lane_champion_ranker import predict_lane_overlay
from modules.kosdaq_3d_continuation_ranker import predict_continuation_overlay
from modules.theme_momentum_loader import load_theme_momentum_lookup, get_theme_momentum


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, "", "nan"):
            return float(default)
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return float(default)
        return result
    except Exception:
        return float(default)


_SWING_VARIANT_PREFIXES = (
    "phase25_kr_swing",
    "phase25_kospi_swing",
    "phase25_kosdaq_swing",
)
_INTRADAY_VARIANT_PREFIXES = (
    "phase25_kr_intraday",
    "phase25_kospi_intraday",
    "phase25_kosdaq_intraday",
)


def _is_swing_variant(variant: str | None) -> bool:
    return any(str(variant or "").startswith(p) for p in _SWING_VARIANT_PREFIXES)


def _is_intraday_variant(variant: str | None) -> bool:
    return any(str(variant or "").startswith(p) for p in _INTRADAY_VARIANT_PREFIXES)


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "nan", "none", "null", "unknown", "na", "n/a"}
    try:
        numeric = float(value)
        if math.isnan(numeric) or math.isinf(numeric):
            return False
        return True
    except Exception:
        return True


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _extract_feature(candidate: Dict[str, Any], *keys: str) -> Any:
    feature_snapshot = candidate.get("feature_snapshot", {}) if isinstance(candidate.get("feature_snapshot"), dict) else {}
    for key in keys:
        if key in candidate and candidate.get(key) not in (None, ""):
            return candidate.get(key)
        if key in feature_snapshot and feature_snapshot.get(key) not in (None, ""):
            return feature_snapshot.get(key)
    return None


def _collect_context(candidate: Dict[str, Any], run_market: str, theme_momentum_lookup: Dict | None = None) -> Dict[str, Any]:
    feature_snapshot = candidate.get("feature_snapshot", {}) if isinstance(candidate.get("feature_snapshot"), dict) else {}
    theme_context = candidate.get("theme_context", {}) if isinstance(candidate.get("theme_context"), dict) else {}
    leader_metrics = candidate.get("leader_metrics", {}) if isinstance(candidate.get("leader_metrics"), dict) else {}
    if not theme_context and isinstance(feature_snapshot.get("theme_context"), dict):
        theme_context = feature_snapshot.get("theme_context", {})
    if not leader_metrics and isinstance(feature_snapshot.get("leader_metrics"), dict):
        leader_metrics = feature_snapshot.get("leader_metrics", {})

    raw_scan_mode = _extract_feature(candidate, "scan_mode")
    raw_phase25_variant = _extract_feature(candidate, "phase25_variant")
    raw_real_trend = _extract_feature(candidate, "real_trend", "trend")
    raw_routing_path = _extract_feature(candidate, "routing_path", "theme_routing_path")
    raw_strategy_text = _extract_feature(candidate, "strategy", "note")
    raw_context_text = _extract_feature(candidate, "context")
    raw_prob_5 = _extract_feature(candidate, "prob_5", "_prob_5", "ml_prob")
    raw_prob_clean = _extract_feature(candidate, "prob_clean", "_prob_clean")
    raw_phase25_shadow_prob = _extract_feature(candidate, "phase25_shadow_prob")
    raw_phase25_recommended_threshold = _extract_feature(candidate, "phase25_recommended_threshold")
    raw_whale_score = _extract_feature(candidate, "whale_score")
    raw_expected_return_1d_pct = _extract_feature(candidate, "expected_return_1d_pct")
    raw_expected_return_3d_pct = _extract_feature(candidate, "expected_return_3d_pct")
    raw_theme_direction = theme_context.get("theme_direction")
    raw_theme_strength = theme_context.get("theme_strength_score")
    raw_primary_theme = theme_context.get("primary_theme") or _extract_feature(candidate, "primary_theme")
    raw_leader_score = leader_metrics.get("kr_flow_leader_score", leader_metrics.get("leader_score"))
    raw_context_adjustment = leader_metrics.get("kr_context_adjustment", theme_context.get("context_score_adjustment"))
    raw_alpha_score = _extract_feature(candidate, "alpha_score")
    raw_decision_score = _extract_feature(candidate, "decision_score", "score")
    raw_kr_universe_role = _extract_feature(candidate, "kr_universe_role")
    raw_scanner_timeframe_profile = _extract_feature(candidate, "scanner_timeframe_profile")
    raw_position = _extract_feature(candidate, "position")
    raw_secondary_themes = _extract_feature(candidate, "secondary_themes")
    raw_secondary_theme_count = (
        len(raw_secondary_themes) if isinstance(raw_secondary_themes, list) else 0
    )
    continuation_gate = is_kosdaq_3d_continuation_eligible(candidate)
    if continuation_gate.get("eligible", False):
        continuation_overlay = predict_continuation_overlay(
            decision_score=raw_decision_score,
            alpha_score=raw_alpha_score,
            ml_prob=raw_prob_5,
            trend=raw_real_trend,
        )
    else:
        continuation_overlay = {"enabled": False, "score_adjustment": 0.0}
    market_name = str(run_market or "").upper()
    # Compute explosive gate for context — used in scoring to penalize ineligible EXPLOSIVE_LEADER picks
    explosive_gate_ctx = is_kr_explosive_leader_eligible(candidate, market_name)
    lane_overlay_1d = predict_lane_overlay(candidate, market_name, "1d")
    lane_overlay_3d = predict_lane_overlay(candidate, market_name, "3d")

    # Theme momentum: FDR avg_change_pct per theme (populated externally; None = no data)
    _lookup = theme_momentum_lookup if isinstance(theme_momentum_lookup, dict) else {}
    theme_momentum_pct, theme_momentum_class = get_theme_momentum(_lookup, raw_primary_theme)

    return {
        "feature_snapshot": feature_snapshot,
        "theme_context": theme_context,
        "leader_metrics": leader_metrics,
        "scan_mode": str(raw_scan_mode or "").upper(),
        "phase25_variant": str(raw_phase25_variant or ""),
        "real_trend": str(raw_real_trend or "").upper(),
        "routing_path": str(raw_routing_path or theme_context.get("routing_path") or "").lower(),
        "strategy_text": str(raw_strategy_text or ""),
        "context_text": str(raw_context_text or ""),
        "prob_5": _safe_float(raw_prob_5, 0.0),
        "prob_clean": _safe_float(raw_prob_clean, 0.0),
        "whale_score": _safe_float(raw_whale_score, 0.0),
        "expected_return_1d_pct": raw_expected_return_1d_pct,
        "expected_return_3d_pct": raw_expected_return_3d_pct,
        "theme_direction": str(raw_theme_direction or "").upper(),
        "theme_strength": _safe_float(raw_theme_strength, 0.0),
        "leader_score": _safe_float(raw_leader_score, 0.0),
        "context_adjustment": _safe_float(raw_context_adjustment, 0.0),
        "alpha_score": _safe_float(raw_alpha_score, 0.0),
        "kr_universe_role": str(raw_kr_universe_role or "").upper(),
        "scanner_timeframe_profile": str(raw_scanner_timeframe_profile or "").upper(),
        "flow_consensus": bool(leader_metrics.get("kr_flow_consensus_buying", False)),
        "retail_dominant": bool(leader_metrics.get("kr_retail_dominant", False)),
        "has_prob_5": _has_value(raw_prob_5),
        "has_prob_clean": _has_value(raw_prob_clean),
        "has_whale_score": _has_value(raw_whale_score),
        "has_expected_return_1d_pct": _has_value(raw_expected_return_1d_pct),
        "has_expected_return_3d_pct": _has_value(raw_expected_return_3d_pct),
        "has_real_trend": _has_value(raw_real_trend),
        "has_routing_path": _has_value(raw_routing_path) or _has_value(theme_context.get("routing_path")),
        "has_theme_direction": _has_value(raw_theme_direction),
        "has_leader_score": _has_value(raw_leader_score),
        "has_context_adjustment": _has_value(raw_context_adjustment),
        "has_strategy_text": _has_value(raw_strategy_text),
        "has_context_text": _has_value(raw_context_text),
        "position": str(raw_position or "").lower(),
        "secondary_theme_count": int(raw_secondary_theme_count),
        "phase25_shadow_prob": _safe_float(raw_phase25_shadow_prob, 0.0),
        "phase25_recommended_threshold": _safe_float(raw_phase25_recommended_threshold, 0.0),
        "has_phase25_shadow": _has_value(raw_phase25_shadow_prob),
        "has_phase25_recommended_threshold": _has_value(raw_phase25_recommended_threshold),
        "explosive_gate_eligible": bool(explosive_gate_ctx.get("eligible", False)),
        "explosive_gate_reasons_ctx": list(explosive_gate_ctx.get("reasons", []) or []),
        "continuation_gate": continuation_gate if isinstance(continuation_gate, dict) else {},
        "continuation_overlay": continuation_overlay if isinstance(continuation_overlay, dict) else {},
        "lane_overlay_1d": lane_overlay_1d if isinstance(lane_overlay_1d, dict) else {},
        "lane_overlay_3d": lane_overlay_3d if isinstance(lane_overlay_3d, dict) else {},
        "theme_momentum_pct": theme_momentum_pct,
        "theme_momentum_class": str(theme_momentum_class or "UNKNOWN"),
        "has_theme_momentum": theme_momentum_pct is not None,
    }


def is_kr_explosive_leader_eligible(candidate: Dict[str, Any], market: str) -> Dict[str, Any]:
    market_name = str(market or "").upper()
    role = str(_extract_feature(candidate, "kr_universe_role") or "").upper()
    scan_mode = str(_extract_feature(candidate, "scan_mode") or "").upper()
    decision_score = _safe_float(_extract_feature(candidate, "decision_score", "score"), 0.0)
    ml_prob = _safe_float(_extract_feature(candidate, "prob_5", "_prob_5", "ml_prob"), 0.0)
    trend = str(_extract_feature(candidate, "real_trend", "trend") or "").upper()
    phase25_variant = str(_extract_feature(candidate, "phase25_variant") or "")

    reasons: List[str] = []
    eligible = True
    if role != "EXPLOSIVE_LEADER" and scan_mode != "INTRADAY":
        eligible = False
        reasons.append("NOT_EXPLOSIVE_ROLE")

    min_score = 70.0 if market_name == "KOSPI" else 85.0
    min_ml = 22.0 if market_name == "KOSPI" else 24.0
    if _is_intraday_variant(phase25_variant):
        min_score += 3.0
        min_ml += 2.0

    if decision_score < min_score:
        eligible = False
        reasons.append(f"DECISION_SCORE_LT_{int(min_score)}")
    if ml_prob < min_ml:
        eligible = False
        reasons.append(f"ML_PROB_LT_{int(min_ml)}")
    if trend == "DOWN":
        eligible = False
        reasons.append("TREND_DOWN")

    return {
        "eligible": bool(eligible),
        "role": role or "UNKNOWN",
        "scan_mode": scan_mode or "UNKNOWN",
        "decision_score": round(decision_score, 2),
        "ml_prob": round(ml_prob, 2),
        "trend": trend or "UNKNOWN",
        "reasons": reasons,
    }


def is_kosdaq_3d_continuation_eligible(candidate: Dict[str, Any]) -> Dict[str, Any]:
    scan_mode = str(_extract_feature(candidate, "scan_mode") or "").upper()
    decision_score = _safe_float(_extract_feature(candidate, "decision_score", "score"), 0.0)
    alpha_score = _safe_float(_extract_feature(candidate, "alpha_score"), 0.0)
    ml_prob = _safe_float(_extract_feature(candidate, "prob_5", "_prob_5", "ml_prob"), 0.0)
    trend = str(_extract_feature(candidate, "real_trend", "trend") or "").upper()

    reasons: List[str] = []
    eligible = True
    if scan_mode != "SWING":
        eligible = False
        reasons.append("SCAN_MODE_NOT_SWING")
    if decision_score < 78.0:
        eligible = False
        reasons.append("DECISION_SCORE_LT_78")
    if alpha_score < 45.0:
        eligible = False
        reasons.append("ALPHA_SCORE_LT_45")
    if ml_prob < 27.0:
        eligible = False
        reasons.append("ML_PROB_LT_27")
    if trend != "UP":
        eligible = False
        reasons.append("TREND_NOT_UP")

    return {
        "eligible": bool(eligible),
        "decision_score": round(decision_score, 2),
        "alpha_score": round(alpha_score, 2),
        "ml_prob": round(ml_prob, 2),
        "trend": trend or "UNKNOWN",
        "reasons": reasons,
    }


def _score_horizon(
    *,
    market: str,
    raw_score: float,
    context: Dict[str, Any],
    horizon: str,
) -> Dict[str, Any]:
    scan_mode = str(context.get("scan_mode") or "").upper()
    phase25_variant = str(context.get("phase25_variant") or "")
    real_trend = str(context.get("real_trend") or "").upper()
    routing_path = str(context.get("routing_path") or "").lower()
    strategy_text = str(context.get("strategy_text") or "")
    context_text = str(context.get("context_text") or "")
    prob_5 = _safe_float(context.get("prob_5"), 0.0)
    prob_clean = _safe_float(context.get("prob_clean"), 0.0)
    whale_score = _safe_float(context.get("whale_score"), 0.0)
    expected_return_1d_pct = context.get("expected_return_1d_pct")
    expected_return_3d_pct = context.get("expected_return_3d_pct")
    theme_direction = str(context.get("theme_direction") or "").upper()
    theme_strength = _safe_float(context.get("theme_strength"), 0.0)
    leader_score = _safe_float(context.get("leader_score"), 0.0)
    context_adjustment = _safe_float(context.get("context_adjustment"), 0.0)
    flow_consensus = bool(context.get("flow_consensus", False))
    retail_dominant = bool(context.get("retail_dominant", False))
    has_prob_5 = bool(context.get("has_prob_5", False))
    has_prob_clean = bool(context.get("has_prob_clean", False))
    has_whale_score = bool(context.get("has_whale_score", False))
    has_expected_return_1d_pct = bool(context.get("has_expected_return_1d_pct", False))
    has_expected_return_3d_pct = bool(context.get("has_expected_return_3d_pct", False))
    has_real_trend = bool(context.get("has_real_trend", False))
    has_routing_path = bool(context.get("has_routing_path", False))
    has_theme_direction = bool(context.get("has_theme_direction", False))
    has_leader_score = bool(context.get("has_leader_score", False))
    has_context_adjustment = bool(context.get("has_context_adjustment", False))
    has_strategy_text = bool(context.get("has_strategy_text", False))
    has_context_text = bool(context.get("has_context_text", False))
    continuation_gate = context.get("continuation_gate", {}) if isinstance(context.get("continuation_gate"), dict) else {}
    continuation_eligible = bool(continuation_gate.get("eligible", False))
    continuation_overlay = context.get("continuation_overlay", {}) if isinstance(context.get("continuation_overlay"), dict) else {}
    continuation_enabled = bool(continuation_overlay.get("enabled", False))
    continuation_score_adjustment = _safe_float(continuation_overlay.get("score_adjustment"), 0.0)
    kr_universe_role = str(context.get("kr_universe_role") or "").upper()
    position = str(context.get("position") or "").lower()
    secondary_theme_count = int(context.get("secondary_theme_count", 0) or 0)
    phase25_shadow_prob = _safe_float(context.get("phase25_shadow_prob"), 0.0)
    phase25_recommended_threshold = _safe_float(context.get("phase25_recommended_threshold"), 0.0)
    has_phase25_shadow = bool(context.get("has_phase25_shadow", False))
    has_phase25_recommended_threshold = bool(context.get("has_phase25_recommended_threshold", False))
    explosive_gate_eligible = bool(context.get("explosive_gate_eligible", False))
    has_theme_momentum = bool(context.get("has_theme_momentum", False))
    theme_momentum_pct = context.get("theme_momentum_pct")
    theme_momentum_class = str(context.get("theme_momentum_class") or "UNKNOWN")
    lane_overlay = (
        context.get("lane_overlay_1d", {}) if horizon == "1d" else context.get("lane_overlay_3d", {})
    ) if isinstance(context.get("lane_overlay_1d"), dict) and isinstance(context.get("lane_overlay_3d"), dict) else {}

    score = float(raw_score)
    adjustments: List[Dict[str, Any]] = []

    def _add(delta: float, reason: str) -> None:
        nonlocal score
        if abs(float(delta)) < 0.01:
            return
        score += float(delta)
        adjustments.append({"reason": reason, "delta": round(float(delta), 2)})

    if horizon == "1d":
        intraday_exception = (
            scan_mode == "INTRADAY"
            and raw_score >= (84.0 if market == "KOSPI" else 86.0)
            and prob_5 >= 58.0
            and real_trend == "UP"
        )
        if scan_mode == "SWING":
            _add(5.0 if market == "KOSPI" else 6.5, "SCAN_MODE_SWING_1D")
        elif scan_mode == "INTRADAY" and not intraday_exception:
            _add(-4.0 if market == "KOSPI" else -7.0, "SCAN_MODE_INTRADAY_1D")
        elif intraday_exception:
            _add(2.0, "SCAN_MODE_INTRADAY_EXCEPTION_1D")
    else:
        if scan_mode == "SWING":
            _add(10.0 if market == "KOSPI" else 12.0, "SCAN_MODE_SWING_3D")
        elif scan_mode == "INTRADAY":
            _add(-8.0 if market == "KOSPI" else -14.0, "SCAN_MODE_INTRADAY_3D")

    # KOSDAQ INTRADAY EXPLOSIVE_LEADER gate enforcement
    # Analysis: 2166 gate-fail picks from April RUNs averaged -4.87% return, 12% win rate
    # Gate failure = missing decision_score, ML score, or trend — stock not ready for explosive play
    if market == "KOSDAQ" and scan_mode == "INTRADAY" and kr_universe_role == "EXPLOSIVE_LEADER":
        if not explosive_gate_eligible:
            _add(-12.0, "KOSDAQ_EXPLOSIVE_GATE_FAIL")

    if real_trend == "UP":
        _add(4.0, "TREND_UP")
    elif real_trend == "DOWN":
        _add(-7.0, "TREND_DOWN")

    if _is_intraday_variant(phase25_variant):
        _add(-5.0 if horizon == "1d" else (-7.0 if market == "KOSPI" else -10.0), f"PHASE25_INTRADAY_{horizon.upper()}_PENALTY")
    elif _is_swing_variant(phase25_variant):
        _add(1.5 if horizon == "1d" else 3.0, f"PHASE25_SWING_{horizon.upper()}_PREMIUM")

    if has_expected_return_1d_pct:
        multiplier = 1.8 if horizon == "1d" else 0.7
        _add(_clamp(_safe_float(expected_return_1d_pct) * multiplier, -7.0, 9.0), f"EXPECTED_RETURN_1D_{horizon.upper()}")
    if has_expected_return_3d_pct:
        multiplier = 0.35 if horizon == "1d" else 0.95
        _add(_clamp(_safe_float(expected_return_3d_pct) * multiplier, -6.0, 11.0), f"EXPECTED_RETURN_3D_{horizon.upper()}")

    if routing_path == "theme_routed":
        _add(4.0 if horizon == "1d" else 5.0, f"THEME_ROUTED_{horizon.upper()}")
    elif routing_path == "theme_shadow":
        _add(1.2 if horizon == "1d" else 1.8, f"THEME_SHADOW_{horizon.upper()}")

    if has_context_text and ("수혜" in context_text or "Beneficiary" in context_text):
        _add(4.5 if horizon == "1d" else 3.5, f"NEWS_BENEFICIARY_{horizon.upper()}")
    if has_context_text and "피해" in context_text:
        _add(-5.0 if horizon == "1d" else -4.5, f"NEWS_HEADWIND_{horizon.upper()}")
    if has_strategy_text and "FlowLeader" in strategy_text:
        _add(4.0 if horizon == "1d" else 3.0, f"FLOW_LEADER_{horizon.upper()}")
    if has_strategy_text and "ThemeRoute" in strategy_text:
        _add(2.0, f"THEME_ROUTE_TAG_{horizon.upper()}")
    if has_strategy_text and "ContextTailwind" in strategy_text:
        _add(3.0 if horizon == "1d" else 2.0, f"CONTEXT_TAILWIND_{horizon.upper()}")
    if has_strategy_text and "ContextRisk" in strategy_text:
        _add(-4.0 if horizon == "1d" else -3.0, f"CONTEXT_RISK_{horizon.upper()}")

    if has_theme_direction and theme_direction == "BENEFICIARY":
        bonus = min(4.0 if horizon == "1d" else 5.0, 1.0 + theme_strength / (25.0 if horizon == "1d" else 20.0))
        _add(bonus, f"THEME_BENEFICIARY_{horizon.upper()}")
    elif has_theme_direction and theme_direction == "HEADWIND":
        penalty = min(5.0 if horizon == "1d" else 5.5, 1.0 + theme_strength / (20.0 if horizon == "1d" else 18.0))
        _add(-penalty, f"THEME_HEADWIND_{horizon.upper()}")

    # Theme momentum: real-time avg_change_pct of theme constituents (from FDR / ThemeMomentum)
    # Amplifies BENEFICIARY or confirms HEADWIND based on actual intraday price movement.
    # Data is populated externally into theme_cache; no-op when unavailable (has_theme_momentum=False).
    if has_theme_momentum and theme_momentum_pct is not None:
        m_pct = float(theme_momentum_pct)
        if theme_direction == "BENEFICIARY":
            if theme_momentum_class == "EXPLODING":
                # Theme surging >2%: strong confirmation — add on top of beneficiary bonus
                _add(3.0 if horizon == "1d" else 2.0, f"THEME_MOMENTUM_EXPLODING_{horizon.upper()}")
            elif theme_momentum_class == "ACCELERATING":
                # Theme up 0.5-2%: moderate confirmation
                _add(1.5 if horizon == "1d" else 1.0, f"THEME_MOMENTUM_ACCELERATING_{horizon.upper()}")
            elif m_pct <= -1.0:
                # Theme down >1% despite BENEFICIARY label — label may be stale, penalize
                _add(-3.0 if horizon == "1d" else -2.0, f"THEME_MOMENTUM_CONTRARIAN_{horizon.upper()}")
            elif theme_momentum_class == "FADING":
                # Theme slightly down (-0.5% to -1%): mild caution
                _add(-1.5 if horizon == "1d" else -1.0, f"THEME_MOMENTUM_FADING_{horizon.upper()}")
        elif theme_direction == "HEADWIND":
            if theme_momentum_class == "FADING" or m_pct <= -2.0:
                # Theme actively falling: confirmed headwind — reinforce penalty
                _add(-2.0 if horizon == "1d" else -1.5, f"THEME_HEADWIND_CONFIRMED_{horizon.upper()}")
            elif m_pct >= 1.0:
                # Theme actually rising despite HEADWIND label — label may be stale, reduce penalty
                _add(2.0 if horizon == "1d" else 1.5, f"THEME_HEADWIND_CONTRARIAN_{horizon.upper()}")
        else:
            # No direction label but momentum data exists — use momentum alone as weak signal
            if theme_momentum_class == "EXPLODING":
                _add(1.5 if horizon == "1d" else 1.0, f"THEME_MOMENTUM_PURE_UP_{horizon.upper()}")
            elif m_pct <= -2.0:
                _add(-1.5 if horizon == "1d" else -1.0, f"THEME_MOMENTUM_PURE_DOWN_{horizon.upper()}")

    if has_leader_score and leader_score >= 80.0:
        _add(5.0 if horizon == "1d" else 4.0, f"LEADER_SCORE_HIGH_{horizon.upper()}")
    elif has_leader_score and leader_score >= 70.0:
        _add(2.5 if horizon == "1d" else 2.0, f"LEADER_SCORE_SUPPORT_{horizon.upper()}")
    if has_context_adjustment and context_adjustment != 0.0:
        _add(_clamp(context_adjustment * (0.7 if horizon == "1d" else 0.45), -6.0, 6.0), f"CONTEXT_ADJUSTMENT_{horizon.upper()}")

    if has_leader_score and flow_consensus:
        _add(2.0 if horizon == "1d" else 1.2, f"FLOW_CONSENSUS_{horizon.upper()}")
    if has_leader_score and retail_dominant:
        _add(-4.0 if horizon == "1d" else -3.0, f"RETAIL_DOMINANT_{horizon.upper()}")

    if has_prob_clean and prob_clean >= 38.0:
        _add(1.5 if horizon == "1d" else 2.5, f"CLEAN_PROB_STRONG_{horizon.upper()}")
    elif has_prob_clean and prob_clean < 28.0:
        _add(-4.0 if horizon == "1d" else -5.0, f"CLEAN_PROB_WEAK_{horizon.upper()}")

    if has_prob_5 and prob_5 >= 60.0:
        _add(_clamp((prob_5 - 60.0) * (0.13 if horizon == "1d" else 0.09), 0.0, 4.0), f"MODEL_SUPPORT_{horizon.upper()}")
    elif has_prob_5 and prob_5 < 45.0:
        _add(-_clamp((45.0 - prob_5) * (0.15 if horizon == "1d" else 0.10), 0.0, 4.0), f"MODEL_UNDER_SUPPORT_{horizon.upper()}")

    if has_whale_score and whale_score >= 65.0:
        _add(_clamp((whale_score - 65.0) * (0.10 if horizon == "1d" else 0.07), 0.0, 3.0), f"WHALE_SUPPORT_{horizon.upper()}")
    elif has_whale_score and whale_score < 40.0:
        _add(-_clamp((40.0 - whale_score) * (0.10 if horizon == "1d" else 0.08), 0.0, 3.0), f"WHALE_WEAK_{horizon.upper()}")

    # Alpha score signal — empirical: SWING rank 1-10 with alpha≥50 averages +5.93% 3D vs +0.26% no-alpha
    # Data source: 22K+ KR RESOLVED outcomes; alpha≥65 → +6.51%, 73% win rate
    alpha_score_raw = _safe_float(context.get("alpha_score"), -1.0)
    has_alpha_score = alpha_score_raw >= 0.0
    if has_alpha_score:
        if alpha_score_raw >= 65.0:
            _add(6.0 if horizon == "3d" else 3.5, f"ALPHA_STRONG_{horizon.upper()}")
        elif alpha_score_raw >= 55.0:
            _add(4.0 if horizon == "3d" else 2.5, f"ALPHA_GOOD_{horizon.upper()}")
        elif alpha_score_raw >= 45.0:
            _add(2.0 if horizon == "3d" else 1.5, f"ALPHA_BASE_{horizon.upper()}")
        elif alpha_score_raw < 35.0:
            _add(-4.0 if horizon == "3d" else -3.0, f"ALPHA_WEAK_{horizon.upper()}")

    if bool(lane_overlay.get("enabled", False)):
        overlay_delta = _safe_float(lane_overlay.get("score_adjustment"), 0.0)
        segment_name = str(lane_overlay.get("segment") or "lane")
        _add(overlay_delta, f"LANE_CHAMPION_{segment_name.upper()}_{horizon.upper()}")

    # KOSPI universe role differentiation: archive data shows CORE_TREND win ≈ 60-66%, EXPLOSIVE_LEADER win ≈ 13%.
    # Apply bonus for confirmed CORE_TREND and penalty for EXPLOSIVE_LEADER without lane champion.
    if market == "KOSPI":
        if kr_universe_role == "CORE_TREND":
            if horizon == "3d":
                _add(2.5, "KOSPI_CORE_TREND_3D")
            else:
                _add(1.5, "KOSPI_CORE_TREND_1D")
        elif kr_universe_role == "EXPLOSIVE_LEADER":
            # Lane champion doesn't cover KOSPI EXPLOSIVE_LEADER — apply mild penalty
            # in bear-signal conditions (trend not up or flow not confirmed)
            if real_trend != "UP":
                _add(-4.0 if horizon == "3d" else -3.0, "KOSPI_EXPLOSIVE_BEARISH_TREND")
            elif not flow_consensus and has_leader_score:
                _add(-2.0, "KOSPI_EXPLOSIVE_NO_FLOW")

    # Phase25 shadow model signal: phase25_kr_swing at threshold=0.6 achieves 90.5% win, 8.0% avg
    # Apply direct score adjustment when shadow model is present and above/below threshold
    if has_phase25_shadow and has_phase25_recommended_threshold and scan_mode in {"SWING", ""}:
        if phase25_shadow_prob >= phase25_recommended_threshold:
            # Shadow model agrees with pick — strong confirmation
            excess = (phase25_shadow_prob - phase25_recommended_threshold) / 40.0  # normalize 0-1
            bonus = _clamp(2.5 + excess * 2.5, 2.0, 5.0)
            _add(bonus, f"PHASE25_SHADOW_CONFIRM_{horizon.upper()}")
        elif phase25_shadow_prob < phase25_recommended_threshold - 15.0:
            # Shadow model disagrees significantly — penalize
            deficit = (phase25_recommended_threshold - 15.0 - phase25_shadow_prob) / 30.0
            penalty = _clamp(2.0 + deficit * 3.0, 1.5, 5.0)
            _add(-penalty, f"PHASE25_SHADOW_REJECT_{horizon.upper()}")

    if market == "KOSDAQ" and horizon == "3d":
        if continuation_eligible and continuation_enabled:
            _add(continuation_score_adjustment, "KOSDAQ_3D_CONTINUATION_MODEL")
        has_exp_1d = has_expected_return_1d_pct
        has_exp_3d = has_expected_return_3d_pct
        has_route = has_routing_path
        has_trend = has_real_trend
        exp_1d = _safe_float(expected_return_1d_pct, 0.0)
        exp_3d = _safe_float(expected_return_3d_pct, 0.0)
        strong_route = routing_path in {"theme_routed", "theme_shadow"}
        persistent_flow = flow_consensus and leader_score >= 62.0 and not retail_dominant

        if has_exp_3d and exp_3d >= 3.5 and persistent_flow and real_trend == "UP":
            _add(5.0, "KOSDAQ_3D_PERSISTENCE_STRONG")
        elif has_exp_3d and exp_3d >= 2.0 and strong_route and real_trend == "UP":
            _add(2.5, "KOSDAQ_3D_PERSISTENCE_BASE")

        # Multi-day whale + flow support
        if has_whale_score and whale_score >= 62.0 and flow_consensus and not retail_dominant:
            _add(3.0, "KOSDAQ_3D_WHALE_PERSIST")
        elif has_whale_score and whale_score >= 70.0 and not retail_dominant:
            _add(1.5, "KOSDAQ_3D_WHALE_SUPPORT")

        # Theme continuation bonus
        if theme_strength >= 25.0 and strong_route:
            _add(2.5, "KOSDAQ_3D_THEME_PERSIST")
        elif theme_strength >= 15.0 and secondary_theme_count >= 1 and strong_route:
            _add(1.5, "KOSDAQ_3D_THEME_MULTI_PERSIST")

        # Anti-fade guard: peak position or overheat tag
        is_position_peak = "peak" in position
        has_overheat_tag = "단기과열" in strategy_text or "overheat" in strategy_text.lower()
        if is_position_peak or has_overheat_tag:
            _add(-4.0, "KOSDAQ_3D_FADE_RISK_PEAK")

        if has_exp_3d and exp_3d < 1.5:
            _add(-8.0, "KOSDAQ_3D_EXPECTED_RETURN_WEAK")
        elif has_exp_3d and exp_3d < 2.5:
            _add(-3.5, "KOSDAQ_3D_EXPECTED_RETURN_SOFT")

        if has_exp_1d and has_exp_3d and exp_1d >= exp_3d + 3.0:
            _add(-4.5, "KOSDAQ_3D_BURST_OVER_CONTINUATION")

        if has_prob_clean and prob_clean < 34.0:
            _add(-4.0, "KOSDAQ_3D_CLEAN_PROB_LOW")

        if has_trend and real_trend != "UP":
            _add(-5.0, "KOSDAQ_3D_TREND_NOT_UP")

        if has_route and not strong_route:
            _add(-4.0, "KOSDAQ_3D_THEME_ROUTE_MISSING")

        if has_leader_score and leader_score >= 60.0 and not flow_consensus:
            _add(-3.0, "KOSDAQ_3D_FLOW_NOT_CONFIRMED")

        if has_leader_score and retail_dominant:
            _add(-3.0, "KOSDAQ_3D_RETAIL_DOMINANT")

        evidence_count = sum(
            1
            for flag in [
                has_exp_3d,
                has_exp_1d,
                has_route,
                has_trend,
                has_leader_score,
                has_prob_clean,
                has_prob_5,
                has_strategy_text,
                has_context_text,
                has_theme_direction,
                continuation_eligible and continuation_enabled,
            ]
            if flag
        )
        shrink = 1.0
        if evidence_count <= 1:
            shrink = 0.10
        elif evidence_count == 2:
            shrink = 0.25
        elif evidence_count == 3:
            shrink = 0.45
        elif evidence_count == 4:
            shrink = 0.65
        elif evidence_count == 5:
            shrink = 0.80
        if shrink < 1.0:
            original_delta = score - raw_score
            adjusted_delta = original_delta * shrink
            score = raw_score + adjusted_delta
            adjustments.append({"reason": "KOSDAQ_3D_EVIDENCE_SHRINK", "delta": round(adjusted_delta - original_delta, 2)})

    final_score = round(_clamp(score, 0.0, 100.0), 2)
    return {
        "score": final_score,
        "raw_score": round(raw_score, 2),
        "adjustments": adjustments,
        "reasons": [str(row["reason"]) for row in adjustments[:8]],
    }


_theme_momentum_cache: Dict[str, Any] = {}


def compute_kr_quant_rerank(candidate: Dict[str, Any], run_market: str) -> Dict[str, Any]:
    market = str(run_market or "").upper()
    raw_score = _safe_float(candidate.get("score", _extract_feature(candidate, "decision_score", "score")), 0.0)
    if market not in {"KOSPI", "KOSDAQ"}:
        return {
            "score": round(raw_score, 2),
            "score_1d": round(raw_score, 2),
            "score_3d": round(raw_score, 2),
            "lane": "raw",
            "raw_score": round(raw_score, 2),
            "continuation_eligible": False,
            "continuation_enabled": False,
            "continuation_prob_3d": None,
            "continuation_gate_reasons": [],
            "continuation_evidence": 0,
            "adjustments": [],
            "reasons": [],
        }

    if market not in _theme_momentum_cache:
        _theme_momentum_cache[market] = load_theme_momentum_lookup(market)
    context = _collect_context(candidate, market, theme_momentum_lookup=_theme_momentum_cache[market])
    rank_1d = _score_horizon(market=market, raw_score=raw_score, context=context, horizon="1d")
    rank_3d = _score_horizon(market=market, raw_score=raw_score, context=context, horizon="3d")
    scan_mode = str(context.get("scan_mode") or "").upper()
    continuation_eligible = bool(context.get("continuation_gate", {}).get("eligible", False))
    explosive_gate = is_kr_explosive_leader_eligible(candidate, market)
    explosive_eligible = bool(explosive_gate.get("eligible", False))
    continuation_evidence = sum(
        1
        for flag in [
            bool(context.get("has_expected_return_3d_pct", False)),
            bool(context.get("has_expected_return_1d_pct", False)),
            bool(context.get("has_routing_path", False)),
            bool(context.get("has_real_trend", False)),
            bool(context.get("has_leader_score", False)),
            bool(context.get("has_prob_clean", False)),
            bool(context.get("has_theme_direction", False)),
            continuation_eligible and bool(context.get("continuation_overlay", {}).get("enabled", False)),
        ]
        if flag
    )
    continuation_prob = _safe_float(context.get("continuation_overlay", {}).get("prob_up_3d"), 0.0)
    continuation_gate_reasons = list(context.get("continuation_gate", {}).get("reasons", []) or [])
    role = str(context.get("kr_universe_role") or "").upper()
    timeframe_profile = str(context.get("scanner_timeframe_profile") or "").upper()
    if scan_mode == "INTRADAY":
        lane = "1d"
    elif market == "KOSDAQ":
        if role == "EXPLOSIVE_LEADER":
            lane = "1d"
        elif continuation_eligible and bool(context.get("continuation_overlay", {}).get("enabled", False)) and continuation_prob >= 62.0:
            lane = "3d"
        elif continuation_evidence >= 2 and float(rank_3d["score"]) >= float(rank_1d["score"]) - 1.0:
            lane = "3d"
        elif (
            bool(context.get("flow_consensus", False))
            and _safe_float(context.get("whale_score"), 0.0) >= 62.0
            and not bool(context.get("retail_dominant", False))
            and context.get("real_trend") == "UP"
            and float(rank_3d["score"]) >= float(rank_1d["score"]) - 3.0
        ):
            lane = "3d"
        else:
            lane = "1d"
    else:
        lane = "3d"
    primary = rank_1d if lane == "1d" else rank_3d
    return {
        "score": float(primary["score"]),
        "score_1d": float(rank_1d["score"]),
        "score_3d": float(rank_3d["score"]),
        "lane": lane,
        "continuation_evidence": int(continuation_evidence),
        "continuation_eligible": bool(continuation_eligible),
        "continuation_enabled": bool(context.get("continuation_overlay", {}).get("enabled", False)),
        "continuation_prob_3d": round(float(continuation_prob), 4),
        "continuation_gate_reasons": continuation_gate_reasons,
        "kr_universe_role": role or "TRANSITIONAL",
        "scanner_timeframe_profile": timeframe_profile or "UNKNOWN",
        "explosive_eligible": bool(explosive_eligible),
        "explosive_gate_reasons": list(explosive_gate.get("reasons", []) or []),
        "lane_overlay_1d": context.get("lane_overlay_1d", {}),
        "lane_overlay_3d": context.get("lane_overlay_3d", {}),
        "raw_score": round(raw_score, 2),
        "adjustments": list(primary.get("adjustments", [])),
        "reasons": list(primary.get("reasons", [])),
        "theme_momentum_pct": context.get("theme_momentum_pct"),
        "theme_momentum_class": context.get("theme_momentum_class", "UNKNOWN"),
    }


def resolve_kr_active_lane(scored_candidates: List[Dict[str, Any]], run_market: str) -> str:
    market = str(run_market or "").upper()
    if market != "KOSDAQ":
        return "mixed"

    lane_scores: Dict[str, List[float]] = {"1d": [], "3d": []}
    lane_evidence: Dict[str, List[float]] = {"1d": [], "3d": []}
    for cand in scored_candidates:
        quant_meta = cand.get("_quant_rerank", {}) if isinstance(cand.get("_quant_rerank"), dict) else {}
        lane = str(quant_meta.get("lane", "raw") or "raw")
        if lane == "1d":
            lane_scores["1d"].append(_safe_float(quant_meta.get("score_1d", quant_meta.get("score")), 0.0))
            lane_evidence["1d"].append(_safe_float(quant_meta.get("continuation_evidence"), 0.0))
        elif lane == "3d":
            lane_scores["3d"].append(_safe_float(quant_meta.get("score_3d", quant_meta.get("score")), 0.0))
            lane_evidence["3d"].append(_safe_float(quant_meta.get("continuation_evidence"), 0.0))

    def _top_avg(values: List[float]) -> float:
        if not values:
            return 0.0
        ordered = sorted([float(v) for v in values], reverse=True)[:3]
        return sum(ordered) / len(ordered)

    lane_1d = _top_avg(lane_scores["1d"])
    lane_3d = _top_avg(lane_scores["3d"])
    lane_3d_count = len(lane_scores["3d"])
    lane_3d_evidence = _top_avg(lane_evidence["3d"])
    # Lowered from 150 to 8: typical KOSDAQ run has 50-100 candidates, few reach 3D lane
    if lane_3d_count < 8 or lane_3d_evidence < 3.0:
        return "1d"
    if lane_3d >= lane_1d + 6.0:
        return "3d"
    return "1d"


def compute_kr_basket_priority(
    candidate: Dict[str, Any],
    run_market: str,
    active_lane: str,
) -> Dict[str, Any]:
    quant_meta = candidate.get("_quant_rerank", {}) if isinstance(candidate.get("_quant_rerank"), dict) else {}
    market = str(run_market or "").upper()
    lane = str(quant_meta.get("lane", "raw") or "raw")
    score = _safe_float(quant_meta.get("score", candidate.get("score")), 0.0)
    score_1d = _safe_float(quant_meta.get("score_1d", score), score)
    score_3d = _safe_float(quant_meta.get("score_3d", score), score)

    if market != "KOSDAQ" or active_lane not in {"1d", "3d"}:
        return {"score": round(score, 2), "lane": lane, "active_lane": active_lane, "delta": 0.0}

    if lane == active_lane:
        boosted = (score_1d if lane == "1d" else score_3d) + 4.0
        return {"score": round(boosted, 2), "lane": lane, "active_lane": active_lane, "delta": 4.0}

    secondary_score = (score_1d if lane == "1d" else score_3d) - 8.0
    return {"score": round(secondary_score, 2), "lane": lane, "active_lane": active_lane, "delta": -8.0}
