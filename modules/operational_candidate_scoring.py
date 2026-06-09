from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Tuple

from modules.kis_model_features import flatten_kis_model_features
from modules.kis_ticker_valuechain_master import load_ticker_valuechain_master


OPERATIONAL_CANDIDATE_SCORE_VERSION = "operational_candidate_score_axes_v1"
DEFAULT_BUY_PREMIUM_PCT = 2.0


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        text = value.strip()
        return bool(text) and text.lower() not in {"none", "nan", "null", "-"}
    if isinstance(value, float):
        return math.isfinite(value)
    return True


def _first(*values: Any) -> Any:
    for value in values:
        if _present(value):
            return value
    return None


def _num(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
        numeric = float(value)
        if not math.isfinite(numeric):
            return None
        return numeric
    except Exception:
        return None


def _clip(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(value)))


def _weighted(parts: Iterable[Tuple[float | None, float, str]], reasons: list[str]) -> float:
    total = 0.0
    weight = 0.0
    for value, part_weight, reason in parts:
        if value is None:
            continue
        total += _clip(value) * float(part_weight)
        weight += float(part_weight)
        if reason:
            reasons.append(reason)
    return round(total / weight, 4) if weight else 0.0


def _dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _nested(row: Mapping[str, Any], *keys: str) -> Any:
    cur: Any = row
    for key in keys:
        if not isinstance(cur, Mapping):
            return None
        cur = cur.get(key)
    return cur


def adjust_return_for_buy_premium(return_pct: Any, buy_premium_pct: float = DEFAULT_BUY_PREMIUM_PCT) -> float | None:
    raw = _num(return_pct)
    if raw is None:
        return None
    premium = max(0.0, float(buy_premium_pct or 0.0))
    adjusted = ((1.0 + raw / 100.0) / (1.0 + premium / 100.0) - 1.0) * 100.0
    return round(adjusted, 6)


@lru_cache(maxsize=1)
def _valuechain_profiles() -> Dict[str, Dict[str, Any]]:
    try:
        payload = load_ticker_valuechain_master(Path("runtime_state/long_term/kis_ticker_valuechain/master.json"))
    except Exception:
        return {}
    profiles = payload.get("profiles") or payload.get("ticker_valuechain_profiles") or payload.get("ticker_profiles") or {}
    if isinstance(profiles, Mapping):
        return {str(key).upper(): _dict(value) for key, value in profiles.items()}
    out: Dict[str, Dict[str, Any]] = {}
    if isinstance(profiles, list):
        for profile in profiles:
            if not isinstance(profile, Mapping):
                continue
            ticker = str(profile.get("ticker") or "").upper()
            if ticker:
                out[ticker] = dict(profile)
    return out


def _kis_features(row: Mapping[str, Any]) -> Dict[str, Any]:
    try:
        return flatten_kis_model_features(row)
    except Exception:
        return {}


def _chart_axis(row: Mapping[str, Any]) -> tuple[float, list[str]]:
    reasons: list[str] = []
    trend = str(_first(row.get("real_trend"), row.get("trend"), row.get("Trend")) or "").upper()
    position = str(_first(row.get("position"), row.get("Position")) or "").lower()
    strategy = str(_first(row.get("strategy"), row.get("note"), row.get("rationale")) or "")
    tech = _num(_first(row.get("tech_score"), row.get("Tech Score")))
    alpha = _num(_first(row.get("alpha_score"), row.get("alpha"), row.get("Alpha Score")))
    volume_ratio = _num(_first(row.get("volume_ratio"), row.get("Volume Ratio"), row.get("vol_ratio")))
    volume_confirmed = str(row.get("volume_confirmed") or "").lower() in {"true", "1", "yes", "y"}

    trend_score = 50.0
    if trend == "UP":
        trend_score = 82.0
    elif trend == "DOWN":
        trend_score = 20.0

    position_score = 50.0
    if "rising" in position:
        position_score = 82.0
    elif "resting" in position:
        position_score = 62.0
    elif "peak" in position:
        position_score = 34.0

    overheat = any(token in strategy for token in ("과열", "Overheat", "Exhaustion"))
    divergence = "RSI_DIV" in strategy or "OBV_DIV" in strategy
    pattern_score = 50.0
    if overheat:
        pattern_score -= 22.0
    if divergence:
        pattern_score -= 16.0
    if "ContextTailwind" in strategy or "Profile:POSITIVE" in strategy:
        pattern_score += 12.0

    volume_score = None
    if volume_ratio is not None:
        if volume_ratio >= 2.5:
            volume_score = 88.0
        elif volume_ratio >= 1.5:
            volume_score = 74.0
        elif volume_ratio >= 1.0 or volume_confirmed:
            volume_score = 58.0
        else:
            volume_score = 30.0

    return _weighted(
        [
            (tech, 1.0, "tech_score"),
            (alpha, 0.7, "alpha_score"),
            (trend_score, 1.0, f"trend={trend or 'UNKNOWN'}"),
            (position_score, 0.8, f"position={position or 'unknown'}"),
            (pattern_score, 0.6, "pattern_risk"),
            (volume_score, 0.8, "volume_ratio"),
        ],
        reasons,
    ), reasons[:8]


def _flow_axis(row: Mapping[str, Any], kis: Mapping[str, Any]) -> tuple[float, list[str]]:
    reasons: list[str] = []
    whale = _num(_first(row.get("whale_score"), kis.get("kis_whale_score"), kis.get("kis_prefilter_flow_whale_score")))
    flow_consensus = str(_first(row.get("flow_consensus_buying"), row.get("flow_consensus")) or "").lower() in {
        "true",
        "1",
        "yes",
    }
    retail_dominant = str(row.get("retail_dominant") or "").lower() in {"true", "1", "yes"}
    foreigner = _num(_first(row.get("foreigner_1d"), row.get("foreign_flow"), kis.get("kis_foreigner_1d"), kis.get("kis_prefilter_flow_foreigner_1d")))
    institution = _num(_first(row.get("institution_1d"), row.get("institution_flow"), kis.get("kis_institution_1d"), kis.get("kis_prefilter_flow_institution_1d")))
    whale_3d = _num(_first(row.get("whale_flow_3d"), kis.get("kis_whale_flow_3d")))

    smart_flow = None
    if foreigner is not None or institution is not None:
        total = float(foreigner or 0.0) + float(institution or 0.0)
        if total > 0:
            smart_flow = 72.0
        elif total < 0:
            smart_flow = 28.0
        else:
            smart_flow = 45.0

    consensus_score = 80.0 if flow_consensus else None
    retail_score = 25.0 if retail_dominant else None
    whale_flow_score = None
    if whale_3d is not None:
        whale_flow_score = 70.0 if whale_3d > 0 else 30.0 if whale_3d < 0 else 45.0

    return _weighted(
        [
            (whale, 1.2, "whale_score"),
            (smart_flow, 1.0, "foreign_institution_flow"),
            (consensus_score, 0.8, "flow_consensus"),
            (retail_score, 0.6, "retail_dominant_penalty"),
            (whale_flow_score, 0.8, "whale_flow_3d"),
        ],
        reasons,
    ), reasons[:8]


def _market_axis(row: Mapping[str, Any]) -> tuple[float, list[str]]:
    reasons: list[str] = []
    gate = str(_first(row.get("market_gate"), _nested(row, "market_gate", "gate")) or "").upper()
    gate_score = None
    if gate:
        gate_score = {"GREEN": 82.0, "YELLOW": 52.0, "RED": 18.0}.get(gate, 45.0)
    breadth = _num(_first(row.get("regime_breadth_pct"), row.get("breadth_pct"), _nested(row, "market_gate", "breadth_pct")))
    avg_chg = _num(_first(row.get("regime_avg_chg"), row.get("avg_chg"), row.get("kosdaq_chg"), _nested(row, "market_gate", "primary_chg")))
    volatility = _num(_first(row.get("regime_volatility_20d"), _nested(row, "market_gate", "volatility_20d")))

    change_score = None
    if avg_chg is not None:
        change_score = _clip(50.0 + avg_chg * 18.0)
    vol_score = None
    if volatility is not None:
        vol_score = _clip(80.0 - max(0.0, volatility - 1.5) * 12.0)

    return _weighted(
        [
            (gate_score, 1.2, f"market_gate={gate or 'UNKNOWN'}"),
            (breadth, 0.8, "market_breadth"),
            (change_score, 0.7, "market_change"),
            (vol_score, 0.6, "market_volatility"),
        ],
        reasons,
    ), reasons[:8]


def _theme_axis(row: Mapping[str, Any], kis: Mapping[str, Any]) -> tuple[float, list[str]]:
    reasons: list[str] = []
    theme = _dict(row.get("theme_context")) or _dict(row.get("theme"))
    primary = str(_first(theme.get("primary_theme"), row.get("primary_theme"), row.get("Theme")) or "").strip()
    direction = str(_first(theme.get("theme_direction"), row.get("theme_direction")) or "").upper()
    strength = _num(_first(theme.get("theme_strength_score"), row.get("theme_strength_score")))
    momentum = _num(_first(row.get("theme_momentum_pct"), theme.get("theme_momentum_pct")))
    evidence_score = _num(_first(row.get("kis_theme_news_score"), kis.get("kis_theme_news_evidence_score")))
    ticker = str(_first(row.get("ticker"), row.get("Ticker"), row.get("symbol")) or "").upper()
    valuechain_profile = _valuechain_profiles().get(ticker, {})
    verified_edges = _num(valuechain_profile.get("verified_edge_count"))

    theme_identity = None
    if primary and primary.lower() != "unclassified":
        theme_identity = 45.0
    direction_score = None
    if direction:
        direction_score = {"BENEFICIARY": 78.0, "TAILWIND": 78.0, "HEADWIND": 22.0, "NEUTRAL": 45.0}.get(direction, 45.0)
    momentum_score = None
    if momentum is not None:
        momentum_score = _clip(50.0 + momentum * 10.0)
    valuechain_score = None
    if verified_edges is not None and verified_edges > 0:
        valuechain_score = _clip(70.0 + min(verified_edges, 3.0) * 8.0)

    return _weighted(
        [
            (theme_identity, 0.6, f"theme={primary}" if primary else ""),
            (strength, 1.0, "theme_strength"),
            (direction_score, 0.8, f"theme_direction={direction}" if direction else ""),
            (momentum_score, 0.7, "theme_momentum"),
            (evidence_score, 1.0, "kis_theme_news_evidence"),
            (valuechain_score, 1.1, "official_valuechain"),
        ],
        reasons,
    ), reasons[:8]


def _financial_news_axis(row: Mapping[str, Any], kis: Mapping[str, Any]) -> tuple[float, list[str]]:
    reasons: list[str] = []
    per = _num(_first(row.get("per"), row.get("PER"), kis.get("kis_per"), kis.get("kis_prefilter_quote_per")))
    pbr = _num(_first(row.get("pbr"), row.get("PBR"), kis.get("kis_pbr"), kis.get("kis_prefilter_quote_pbr")))
    market_cap = _num(_first(row.get("market_cap"), kis.get("kis_market_cap"), kis.get("kis_prefilter_quote_market_cap")))
    news_count = _num(_first(row.get("kis_news_title_count"), kis.get("kis_news_title_count"), kis.get("kis_theme_news_news_count")))
    risk_tag_count = _num(kis.get("kis_theme_news_risk_tag_count"))
    positive_tag_count = _num(kis.get("kis_theme_news_positive_tag_count"))
    news_blocked = _num(kis.get("kis_theme_news_promotion_blocked"))
    stock_admin = str(_first(kis.get("kis_stock_admin_item"), row.get("admin_item")) or "").lower() in {"true", "1", "yes", "y"}
    trade_stop = str(_first(kis.get("kis_stock_trade_stop"), row.get("trade_stop")) or "").lower() in {"true", "1", "yes", "y"}

    valuation = None
    if per is not None or pbr is not None:
        valuation = 55.0
        if per is not None and 0.0 < per <= 35.0:
            valuation += 12.0
        elif per is not None and per > 80.0:
            valuation -= 15.0
        if pbr is not None and 0.0 < pbr <= 4.0:
            valuation += 8.0
        elif pbr is not None and pbr > 10.0:
            valuation -= 12.0

    size_score = None
    if market_cap is not None:
        size_score = 35.0 if market_cap <= 0 else 62.0
    news_score = None
    if news_count is not None:
        news_score = _clip(40.0 + min(news_count, 5.0) * 8.0)
        if positive_tag_count:
            news_score += min(positive_tag_count, 3.0) * 6.0
        if risk_tag_count:
            news_score -= min(risk_tag_count, 3.0) * 10.0
        if news_blocked:
            news_score = min(news_score, 25.0)
    status_score = 20.0 if stock_admin or trade_stop else None

    return _weighted(
        [
            (valuation, 1.0, "valuation_per_pbr"),
            (size_score, 0.5, "market_cap"),
            (news_score, 1.0, "news_evidence"),
            (status_score, 1.0, "listing_status_penalty"),
        ],
        reasons,
    ), reasons[:8]


def build_operational_candidate_score(
    row: Mapping[str, Any],
    *,
    buy_premium_pct: float = DEFAULT_BUY_PREMIUM_PCT,
) -> Dict[str, Any]:
    row = row if isinstance(row, Mapping) else {}
    kis = _kis_features(row)
    chart, chart_reasons = _chart_axis(row)
    flow, flow_reasons = _flow_axis(row, kis)
    market, market_reasons = _market_axis(row)
    theme, theme_reasons = _theme_axis(row, kis)
    financial_news, financial_reasons = _financial_news_axis(row, kis)
    axes = {
        "chart": chart,
        "flow": flow,
        "market": market,
        "theme_valuechain": theme,
        "financial_news": financial_news,
    }
    non_chart_values = [flow, market, theme, financial_news]
    non_chart_avg = round(sum(non_chart_values) / len(non_chart_values), 4) if non_chart_values else 0.0
    total = round(chart * 0.28 + flow * 0.22 + market * 0.16 + theme * 0.18 + financial_news * 0.16, 4)
    axis_sum = sum(max(0.0, value) for value in axes.values())
    chart_dominance = round((chart / axis_sum * 100.0) if axis_sum else 0.0, 4)
    chart_only = bool(chart >= 70.0 and (non_chart_avg < 45.0 or chart_dominance >= 48.0))
    weak_support_axes = [key for key, value in axes.items() if key != "chart" and value < 35.0]
    if chart_only:
        action_level = "OBSERVE_CHART_ONLY"
        action_label = "차트 편중 관찰"
    elif total >= 65.0 and non_chart_avg >= 50.0 and market >= 45.0:
        action_level = "OPERABLE"
        action_label = "운용 후보"
    elif total >= 50.0:
        action_level = "WATCH_VALIDATE"
        action_label = "검증 후보"
    else:
        action_level = "AVOID_WEAK_SUPPORT"
        action_label = "운용 보류"

    returns = {
        "return_1d_pct": adjust_return_for_buy_premium(row.get("return_1d_pct"), buy_premium_pct),
        "return_3d_pct": adjust_return_for_buy_premium(row.get("return_3d_pct"), buy_premium_pct),
        "return_5d_pct": adjust_return_for_buy_premium(row.get("return_5d_pct"), buy_premium_pct),
        "base_expected_value_5d_pct": adjust_return_for_buy_premium(
            _nested(row, "realized_expectancy_admission", "base_expected_value_5d_pct")
            or row.get("base_expected_value_5d_pct"),
            buy_premium_pct,
        ),
        "stress_expected_value_5d_pct": adjust_return_for_buy_premium(
            _nested(row, "realized_expectancy_admission", "stress_expected_value_5d_pct")
            or row.get("stress_expected_value_5d_pct"),
            buy_premium_pct,
        ),
    }
    return {
        "version": OPERATIONAL_CANDIDATE_SCORE_VERSION,
        "buy_premium_pct": float(buy_premium_pct),
        "axes": axes,
        "axis_reasons": {
            "chart": chart_reasons,
            "flow": flow_reasons,
            "market": market_reasons,
            "theme_valuechain": theme_reasons,
            "financial_news": financial_reasons,
        },
        "total_score": total,
        "non_chart_avg_score": non_chart_avg,
        "chart_dominance_pct": chart_dominance,
        "chart_only": chart_only,
        "weak_support_axes": weak_support_axes,
        "action_level": action_level,
        "action_label": action_label,
        "return_after_buy_premium_pct": returns,
    }


def attach_operational_candidate_score(
    row: Mapping[str, Any],
    *,
    buy_premium_pct: float = DEFAULT_BUY_PREMIUM_PCT,
) -> Dict[str, Any]:
    out = dict(row) if isinstance(row, Mapping) else {}
    score = build_operational_candidate_score(out, buy_premium_pct=buy_premium_pct)
    out["operational_score_axes"] = score
    out["operational_action_level"] = score.get("action_level")
    out["operational_action_label"] = score.get("action_label")
    out["chart_dominance_pct"] = score.get("chart_dominance_pct")
    out["chart_only_candidate"] = bool(score.get("chart_only"))
    return out


__all__ = [
    "DEFAULT_BUY_PREMIUM_PCT",
    "OPERATIONAL_CANDIDATE_SCORE_VERSION",
    "adjust_return_for_buy_premium",
    "attach_operational_candidate_score",
    "build_operational_candidate_score",
]
