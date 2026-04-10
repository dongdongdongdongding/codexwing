from __future__ import annotations

from typing import Any, Dict


_EXCEPTION_GATE_RULES: Dict[str, Dict[str, float]] = {
    "YELLOW": {
        "min_strength": 24.0,
        "min_membership": 0.85,
        "min_leader_score": 70.0,
        "min_turnover_ratio": 0.85,
        "min_turnover_growth": 1.0,
        "min_breakout_quality": 42.0,
        "min_close_location": 70.0,
        "score_bonus": 2.0,
    },
    "RED": {
        "min_strength": 30.0,
        "min_membership": 0.90,
        "min_leader_score": 74.0,
        "min_turnover_ratio": 1.00,
        "min_turnover_growth": 1.2,
        "min_breakout_quality": 48.0,
        "min_close_location": 76.0,
        "score_bonus": 1.5,
    },
}


def route_theme_candidate(
    *,
    theme_context: Dict[str, Any],
    leader_metrics: Dict[str, Any],
    market_gate: str,
) -> Dict[str, Any]:
    primary_theme = str(theme_context.get("primary_theme") or "").strip().lower()
    if primary_theme in {"", "unclassified"} or bool(theme_context.get("is_spac", False)):
        return {
            "routing_path": "core_only",
            "score_adjustment": 0.0,
            "exception_allowance": False,
            "reasons": [],
        }
    direction = str(theme_context.get("theme_direction") or "NEUTRAL").upper()
    strength = float(theme_context.get("theme_strength_score", 0.0) or 0.0)
    membership = float(theme_context.get("theme_membership_confidence", 0.0) or 0.0)
    theme_source = str(theme_context.get("theme_source") or "").strip().lower()
    leader_score = float(leader_metrics.get("leader_score", 0.0) or 0.0)
    theme_rank_raw = leader_metrics.get("theme_rank")
    try:
        theme_rank = int(theme_rank_raw) if theme_rank_raw is not None else None
    except Exception:
        theme_rank = None
    breakout_quality = float(leader_metrics.get("breakout_quality_score", 0.0) or 0.0)
    close_location = float(leader_metrics.get("close_location_score", 0.0) or 0.0)
    turnover_ratio = float(leader_metrics.get("turnover_ratio_vs_float_cap", 0.0) or 0.0)
    turnover_growth = float(leader_metrics.get("turnover_growth_5d", 0.0) or 0.0)
    gate = str(market_gate or "GREEN").upper()

    score_adjustment = 0.0
    reasons = []
    routing_path = "core_only"
    exception_allowance = False

    if direction == "BENEFICIARY" and strength >= 18 and membership >= 0.6:
        score_adjustment += min(8.0, max(0.0, (strength - 18.0) * 0.2 + 1.0))
        reasons.append("THEME_BENEFICIARY")
        routing_path = "theme_shadow"
    elif direction == "HEADWIND" and strength >= 45:
        score_adjustment -= min(8.0, (strength - 35.0) * 0.12)
        reasons.append("THEME_HEADWIND")
        routing_path = "theme_shadow"

    if leader_score >= 68:
        score_adjustment += 2.5
        reasons.append("THEME_LEADER_SCORE_HIGH")
    elif leader_score <= 40 and direction == "BENEFICIARY":
        score_adjustment -= 1.5
        reasons.append("THEME_LEADER_WEAK")

    if theme_rank in (1, 2):
        score_adjustment += 1.5
        reasons.append(f"THEME_LEADER_TOP{theme_rank}")

    pre_rank_strong_leader = (
        theme_rank is None
        and leader_score >= 70
        and turnover_ratio >= 0.9
        and (breakout_quality >= 42 or close_location >= 70)
    )
    if pre_rank_strong_leader:
        score_adjustment += 1.0
        reasons.append("THEME_LEADER_PRE_RANK_STRONG")

    if breakout_quality >= 72:
        score_adjustment += 1.5
        reasons.append("TURNOVER_BREAKOUT_CONFIRMED")

    gate_rule = _EXCEPTION_GATE_RULES.get(gate)
    strict_exception_candidate = False
    if (
        gate_rule
        and direction == "BENEFICIARY"
        and theme_source == "stock_master"
        and strength >= gate_rule["min_strength"]
        and membership >= gate_rule["min_membership"]
        and leader_score >= gate_rule["min_leader_score"]
        and turnover_ratio >= gate_rule["min_turnover_ratio"]
        and turnover_growth >= gate_rule["min_turnover_growth"]
        and (breakout_quality >= gate_rule["min_breakout_quality"] or close_location >= gate_rule["min_close_location"])
    ):
        if gate == "RED":
            strict_exception_candidate = theme_rank == 1 or pre_rank_strong_leader
        else:
            strict_exception_candidate = theme_rank in (1, 2) or pre_rank_strong_leader
    if strict_exception_candidate:
        exception_allowance = True
        routing_path = "theme_exception_candidate"
        score_adjustment += float(gate_rule["score_bonus"]) if gate_rule else 2.0
        reasons.append("THEME_EXCEPTION_ALLOWANCE")
        reasons.append(f"THEME_EXCEPTION_{gate}_STRICT")
        if theme_rank in (1, 2):
            reasons.append(f"THEME_ROUTE_READY_TOP{theme_rank}")
        else:
            reasons.append("THEME_ROUTE_READY_PRE_RANK")

    return {
        "routing_path": routing_path,
        "score_adjustment": round(float(score_adjustment), 2),
        "exception_allowance": bool(exception_allowance),
        "reasons": reasons[:6],
    }
