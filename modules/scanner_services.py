from __future__ import annotations

import os
from typing import Any, Callable, Dict, Optional

from modules import quant_analysis
from modules.kr_regime_ranker import predict_rank_overlay
from modules.regime_market_policy import evaluate_market_policy
from modules.regime_ticker_profiles import (
    apply_profile_to_setup,
    compute_profile_adjustment,
    get_ticker_profile,
    resolve_profile_market,
    resolve_profile_regime,
)
from modules.theme_catalog import primary_theme, resolve_theme_memberships
from modules.theme_leader_ranker import compute_theme_leader_metrics
from modules.theme_router import route_theme_candidate
from modules.theme_signal_engine import theme_state_lookup


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return float(default)


def _clamp_float(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _safe_last(series: Any, default: float = 0.0) -> float:
    try:
        if series is None or len(series) == 0:
            return float(default)
        value = series.iloc[-1]
        return float(value)
    except Exception:
        return float(default)


def _safe_numeric(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _theme_flat_fields(theme_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    ctx = theme_context if isinstance(theme_context, dict) else {}
    return {
        "primary_theme": ctx.get("primary_theme"),
        "theme_source": ctx.get("theme_source"),
        "theme_inference_status": ctx.get("theme_inference_status"),
        "secondary_themes": ctx.get("secondary_themes") or [],
        "theme_routing_path": ctx.get("routing_path") or "",
    }


def compute_expected_edge_profile(
    *,
    prob_5: float,
    prob_clean: float,
    decision_score: float,
    conviction_score: float,
    real_trend: str,
    routing_path: str,
    scan_mode: str,
    market_gate: str,
    theme_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    theme_ctx = theme_context if isinstance(theme_context, dict) else {}
    direction = str(theme_ctx.get("theme_direction") or "").upper()
    strength = float(theme_ctx.get("theme_strength_score", 0.0) or 0.0)
    route = str(routing_path or "").lower()
    mode = str(scan_mode or "SWING").upper()
    gate = str(market_gate or "GREEN").upper()
    trend = str(real_trend or "").upper()

    edge_score = (
        (float(prob_5) - 50.0) * 0.42
        + (float(prob_clean) - 50.0) * 0.55
        + (float(decision_score) - 65.0) * 0.20
        + (float(conviction_score) - 60.0) * 0.12
    )
    if trend == "UP":
        edge_score += 4.0
    elif trend == "DOWN":
        edge_score -= 6.0

    if direction == "BENEFICIARY":
        edge_score += min(4.5, strength / 20.0)
    elif direction == "HEADWIND":
        edge_score -= min(5.0, strength / 18.0)

    if route == "theme_routed":
        edge_score += 2.0
    elif route == "theme_shadow":
        edge_score += 0.7

    if gate == "RED":
        edge_score -= 2.5
    elif gate == "YELLOW":
        edge_score -= 1.0

    mode_multiplier = 0.11 if mode == "INTRADAY" else 0.085
    expected_1d = _clamp_float(edge_score * mode_multiplier, -4.0, 6.0)
    expected_3d = _clamp_float(
        expected_1d * (1.55 if mode == "INTRADAY" else 1.95) + (0.45 if mode == "SWING" else 0.15),
        -6.0,
        10.0,
    )

    return {
        "expected_edge_score": round(float(edge_score), 2),
        "expected_return_1d_pct": round(float(expected_1d), 2),
        "expected_return_3d_pct": round(float(expected_3d), 2),
    }


def _intraday_position_label(close_price: float, ema_fast: float, ema_slow: float, breakout: bool) -> str:
    if breakout and close_price > ema_fast > ema_slow:
        return "🚀 Intraday Breakout"
    if close_price > ema_fast > ema_slow:
        return "📈 Intraday Trend"
    if close_price >= ema_slow:
        return "🟡 Reclaim"
    return "🔻 Weak"


def _intraday_market_key(sym: str, is_us: bool, is_amex: bool) -> str:
    ticker = str(sym).upper()
    if is_amex:
        return "AMEX"
    if is_us:
        return "US"
    if ticker.endswith('.KQ'):
        return "KOSDAQ"
    if ticker.endswith('.KS'):
        return "KOSPI"
    return "KR"


def resolve_strategy_family(market_type: str, *, is_amex: bool = False) -> str:
    market = str(market_type or "").upper()
    if is_amex or market == "AMEX":
        return "AMEX_MOONSHOT"
    if market in {"US", "NASDAQ", "S&P500", "SP500", "NYSE"}:
        return "US_MAIN"
    if market in {"KOSPI", "KOSDAQ", "KR"}:
        return "KR_CORE"
    return "GENERAL"


def build_theme_overlay(
    *,
    sym: str,
    stock_name: str,
    market_type: str,
    intel_data: Any,
    market_gate: str,
    df: Any,
    current_price: float,
    volume_ratio: float,
    decision_score: float,
    scan_mode: str,
) -> Dict[str, Any]:
    memberships = resolve_theme_memberships(
        ticker=sym,
        stock_name=stock_name,
        market=market_type,
        extra_texts=[
            str(intel_data.get("key_insight", "")) if isinstance(intel_data, dict) else "",
            " ".join(str(x) for x in (intel_data.get("beneficiary_keywords", []) or [])) if isinstance(intel_data, dict) else "",
        ],
    )
    primary = primary_theme(memberships)
    primary_theme_name = str(primary.get("theme_name") or "").strip()
    theme_source = str(primary.get("theme_source") or "")
    theme_inference_status = str(primary.get("theme_inference_status") or "")
    secondary_themes = [str(x or "").strip() for x in (primary.get("secondary_themes", []) or []) if str(x or "").strip()]
    is_spac = bool(primary.get("is_spac", False))
    theme_disabled = primary_theme_name in {"", "unclassified"} or is_spac
    state_lookup = theme_state_lookup(intel_data if isinstance(intel_data, dict) else {})
    state = {}
    if not theme_disabled:
        state = state_lookup.get(str(primary.get("theme_id") or ""), {}) or state_lookup.get(primary_theme_name, {}) or {}
    theme_direction = str(state.get("direction") or "NEUTRAL").upper()
    theme_strength = float(state.get("strength_score", 0.0) or 0.0)
    theme_reasons = list(primary.get("reasons", []) or [])
    if state.get("evidence"):
        theme_reasons.extend([f"evidence:{x}" for x in list(state.get("evidence", []))[:2]])
    leader_metrics = compute_theme_leader_metrics(
        df=df,
        current_price=float(current_price or 0.0),
        volume_ratio=float(volume_ratio or 1.0),
        decision_score=float(decision_score or 0.0),
        primary_theme=primary_theme_name,
        scan_mode=scan_mode,
    ) if not theme_disabled else {}
    router = route_theme_candidate(
        theme_context={
            "primary_theme": primary_theme_name,
            "theme_direction": theme_direction,
            "theme_strength_score": theme_strength,
            "theme_membership_confidence": float(primary.get("confidence", 0.0) or 0.0),
            "theme_source": theme_source,
            "theme_inference_status": theme_inference_status,
            "secondary_themes": secondary_themes,
            "is_spac": is_spac,
        },
        leader_metrics=leader_metrics,
        market_gate=str(market_gate or "GREEN"),
    ) if not theme_disabled else {"routing_path": "core_only", "score_adjustment": 0.0, "exception_allowance": False, "reasons": []}
    if is_spac:
        theme_reasons.append("spac_excluded")
    if primary_theme_name == "unclassified":
        theme_reasons.append("unclassified_theme")
    return {
        "theme_context": {
            "primary_theme": primary_theme_name,
            "theme_direction": theme_direction,
            "theme_strength_score": round(theme_strength, 1),
            "theme_membership_confidence": round(float(primary.get("confidence", 0.0) or 0.0), 3),
            "theme_source": theme_source,
            "theme_inference_status": theme_inference_status,
            "secondary_themes": secondary_themes,
            "is_spac": is_spac,
            "routing_path": str(router.get("routing_path") or "core_only"),
            "theme_reasons": sorted(dict.fromkeys(theme_reasons + list(router.get("reasons", []) or [])))[:8],
            "matched_themes": [
                {
                    "theme_name": str(item.get("theme_name") or ""),
                    "confidence": float(item.get("confidence", 0.0) or 0.0),
                    "theme_source": str(item.get("theme_source") or ""),
                }
                for item in memberships[:4]
            ],
        },
        "leader_metrics": leader_metrics,
        "routing_path": str(router.get("routing_path") or "core_only"),
        "score_adjustment": float(router.get("score_adjustment", 0.0) or 0.0),
        "exception_allowance": bool(router.get("exception_allowance", False)),
    }


def _activate_theme_route(theme_overlay: Dict[str, Any], reason: str) -> Dict[str, Any]:
    overlay = dict(theme_overlay or {})
    theme_context = dict(overlay.get("theme_context", {}) or {})
    reasons = list(theme_context.get("theme_reasons", []) or [])
    if reason and reason not in reasons:
        reasons.append(reason)
    theme_context["theme_reasons"] = reasons[:10]
    theme_context["routing_path"] = "theme_routed"
    overlay["theme_context"] = theme_context
    overlay["routing_path"] = "theme_routed"
    return overlay


def evaluate_intraday_candidate(
    sym: str,
    stock_name: str,
    qs: Any,
    is_us: bool,
    is_amex: bool,
    r_status: str,
    intel_data: Any,
    market_gate: Dict[str, Any],
    news_adjustment_fn: Callable[..., Dict[str, Any]],
    reject_reason_fn: Optional[Callable[[str], None]] = None,
    reject_meta_fn: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Optional[Dict[str, Dict[str, Any]]]:
    def _reject(reason: str, meta: Optional[Dict[str, Any]] = None) -> None:
        if reject_reason_fn is not None:
            try:
                reject_reason_fn(reason)
            except Exception:
                pass
        if reject_meta_fn is not None:
            try:
                payload = {"ticker": sym, "stock_name": stock_name, "stage": "intraday", "reason": reason}
                if isinstance(meta, dict):
                    payload.update(meta)
                reject_meta_fn(payload)
            except Exception:
                pass

    if qs.df is None or qs.df.empty or len(qs.df) < 30:
        _reject("INTRADAY_HISTORY_SHORT")
        return None

    df = qs.df.copy()
    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    volume = df["Volume"].astype(float)

    close_now = _safe_last(close)
    if close_now <= 0:
        _reject("INTRADAY_INVALID_PRICE")
        return None

    market_key = _intraday_market_key(sym, is_us=is_us, is_amex=is_amex)
    min_price = 1.0 if is_amex else (5.0 if is_us else 1000.0)
    min_volume = _env_float("AG_INTRADAY_AMEX_MIN_VOLUME", 20_000) if is_amex else (
        _env_float("AG_INTRADAY_US_MIN_VOLUME", 40_000) if is_us else _env_float("AG_INTRADAY_KR_MIN_VOLUME", 20_000)
    )
    avg_volume_5 = max(_safe_last(volume.tail(5).rolling(5, min_periods=2).mean(), _safe_last(volume)), 0.0)
    curr_volume = max(_safe_last(volume), 0.0)
    curr_turnover = close_now * curr_volume
    avg_turnover_5 = _safe_last((close * volume).tail(5).rolling(5, min_periods=2).mean(), curr_turnover)
    min_turnover = {
        "KOSPI": _env_float("AG_INTRADAY_KOSPI_MIN_TURNOVER", 700_000_000),
        "KOSDAQ": _env_float("AG_INTRADAY_KOSDAQ_MIN_TURNOVER", 300_000_000),
        "KR": _env_float("AG_INTRADAY_KR_MIN_TURNOVER", 300_000_000),
        "US": _env_float("AG_INTRADAY_US_MIN_TURNOVER", 1_500_000),
        "AMEX": _env_float("AG_INTRADAY_AMEX_MIN_TURNOVER", 400_000),
    }.get(market_key, 300_000_000)
    liquidity_score = max(curr_turnover, avg_turnover_5)
    if close_now < min_price or (curr_volume < min_volume and avg_volume_5 < min_volume) or liquidity_score < min_turnover:
        _reject(
            "INTRADAY_MIN_PRICE_VOLUME_FAIL",
            {
                "curr_price": round(close_now, 4),
                "curr_volume": round(curr_volume, 2),
                "avg_volume_5": round(avg_volume_5, 2),
                "curr_turnover": round(curr_turnover, 2),
                "avg_turnover_5": round(avg_turnover_5, 2),
                "min_price": min_price,
                "min_volume": min_volume,
                "min_turnover": min_turnover,
                "market_key": market_key,
            },
        )
        return None

    ema_fast = _safe_last(close.ewm(span=8, adjust=False).mean(), close_now)
    ema_slow = _safe_last(close.ewm(span=20, adjust=False).mean(), close_now)
    avg_vol20 = max(_safe_last(volume.tail(20).rolling(20, min_periods=5).mean(), _safe_last(volume)), 1.0)
    vol_ratio = _safe_last(volume) / avg_vol20 if avg_vol20 > 0 else 1.0
    prev_high_3 = float(high.tail(4).iloc[:-1].max()) if len(high) >= 4 else close_now
    breakout = close_now >= prev_high_3 * 0.998 if prev_high_3 > 0 else False

    try:
        latest_date = df.index[-1].date()
        session_rows = df[df.index.date == latest_date]
        session_open = float(session_rows["Open"].iloc[0]) if not session_rows.empty else close_now
        prev_session = df[df.index.date < latest_date]
        prev_session_close = float(prev_session["Close"].iloc[-1]) if not prev_session.empty else session_open
    except Exception:
        session_open = close_now
        prev_session_close = close_now

    intraday_ret = ((close_now / session_open) - 1.0) * 100.0 if session_open > 0 else 0.0
    day_ret = ((close_now / prev_session_close) - 1.0) * 100.0 if prev_session_close > 0 else 0.0

    tr = (high - low).abs()
    atr_pct = _safe_last((tr.rolling(14, min_periods=5).mean() / close.replace(0, float("nan"))) * 100.0, 1.2)
    stop_pct = max(0.8, min(3.5, atr_pct * 0.9))
    target_pct = max(1.5, min(8.0, atr_pct * 1.8))

    news_adj = news_adjustment_fn(stock_name, sym, "", intel_data)
    ml_pred = qs.get_ml_prediction() or {}
    model_prob = float(ml_pred.get("prob", 50) or 50)
    model_clean_prob = float(ml_pred.get("clean_prob", model_prob) or model_prob)
    gate = str((market_gate or {}).get("gate", "GREEN")).upper()
    gate_penalty = {"GREEN": 0.0, "YELLOW": 2.0, "RED": 5.0}.get(gate, 0.0)

    trend_points = 18.0 if close_now > ema_fast > ema_slow else (10.0 if close_now > ema_slow else -12.0)
    breakout_points = 18.0 if breakout else 0.0
    volume_points = max(-4.0, min(16.0, (vol_ratio - 1.0) * 10.0))
    momentum_points = max(-8.0, min(14.0, day_ret * 2.0))
    model_points = ((model_prob - 50.0) * 0.25) + ((model_clean_prob - 50.0) * 0.15)
    score_raw = 52.0 + trend_points + breakout_points + volume_points + momentum_points + model_points + float(news_adj.get("score_adjustment", 0))
    decision_score = round(_clamp_float(score_raw - gate_penalty, 0.0, 100.0), 1)
    alpha_score = round(_clamp_float(45.0 + trend_points + breakout_points + momentum_points * 0.7, 0.0, 100.0), 1)
    heuristic_prob_5 = round(_clamp_float(35.0 + trend_points * 0.8 + breakout_points * 0.7 + volume_points * 0.6 - gate_penalty, 1.0, 99.0), 1)
    heuristic_prob_clean = round(_clamp_float(30.0 + trend_points * 0.7 + volume_points * 0.8 - gate_penalty, 1.0, 99.0), 1)
    prob_5 = round(_clamp_float((heuristic_prob_5 * 0.55) + (model_prob * 0.45), 1.0, 99.0), 1)
    prob_clean = round(_clamp_float((heuristic_prob_clean * 0.55) + (model_clean_prob * 0.45), 1.0, 99.0), 1)
    conviction_score = round(_clamp_float((decision_score + prob_clean) / 2.0, 1.0, 99.0), 1)
    theme_overlay = build_theme_overlay(
        sym=sym,
        stock_name=stock_name,
        market_type=market_key,
        intel_data=intel_data if isinstance(intel_data, dict) else {},
        market_gate=gate,
        df=df,
        current_price=close_now,
        volume_ratio=vol_ratio,
        decision_score=decision_score,
        scan_mode="INTRADAY",
    )
    theme_exception_active = bool(theme_overlay.get("exception_allowance", False)) and bool((market_gate or {}).get("theme_exception_allowance", False))
    decision_score = round(_clamp_float(decision_score + float(theme_overlay.get("score_adjustment", 0.0) or 0.0), 0.0, 100.0), 1)
    conviction_score = round(_clamp_float((decision_score + prob_clean) / 2.0, 1.0, 99.0), 1)
    provisional_trend = "UP" if close_now > ema_fast > ema_slow else ("SIDE" if close_now >= ema_slow else "DOWN")
    expected_edge = compute_expected_edge_profile(
        prob_5=float(prob_5),
        prob_clean=float(prob_clean),
        decision_score=float(decision_score),
        conviction_score=float(conviction_score),
        real_trend=provisional_trend,
        routing_path=str(theme_overlay.get("routing_path", "core_only") or "core_only"),
        scan_mode="INTRADAY",
        market_gate=gate,
        theme_context=theme_overlay.get("theme_context", {}),
    )

    weak_setup = decision_score < 60 or (not breakout and vol_ratio < 1.15 and intraday_ret < 0.4)
    theme_intraday_override = (
        theme_exception_active
        and float(decision_score) >= 56.0
        and float(conviction_score) >= 48.0
        and (bool(breakout) or float(vol_ratio) >= 1.1 or float(intraday_ret) >= 0.3)
    )
    if weak_setup and not theme_intraday_override:
        _reject(
            "INTRADAY_SETUP_WEAK",
            {
                "decision_score": decision_score,
                "breakout": bool(breakout),
                "vol_ratio": round(vol_ratio, 2),
                "intraday_ret": round(intraday_ret, 2),
                "day_ret": round(day_ret, 2),
                "ema_fast": round(ema_fast, 4),
                "ema_slow": round(ema_slow, 4),
            },
        )
        return None
    if theme_intraday_override:
        theme_overlay = _activate_theme_route(theme_overlay, "THEME_ROUTE_INTRADAY_OVERRIDE")

    position = _intraday_position_label(close_now, ema_fast, ema_slow, breakout)
    strategy_tag = "⏱️ Intraday Breakout" if breakout else "⏱️ Intraday Trend"
    if gate == "RED":
        strategy_tag = f"{strategy_tag} | Risk-On-Exception"
    if news_adj.get("is_beneficiary"):
        strategy_tag = f"{strategy_tag} | News Tailwind"
    elif news_adj.get("is_victim"):
        strategy_tag = f"{strategy_tag} | News Headwind"
    strategy_tag = f"{strategy_tag} | 1H"

    surge_tag = "⚡ High-Volume Breakout" if breakout and vol_ratio >= 1.8 else ("📈 Trend Continuation" if intraday_ret > 0 else "-")
    tier = "🏆T1" if decision_score >= 85 else ("⭐T2" if decision_score >= 72 else "⚡T3")
    tier_sort = 1 if decision_score >= 85 else (2 if decision_score >= 72 else 3)
    whale_score = int(_clamp_float(35.0 + vol_ratio * 20.0 + max(day_ret, 0.0) * 6.0, 0.0, 100.0))
    real_trend = provisional_trend

    entry_price = close_now
    target_price = close_now * (1.0 + target_pct / 100.0)
    stop_loss = close_now * (1.0 - stop_pct / 100.0)
    volume_badge = f"{'✅' if vol_ratio >= 1.5 else '⚠️'} x{vol_ratio:.1f}"
    news_tag = "🔥 수혜" if news_adj.get("is_beneficiary") else ("⚠️ 피해" if news_adj.get("is_victim") else "-")

    if is_us:
        res_data = {
            "Tier": tier,
            "_tier_sort": tier_sort,
            "Ticker": sym,
            "Name": stock_name,
            "Antigrav": int(alpha_score),
            "Whale": f"{whale_score}pts",
            "Trend": real_trend,
            "1D Change": f"{day_ret:+.2f}%",
            "Consecutive": "Intraday",
            "RS vs SPY": f"{intraday_ret:+.1f}% intraday",
            "Entry(-2%)": f"{entry_price:,.2f}",
            "Target": f"{target_price:,.2f}",
            "Stop": f"{stop_loss:,.2f} (-{stop_pct:.1f}%)",
            "Hold": "same-day",
            "Volume": volume_badge,
            "Strategy": strategy_tag,
            "Surge": surge_tag,
            "WR": "-",
            "AI Prob": f"{prob_5:.1f}%",
            "Clean Hit": f"{prob_clean:.1f}%",
            "Conviction": conviction_score,
            "Position": position,
            "Context": "🔥 Beneficiary" if news_adj.get("is_beneficiary") else ("⚠️ Impact" if news_adj.get("is_victim") else "-"),
            "_prob_5": prob_5,
            "_prob_clean": prob_clean,
            "Decision Score": decision_score,
            "Model Variant": ml_pred.get("phase25_variant", "-"),
            "phase25_variant": ml_pred.get("phase25_variant"),
            "phase25_prob": ml_pred.get("phase25_prob"),
            "phase25_shadow_variant": ml_pred.get("phase25_shadow_variant"),
            "phase25_shadow_prob": ml_pred.get("phase25_shadow_prob"),
            "phase25_recommended_threshold": ml_pred.get("phase25_recommended_threshold"),
            "model_trace_status": ml_pred.get("model_trace_status"),
            "model_error": ml_pred.get("model_error"),
            "expected_edge_score": expected_edge.get("expected_edge_score"),
            "expected_return_1d_pct": expected_edge.get("expected_return_1d_pct"),
            "expected_return_3d_pct": expected_edge.get("expected_return_3d_pct"),
            "_theme_context": theme_overlay.get("theme_context", {}),
            "_leader_metrics": theme_overlay.get("leader_metrics", {}),
            "_routing_path": theme_overlay.get("routing_path", "core_only"),
            "Theme": (theme_overlay.get("theme_context", {}) or {}).get("primary_theme", "-"),
            "scan_mode": "INTRADAY",
            "strategy_family": resolve_strategy_family("AMEX" if is_amex else "US", is_amex=is_amex),
        }
        db_payload = {
            "ticker": sym,
            "name": stock_name,
            "alpha_score": int(alpha_score),
            "tech_score": int(alpha_score),
            "ml_prob": prob_5,
            "whale_score": whale_score,
            "fund_status": "INTRADAY",
            "initial_trend": real_trend,
            "market_type": "AMEX" if is_amex else "US",
            "note": strategy_tag,
            "position": position,
            "tier": tier,
            "volume": volume_badge,
            "context": res_data["Context"],
            "surge": surge_tag,
            "win_rate": "-",
            "decision_score": decision_score,
            "strategy_family": resolve_strategy_family("AMEX" if is_amex else "US", is_amex=is_amex),
            "phase25_prob": ml_pred.get("phase25_prob"),
            "phase25_variant": ml_pred.get("phase25_variant"),
            "phase25_shadow_variant": ml_pred.get("phase25_shadow_variant"),
            "phase25_shadow_prob": ml_pred.get("phase25_shadow_prob"),
            "phase25_recommended_threshold": ml_pred.get("phase25_recommended_threshold"),
            "model_trace_status": ml_pred.get("model_trace_status"),
            "model_error": ml_pred.get("model_error"),
            "expected_edge_score": expected_edge.get("expected_edge_score"),
            "expected_return_1d_pct": expected_edge.get("expected_return_1d_pct"),
            "expected_return_3d_pct": expected_edge.get("expected_return_3d_pct"),
            **_theme_flat_fields(theme_overlay.get("theme_context", {})),
        }
    else:
        res_data = {
            "Tier": tier,
            "_tier_sort": tier_sort,
            "티커": sym,
            "종목명": stock_name,
            "Antigrav": int(alpha_score),
            "수급": f"{whale_score}점 장중",
            "추세": real_trend,
            "전일비": f"{day_ret:+.2f}%",
            "연속등락": "장중",
            "매수가(-2%)": f"{entry_price:,.0f}",
            "목표가(+3.5%)": f"{target_price:,.0f}",
            "손절가": f"{stop_loss:,.0f} (-{stop_pct:.1f}%)",
            "보유한도": "당일",
            "거래량": volume_badge,
            "시장맥락": news_tag,
            "전략": strategy_tag,
            "급등예측": surge_tag,
            "승률": "-",
            "AI확률": f"{prob_5:.1f}%",
            "정밀확률": f"{prob_clean:.1f}%",
            "확신도": conviction_score,
            "위치": position,
            "_prob_5": prob_5,
            "_prob_clean": prob_clean,
            "Decision Score": decision_score,
            "모델": ml_pred.get("phase25_variant", "-"),
            "phase25_variant": ml_pred.get("phase25_variant"),
            "phase25_prob": ml_pred.get("phase25_prob"),
            "phase25_shadow_variant": ml_pred.get("phase25_shadow_variant"),
            "phase25_shadow_prob": ml_pred.get("phase25_shadow_prob"),
            "phase25_recommended_threshold": ml_pred.get("phase25_recommended_threshold"),
            "model_trace_status": ml_pred.get("model_trace_status"),
            "model_error": ml_pred.get("model_error"),
            "expected_edge_score": expected_edge.get("expected_edge_score"),
            "expected_return_1d_pct": expected_edge.get("expected_return_1d_pct"),
            "expected_return_3d_pct": expected_edge.get("expected_return_3d_pct"),
            "_theme_context": theme_overlay.get("theme_context", {}),
            "_leader_metrics": theme_overlay.get("leader_metrics", {}),
            "_routing_path": theme_overlay.get("routing_path", "core_only"),
            "테마": (theme_overlay.get("theme_context", {}) or {}).get("primary_theme", "-"),
            "scan_mode": "INTRADAY",
            "strategy_family": resolve_strategy_family("KR"),
        }
        db_payload = {
            "ticker": sym,
            "name": stock_name,
            "alpha_score": int(alpha_score),
            "tech_score": int(alpha_score),
            "ml_prob": prob_5,
            "whale_score": whale_score,
            "fund_status": "INTRADAY",
            "initial_trend": real_trend,
            "market_type": "KR",
            "note": strategy_tag,
            "position": position,
            "tier": tier,
            "volume": volume_badge,
            "context": news_tag,
            "surge": surge_tag,
            "win_rate": "-",
            "decision_score": decision_score,
            "strategy_family": resolve_strategy_family("KR"),
            "phase25_prob": ml_pred.get("phase25_prob"),
            "phase25_variant": ml_pred.get("phase25_variant"),
            "phase25_shadow_variant": ml_pred.get("phase25_shadow_variant"),
            "phase25_shadow_prob": ml_pred.get("phase25_shadow_prob"),
            "phase25_recommended_threshold": ml_pred.get("phase25_recommended_threshold"),
            "model_trace_status": ml_pred.get("model_trace_status"),
            "model_error": ml_pred.get("model_error"),
            "expected_edge_score": expected_edge.get("expected_edge_score"),
            "expected_return_1d_pct": expected_edge.get("expected_return_1d_pct"),
            "expected_return_3d_pct": expected_edge.get("expected_return_3d_pct"),
            "theme_context": theme_overlay.get("theme_context", {}),
            "leader_metrics": theme_overlay.get("leader_metrics", {}),
            "routing_path": theme_overlay.get("routing_path", "core_only"),
            "theme_score_adjustment": round(float(theme_overlay.get("score_adjustment", 0.0) or 0.0), 2),
            **_theme_flat_fields(theme_overlay.get("theme_context", {})),
        }

    db_payload["scan_mode"] = "INTRADAY"
    db_payload["entry_price"] = round(entry_price, 6)
    db_payload["target_price"] = round(target_price, 6)
    db_payload["stop_loss"] = round(stop_loss, 6)
    db_payload["r_status"] = str(r_status)
    return {"res_data": res_data, "db_payload": db_payload}


def normalize_uploaded_ticker(symbol: str) -> str:
    """Normalize user-uploaded ticker symbol with a conservative KR fallback."""
    sym = str(symbol).strip()
    if not sym:
        return sym
    if not sym.isalpha() and not sym.endswith(".KS") and not sym.endswith(".KQ"):
        return f"{sym}.KS"
    return sym


def evaluate_universe_candidate(
    ticker: str,
    name: str,
    market_code: str = "US",
    is_top_100: bool = False,
) -> Optional[Dict[str, Any]]:
    """Evaluate legacy universe-scan candidate using existing QuantStrategy logic.

    Returns:
      {
        "candidate_data": {...},
        "is_active": bool,
      }
    or None when excluded / failed.
    """

    try:
        qs = quant_analysis.QuantStrategy(ticker)
        if not qs.fetch_data(period="1y", interval="1d"):
            return None
        qs.calculate_indicators()
        if qs.df is None or qs.df.empty:
            return None

        fund_pass, _fund_reason = qs.check_fundamentals()
        ml_pred = qs.get_ml_prediction()
        ml_prob = ml_pred.get("prob", 50)

        whale_data = qs.get_investor_flows()
        whale_score = whale_data.get("whale_score", 0)

        macro = qs.get_macro_metrics()
        r_status = macro.get("status", "NEUTRAL") if macro else "NEUTRAL"

        alpha_score = qs.calculate_alpha_score_v30(
            win_rate=0,
            profit_factor=0,
            ai_return=0,
            whale_score=whale_score,
            macro_status=r_status,
        )

        surge_data = qs.detect_pre_surge_signals()
        is_pre_surge = surge_data.get("is_pre_surge", False)
        surge_type = surge_data.get("type")

        position = qs.get_price_position()

        strategy_tag = surge_type
        is_active = False

        if fund_pass and alpha_score >= 60 and ml_prob >= 55 and whale_score >= 50:
            is_active = True
            strategy_tag = "🚀 Momentum"

        if is_pre_surge or surge_data.get("strategy_type") == "REVERSAL":
            if ml_prob >= 50:
                is_active = True
                strategy_tag = f"🎣 {surge_data.get('type')}"

        if not (is_top_100 or is_active):
            return None

        candidate_data = {
            "ticker": ticker,
            "name": name,
            "is_top_100": is_top_100,
            "is_sniper": is_active,
            "alpha_score": alpha_score,
            "ml_prob": round(ml_prob, 1),
            "whale_score": whale_score,
            "fund_status": "Pass" if fund_pass else "Fail",
            "market_type": market_code,
            "note": strategy_tag,
            "position": position,
        }
        return {"candidate_data": candidate_data, "is_active": is_active}
    except Exception:
        return None


def evaluate_uploaded_candidate(
    ticker: str,
    display_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Evaluate one uploaded ticker for app custom scan flow."""
    try:
        qs = quant_analysis.QuantStrategy(ticker)
        if not qs.fetch_data(period="1y"):
            return None
        qs.calculate_indicators()
        if qs.df is None or qs.df.empty:
            return None

        fund_pass, _ = qs.check_fundamentals()
        ml_pred = qs.get_ml_prediction()
        whale_data = qs.get_investor_flows()

        ml_prob = ml_pred.get("prob", 50)
        whale_score = whale_data.get("whale_score", 0)
        tech_score = qs.df["Antigrav_Score"].iloc[-1] if "Antigrav_Score" in qs.df.columns else 0
        alpha_score = qs.calculate_antigravity_score(
            0,
            0,
            0,
            whale_score=whale_score,
            macro_status="NEUTRAL",
        )
        if alpha_score is None:
            return None

        row = {
            "티커": ticker,
            "AI확률": f"{float(ml_prob):.1f}%",
            "세력점수": f"{int(whale_score)}점",
            "Antigrav": alpha_score,
            "날짜": qs.df.index[-1].strftime("%Y-%m-%d"),
        }
        db_payload = {
            "ticker": ticker,
            "name": display_name or ticker,
            "alpha_score": int(alpha_score),
            "tech_score": int(tech_score),
            "ml_prob": round(float(ml_prob), 1),
            "whale_score": int(whale_score),
            "fund_status": "Pass" if fund_pass else "Fail",
            "initial_trend": "UP" if float(ml_prob) > 50 else "DOWN",
            "market_type": "CUSTOM",
        }
        return {"ui_row": row, "db_payload": db_payload}
    except Exception:
        return None


def evaluate_active_signal_candidate(
    ticker: str,
    stock_name: str,
    regime_status: str,
) -> Optional[Dict[str, Any]]:
    """Evaluate one active-watchlist ticker for hourly bot signal path."""
    try:
        qs = quant_analysis.QuantStrategy(ticker)
        if not qs.fetch_data(period="1y"):
            return None

        qs.calculate_indicators()
        qs.check_signals()
        if qs.df is None or qs.df.empty:
            return None

        latest = qs.df.iloc[-1]
        if float(latest.get("Signal", 0) or 0) != 1:
            return None

        if regime_status == "CRASH":
            return {"skip_reason": "MARKET_CRASH"}

        stats = qs.backtest()
        forecast = qs.predict_future(days=30)
        macro = qs.get_macro_metrics()
        r_status = macro.get("status", "NEUTRAL") if macro else "NEUTRAL"

        prophet_ret = 0.0
        if forecast is not None and "forecast" in forecast:
            curr = float(latest["Close"])
            fc_df = forecast["forecast"]
            pred = fc_df["yhat"].iloc[-1] if "yhat" in fc_df.columns else curr
            if curr > 0:
                prophet_ret = ((pred - curr) / curr) * 100

        wr = float(stats.get("Win Rate", "0").strip("%")) / 100.0
        pf = float(stats.get("Profit Factor", "0"))

        whale_data = qs.get_investor_flows()
        whale_score = whale_data.get("whale_score", 0)
        score = qs.calculate_alpha_score_v30(
            wr,
            pf,
            prophet_ret,
            whale_score=whale_score,
            macro_status=r_status,
        )

        fund_note = "Skipped"
        signal_type = "BUY"
        if score >= 70:
            fund_ok, fund_note = qs.check_fundamentals()
            if not fund_ok:
                score -= 30
                signal_type = "RISKY"

        if regime_status == "BULL":
            signal_type = "STRONG BUY" if score >= 80 else "BUY"
        elif regime_status == "BEAR":
            signal_type = "SCALPING ONLY"

        signal_emoji = "🚨" if score >= 70 else "👀"
        signal_title = f"{signal_type} ({regime_status})"
        kelly_pct = stats.get("Kelly Allocation", "0%")
        setup = qs.get_trade_setup()
        profile_overlay = resolve_ticker_profile_overlay(
            ticker=ticker,
            market_type="KR" if ".K" in ticker.upper() else "US",
            market_gate=regime_status,
            setup=setup,
        )
        setup = profile_overlay["setup"]
        score = float(score) + float(profile_overlay["overlay"].get("score_adjustment", 0.0) or 0.0)
        entry_price = float(setup.get("Entry Price", 0) or 0)
        target_price = float(setup.get("Target Price", 0) or 0)
        stop_loss = float(setup.get("Stop Loss", 0) or 0)

        currency = "$" if ticker.upper().isupper() and ".K" not in ticker else "₩"
        signal_data = {
            "score": score,
            "emoji": signal_emoji,
            "title": signal_title,
            "stock_name": stock_name,
            "ticker": ticker,
            "price": float(latest["Close"]),
            "currency": currency,
            "forecast": prophet_ret,
            "regime": regime_status,
            "entry": entry_price,
            "target": target_price,
            "stop_loss": stop_loss,
            "kelly": kelly_pct,
            "fund_note": fund_note,
            "profile_policy": profile_overlay["overlay"].get("policy"),
            "profile_regime": profile_overlay.get("regime"),
        }
        save_signal_payload = {
            "ticker": ticker,
            "stock_name": stock_name,
            "price": float(latest["Close"]),
            "alpha_score": score,
            "ai_prediction": prophet_ret,
            "signal_type": signal_type,
            "entry_price": entry_price,
            "target_price": target_price,
            "stop_loss": stop_loss,
            "profile_policy": profile_overlay["overlay"].get("policy"),
        }
        log_line = f"{signal_emoji} {signal_type}: {ticker} ({stock_name}) (Score: {score}) | Fund: {fund_note}"
        return {
            "signal_data": signal_data,
            "save_signal_payload": save_signal_payload,
            "log_line": log_line,
        }
    except Exception:
        return None


def compute_exhaustion_context(df: Any, is_us: bool) -> Optional[Dict[str, Any]]:
    """Compute short-term momentum/exhaustion metrics used in app scanner."""
    try:
        import numpy as np
        import pandas as pd

        if df is None or len(df) < 20:
            return None

        closes = df["Close"]
        vols = df["Volume"]
        curr_c = float(closes.iloc[-1])
        curr_vol = float(vols.iloc[-1])

        prev_pct_change = 0.0
        if len(df) >= 2:
            prev_c = float(closes.iloc[-2])
            if prev_c > 0:
                prev_pct_change = (curr_c - prev_c) / prev_c * 100

        consec_days = 0
        if len(df) >= 2:
            deltas = closes.diff().dropna()
            if len(deltas) > 0:
                last_sign = np.sign(deltas.iloc[-1])
                if last_sign != 0:
                    for val in reversed(deltas.tolist()):
                        if np.sign(val) == last_sign:
                            consec_days += int(last_sign)
                        else:
                            break

        bb_mid = closes.rolling(window=20).mean().iloc[-1]
        bb_std = closes.rolling(window=20).std().iloc[-1]
        bb_width = ((bb_mid + bb_std * 2) - (bb_mid - bb_std * 2)) / bb_mid * 100 if bb_mid > 0 else 0

        past_c = float(closes.iloc[-10]) if len(df) >= 10 else curr_c
        trend_10d = (curr_c - past_c) / past_c * 100 if past_c > 0 else 0

        vol_ma20 = vols.rolling(20).mean().iloc[-1]
        avg_vol_20 = float(vol_ma20) if pd.notna(vol_ma20) else curr_vol
        vol_ratio_today = curr_vol / max(1, avg_vol_20)

        is_exhausted = (bb_width >= 48) or (trend_10d >= 18) or (vol_ratio_today >= 2.5)
        exhaustion_tag = "⚡ Momentum" if is_us else "⚡ 단기과열(강세)"
        turnover = curr_c * avg_vol_20

        return {
            "curr_price": curr_c,
            "curr_volume": curr_vol,
            "avg_vol_20": avg_vol_20,
            "turnover": turnover,
            "prev_pct_change": prev_pct_change,
            "consec_days": consec_days,
            "is_exhausted": is_exhausted,
            "exhaustion_tag": exhaustion_tag,
        }
    except Exception:
        return None


def resolve_liquidity_gate(is_us: bool, ticker: str | None = None) -> Dict[str, Any]:
    """Return market-aware liquidity thresholds."""
    def _env_float(name: str, default: float) -> float:
        try:
            return float(os.getenv(name, str(default)))
        except Exception:
            return float(default)

    if is_us:
        us_min_price = _env_float("AG_US_MIN_PRICE", 1.0)
        us_min_turnover = _env_float("AG_US_MIN_TURNOVER", 1_000_000)
        return {
            "market": "US",
            "min_price": float(us_min_price),
            "min_turnover": float(us_min_turnover),
        }

    market = resolve_profile_market(market_type="KR", ticker=ticker)
    kr_min_price = _env_float("AG_KR_MIN_PRICE", 1000.0)
    kospi_min_turnover = _env_float("AG_KOSPI_MIN_TURNOVER", 10_000_000_000)
    kosdaq_min_turnover = _env_float("AG_KOSDAQ_MIN_TURNOVER", 7_000_000_000)
    min_turnover = kosdaq_min_turnover if market == "KOSDAQ" else kospi_min_turnover
    return {
        "market": market,
        "min_price": float(kr_min_price),
        "min_turnover": float(min_turnover),
    }


def passes_liquidity_filter(
    curr_price: float,
    turnover: float,
    is_us: bool,
    ticker: str | None = None,
) -> bool:
    """Liquidity filter with market-aware KR thresholds."""
    gate = resolve_liquidity_gate(is_us=is_us, ticker=ticker)
    return curr_price >= float(gate.get("min_price", 0.0)) and turnover >= float(gate.get("min_turnover", 0.0))


def compute_surge_tag_data(df: Any, ml_pred: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
    """Compute legacy surge tag and probability fields without changing thresholds."""
    result = {"surge_tag": "-", "prob_3": 0.0, "prob_5": 0.0, "prob_10": 0.0, "prob_clean": 0.0}
    try:
        import numpy as np
        import pandas as pd

        _close = df["Close"]
        _vol = df["Volume"]
        _c = _close.values.astype(float)
        _v = _vol.values.astype(float)

        # Keep legacy feature calculations for behavior parity / future instrumentation.
        _ma5 = float(np.mean(_c[-5:])) if len(_c) >= 5 else _c[-1]
        _ma10 = float(np.mean(_c[-10:])) if len(_c) >= 10 else _c[-1]
        _ma20 = float(np.mean(_c[-20:])) if len(_c) >= 20 else _c[-1]
        _curr = float(_c[-1])
        _ma_aligned = _curr > _ma5 > _ma10 > _ma20
        _trend10 = (_curr - float(_c[-11])) / float(_c[-11]) * 100 if len(_c) >= 11 and float(_c[-11]) > 0 else 0
        _bb_mid = _ma20
        _bb_std = float(np.std(_c[-20:])) if len(_c) >= 20 else 0
        _bb_u = _bb_mid + 2 * _bb_std
        _bb_l = _bb_mid - 2 * _bb_std
        _bb_pos = (_curr - _bb_l) / (_bb_u - _bb_l) if (_bb_u - _bb_l) > 0 else 0.5
        _close_s = pd.Series(_c)
        _ema12 = float(_close_s.ewm(span=12).mean().iloc[-1])
        _ema26 = float(_close_s.ewm(span=26).mean().iloc[-1])
        _macd = _ema12 - _ema26
        _sig = float(_close_s.ewm(span=12).mean().diff().ewm(span=9).mean().iloc[-1])
        _macd_hist = _macd - _sig
        _avg_vol = float(np.mean(_v[-20:])) if len(_v) >= 20 else float(_v[-1])
        _vol_r = float(_v[-1]) / max(_avg_vol, 1)
        _ = (_ma_aligned, _trend10, _bb_pos, _macd_hist, _vol_r)

        source = ml_pred or {}
        blended_prob = float(source.get("prob", source.get("raw_prob", 50.0)) or 50.0)
        raw_prob_5 = float(source.get("5pct", blended_prob) or blended_prob)
        result["prob_3"] = float(source.get("3pct", blended_prob) or blended_prob)
        result["prob_5"] = float(blended_prob)
        result["prob_10"] = float(source.get("10pct", 0.0) or 0.0)
        result["prob_clean"] = float(source.get("5pct_clean", source.get("clean_prob", result["prob_5"])) or result["prob_5"])
        result["prob_5_raw"] = float(raw_prob_5)

        if result["prob_clean"] >= 60.0:
            result["surge_tag"] = f"💎 무결점 {result['prob_clean']}%"
        elif result["prob_10"] >= 60.0:
            result["surge_tag"] = f"🚀 +10% (P={result['prob_10']}%)"
        elif result["prob_5"] >= 60.0:
            result["surge_tag"] = f"⬆️ +5% (P={result['prob_5']}%)"
        elif result["prob_3"] >= 60.0:
            result["surge_tag"] = f"📈 +3% (P={result['prob_3']}%)"
        return result
    except Exception:
        return result


def resolve_precision_gate_profile() -> Dict[str, float]:
    """Scanner precision profile prioritizing hit rate over candidate count."""
    def _env_float(name: str, default: float) -> float:
        try:
            return float(os.getenv(name, str(default)))
        except Exception:
            return float(default)

    enabled = str(os.getenv("AG_ENABLE_PRECISION_GATE", "1")).strip().lower() not in {"0", "false", "off", "no"}
    return {
        "enabled": 1.0 if enabled else 0.0,
        "green_min_conviction": _env_float("AG_GREEN_MIN_CONVICTION", 57.0),
        "yellow_min_conviction": _env_float("AG_YELLOW_MIN_CONVICTION", 62.0),
        "red_min_conviction": _env_float("AG_RED_MIN_CONVICTION", 70.0),
        "kosdaq_red_min_conviction": _env_float("AG_KOSDAQ_RED_MIN_CONVICTION", 64.0),
        "kosdaq_red_alpha_relax_floor": _env_float("AG_KOSDAQ_RED_ALPHA_RELAX_FLOOR", 45.0),
        "amex_red_min_conviction": _env_float("AG_AMEX_RED_MIN_CONVICTION", 56.0),
        "min_prob": _env_float("AG_SCAN_MIN_PROB", 52.0),
        "min_clean_prob": _env_float("AG_SCAN_MIN_CLEAN_PROB", 50.0),
        "amex_min_prob": _env_float("AG_AMEX_SCAN_MIN_PROB", 42.0),
        "amex_min_clean_prob": _env_float("AG_AMEX_SCAN_MIN_CLEAN_PROB", 38.0),
    }


def compute_conviction_score(
    alpha_score: float,
    whale_score: float,
    prob_5: float,
    prob_clean: float,
    wr: float,
    pf: float,
    real_trend: str,
    position: str,
    market_gate: str,
    strategy_type: str,
) -> float:
    """Auditable blend of rule, ML, and trade-quality signals."""
    pf_score = max(0.0, min(100.0, float(pf) * 25.0))
    trend_bonus = 5.0 if str(real_trend) == "UP" else -8.0
    if "Rising" in str(position):
        trend_bonus += 4.0
    elif "Resting" in str(position):
        trend_bonus += 1.5
    elif "Peak" in str(position):
        trend_bonus -= 2.0

    gate_bonus = {"GREEN": 4.0, "YELLOW": -2.0, "RED": -8.0}.get(str(market_gate), 0.0)
    strategy_bonus = 4.0 if str(strategy_type) in {"PRE_SURGE", "REVERSAL"} else 1.5

    score = (
        float(alpha_score) * 0.38
        + float(whale_score) * 0.18
        + float(prob_5) * 0.18
        + float(prob_clean) * 0.12
        + float(wr) * 0.08
        + pf_score * 0.06
        + trend_bonus
        + gate_bonus
        + strategy_bonus
    )
    return round(max(0.0, min(100.0, score)), 1)


def compute_score_edge_adjustment(
    *,
    prob_5: float,
    alpha_score: float,
    whale_score: float,
    position: str,
    strategy_tag: str,
    volume_ratio: float,
) -> Dict[str, Any]:
    """Apply small, auditable score edges backed by recent realized scan outcomes."""
    is_peak = "Peak" in str(position)
    is_rising = "Rising" in str(position)
    is_overheat = any(tag in str(strategy_tag) for tag in ["과열", "Overheat", "Exhaustion"])
    is_rsidiv = "RSI_DIV" in str(strategy_tag)
    is_obvdiv = "OBV_DIV" in str(strategy_tag)

    adjustment = 0.0
    reasons: list[str] = []

    if is_peak and is_overheat and float(prob_5) >= 30.0:
        adjustment += 20.0
        reasons.append("EDGE_PEAK_OVERHEAT_MODEL_CONFIRM")
    elif is_peak and is_overheat:
        adjustment += 10.0
        reasons.append("EDGE_PEAK_OVERHEAT")

    if float(volume_ratio) >= 2.5 and is_overheat:
        adjustment += 5.0
        reasons.append("EDGE_VOLUME_EXPANSION")

    if float(alpha_score) >= 75.0 and float(whale_score) >= 65.0 and float(volume_ratio) >= 2.5:
        adjustment += 4.0
        reasons.append("EDGE_ALPHA_WHALE_BREAKOUT")

    if is_rsidiv:
        adjustment -= 10.0
        reasons.append("EDGE_RSI_DIV_PENALTY")
    elif is_obvdiv and not is_overheat:
        adjustment -= 5.0
        reasons.append("EDGE_OBV_DIV_PENALTY")

    if is_rising and not is_overheat and float(volume_ratio) <= 1.8:
        adjustment -= 8.0
        reasons.append("EDGE_RISING_NO_EXPANSION")

    if is_rising and float(prob_5) < 25.0:
        adjustment -= 3.0
        reasons.append("EDGE_LOW_MODEL_SUPPORT")

    return {
        "adjustment": round(adjustment, 1),
        "reasons": reasons,
    }


def compute_kr_context_adjustment(
    *,
    intel_data: Optional[Dict[str, Any]],
    news_adj: Optional[Dict[str, Any]],
    theme_overlay: Optional[Dict[str, Any]],
    leader_signal: Optional[Dict[str, Any]],
    market_gate: str,
    real_trend: str,
) -> Dict[str, Any]:
    """Blend macro/news/theme context into an auditable KR ranking premium."""
    intel = intel_data if isinstance(intel_data, dict) else {}
    news = news_adj if isinstance(news_adj, dict) else {}
    overlay = theme_overlay if isinstance(theme_overlay, dict) else {}
    theme_context = overlay.get("theme_context", {}) if isinstance(overlay.get("theme_context"), dict) else {}
    leader = leader_signal if isinstance(leader_signal, dict) else {}

    adjustment = 0.0
    reasons: list[str] = []

    sentiment = str(intel.get("market_sentiment") or "NEUTRAL").upper()
    sentiment_score = _safe_numeric(intel.get("sentiment_score"), 0.0)
    market_gate_upper = str(market_gate or "GREEN").upper()
    real_trend_upper = str(real_trend or "").upper()
    theme_direction = str(theme_context.get("theme_direction") or "NEUTRAL").upper()
    theme_strength = _safe_numeric(theme_context.get("theme_strength_score"), 0.0)
    routing_path = str(overlay.get("routing_path") or "core_only").lower()
    leader_score = _safe_numeric(leader.get("leader_score"), 0.0)
    flow_consensus = bool(leader.get("flow_consensus_buying", False))
    retail_dominant = bool(leader.get("retail_dominant", False))

    if sentiment == "BULLISH":
        bonus = min(5.0, max(1.5, sentiment_score / 22.0))
        adjustment += bonus
        reasons.append("MACRO_BULLISH")
    elif sentiment == "BEARISH":
        penalty = min(6.5, max(2.0, abs(sentiment_score) / 18.0))
        adjustment -= penalty
        reasons.append("MACRO_BEARISH")
    elif sentiment == "MIXED":
        adjustment -= 0.8
        reasons.append("MACRO_MIXED")

    if bool(news.get("is_beneficiary")):
        adjustment += 4.0
        reasons.append("NEWS_BENEFICIARY")
    elif bool(news.get("is_victim")):
        adjustment -= 5.0
        reasons.append("NEWS_HEADWIND")

    if theme_direction == "BENEFICIARY":
        bonus = min(4.5, 1.5 + theme_strength / 22.0)
        adjustment += bonus
        reasons.append("THEME_BENEFICIARY")
    elif theme_direction == "HEADWIND":
        penalty = min(5.5, 1.5 + theme_strength / 18.0)
        adjustment -= penalty
        reasons.append("THEME_HEADWIND")

    if routing_path == "theme_routed":
        adjustment += 2.0
        reasons.append("THEME_ROUTED")
    elif routing_path == "theme_shadow":
        adjustment += 0.6
        reasons.append("THEME_SHADOW")

    if leader_score >= 78.0 and flow_consensus:
        adjustment += 3.5
        reasons.append("FLOW_LEADER_CONSENSUS")
    elif leader_score >= 70.0:
        adjustment += 1.8
        reasons.append("FLOW_LEADER")

    if retail_dominant:
        adjustment -= 3.5
        reasons.append("RETAIL_DOMINANT")

    if market_gate_upper == "RED" and sentiment != "BULLISH":
        adjustment -= 2.5
        reasons.append("RED_GATE_RISK")
    elif market_gate_upper == "GREEN" and sentiment == "BULLISH" and real_trend_upper == "UP":
        adjustment += 1.5
        reasons.append("GREEN_GATE_TREND")

    if real_trend_upper == "DOWN" and bool(news.get("is_victim")):
        adjustment -= 2.0
        reasons.append("DOWN_TREND_HEADWIND")

    return {
        "adjustment": round(_clamp_float(adjustment, -12.0, 12.0), 1),
        "reasons": reasons[:8],
        "market_sentiment": sentiment,
        "sentiment_score": round(float(sentiment_score), 1),
        "theme_direction": theme_direction,
        "theme_strength_score": round(float(theme_strength), 1),
    }


def resolve_ticker_profile_overlay(
    *,
    ticker: str,
    market_type: str,
    market_gate: str,
    setup: Dict[str, Any],
) -> Dict[str, Any]:
    profile = get_ticker_profile(
        ticker=ticker,
        market_type=market_type,
        market_gate=market_gate,
    )
    overlay = compute_profile_adjustment(profile)
    updated_setup = apply_profile_to_setup(setup, profile)
    return {
        "profile": profile,
        "overlay": overlay,
        "setup": updated_setup,
        "regime": resolve_profile_regime(market_gate),
    }


def profile_supports_hard_filter_override(profile_overlay: Dict[str, Any]) -> bool:
    profile = (profile_overlay or {}).get("profile") or {}
    overlay = (profile_overlay or {}).get("overlay") or {}
    if not profile:
        return False
    if str(overlay.get("policy")) != "POSITIVE":
        return False
    return (
        int(profile.get("signals", 0) or 0) >= 5
        and float(profile.get("win_5d_pct", 0.0) or 0.0) >= 70.0
        and float(profile.get("avg_5d_pct", 0.0) or 0.0) >= 10.0
    )


def evaluate_precision_gate(
    *,
    conviction_score: float,
    prob_5: float,
    prob_clean: float,
    real_trend: str,
    market_gate: str,
    tier_sort: int,
    market_type: str | None = None,
    ticker: str | None = None,
    alpha_score: float = 0.0,
) -> Dict[str, Any]:
    cfg = resolve_precision_gate_profile()
    if not bool(cfg.get("enabled", 1.0)):
        return {"hard_reject": False, "penalty": 0.0, "reason": None, "min_conviction": 0.0}

    gate = str(market_gate or "GREEN")
    min_conviction = float(cfg.get(f"{gate.lower()}_min_conviction", cfg["green_min_conviction"]))
    market = resolve_profile_market(market_type=market_type, ticker=ticker)
    if (
        market == "KOSDAQ"
        and gate == "RED"
        and float(alpha_score) >= float(cfg.get("kosdaq_red_alpha_relax_floor", 45.0))
    ):
        min_conviction = min(min_conviction, float(cfg.get("kosdaq_red_min_conviction", 64.0)))
    if market == "AMEX":
        min_conviction = min(min_conviction, float(cfg.get("amex_red_min_conviction", 56.0 if gate == "RED" else 54.0)))
    min_prob = float(cfg.get("min_prob", 52.0))
    min_clean = float(cfg.get("min_clean_prob", 50.0))
    if market == "AMEX":
        min_prob = min(min_prob, float(cfg.get("amex_min_prob", 42.0)))
        min_clean = min(min_clean, float(cfg.get("amex_min_clean_prob", 38.0)))

    hard_reject = False
    penalty = 0.0
    reason = None

    if gate == "RED" and conviction_score < min_conviction and int(tier_sort) > 1:
        hard_reject = True
        reason = "PRECISION_GATE_RED_MARKET"
    elif int(tier_sort) >= 3 and float(prob_5) < min_prob and float(prob_clean) < max(min_clean - 10.0, 35.0):
        hard_reject = True
        reason = "PRECISION_GATE_T3_LOW_ML_SUPPORT"
    elif str(real_trend) != "UP" and conviction_score < max(min_conviction, 55.0 if market == "AMEX" else 60.0):
        hard_reject = True
        reason = "PRECISION_GATE_TREND_MISMATCH"
    elif float(prob_5) < min_prob and float(prob_clean) < min_clean and conviction_score < (min_conviction + 3.0):
        hard_reject = True
        reason = "PRECISION_GATE_LOW_MODEL_SUPPORT"
    elif conviction_score < min_conviction:
        penalty = round(min(12.0, (min_conviction - conviction_score) * 0.7), 1)
        reason = "PRECISION_GATE_SOFT_PENALTY"

    return {
        "hard_reject": hard_reject,
        "penalty": penalty,
        "reason": reason,
        "min_conviction": round(min_conviction, 1),
    }


def parse_wr_pf(stats: Dict[str, Any]) -> Dict[str, float]:
    """Safe parser for backtest win-rate/profit-factor."""
    try:
        wr = float(str(stats.get("Win Rate", "0")).strip("%"))
    except Exception:
        wr = 0.0
    try:
        pf = float(stats.get("Profit Factor", "0"))
    except Exception:
        pf = 0.0
    return {"wr": wr, "pf": pf}


def resolve_us_signal_window_gate() -> Dict[str, int]:
    """Resolve US signal-window gate from env with safe defaults.

    Env:
      - AG_US_SIGNAL_LOOKBACK (default: 10, range: 1..60)
      - AG_US_SIGNAL_MIN_HITS (default: 1, range: 0..10)
    """
    try:
        lookback = int(os.getenv("AG_US_SIGNAL_LOOKBACK", "10"))
    except Exception:
        lookback = 10
    try:
        min_hits = int(os.getenv("AG_US_SIGNAL_MIN_HITS", "1"))
    except Exception:
        min_hits = 1

    lookback = max(1, min(60, lookback))
    min_hits = max(0, min(10, min_hits))
    return {"lookback": lookback, "min_hits": min_hits}


def resolve_amex_moonshot_gate() -> Dict[str, float]:
    """Dedicated AMEX moonshot thresholds for >20/>50/>100 style runners."""
    return {
        "min_price": _env_float("AG_AMEX_MOONSHOT_MIN_PRICE", 0.7),
        "preferred_max_price": _env_float("AG_AMEX_MOONSHOT_PREFERRED_MAX_PRICE", 7.0),
        "max_price": _env_float("AG_AMEX_MOONSHOT_MAX_PRICE", 25.0),
        "min_alpha": _env_float("AG_AMEX_MOONSHOT_MIN_ALPHA", 28.0),
        "min_alpha_down": _env_float("AG_AMEX_MOONSHOT_MIN_ALPHA_DOWN", 40.0),
        "min_volume_ratio": _env_float("AG_AMEX_MOONSHOT_MIN_VOLUME_RATIO", 1.8),
        "min_day_change": _env_float("AG_AMEX_MOONSHOT_MIN_DAY_CHANGE", 4.0),
        "min_range_pct": _env_float("AG_AMEX_MOONSHOT_MIN_RANGE_PCT", 6.0),
        "min_rs": _env_float("AG_AMEX_MOONSHOT_MIN_RS", -12.0),
        "breakout_lookback": _env_float("AG_AMEX_MOONSHOT_BREAKOUT_LOOKBACK", 20.0),
        "max_close_to_high_pct": _env_float("AG_AMEX_MOONSHOT_MAX_CLOSE_TO_HIGH_PCT", 2.5),
        "signal_lookback": _env_float("AG_AMEX_MOONSHOT_SIGNAL_LOOKBACK", 20.0),
        "signal_min_hits": _env_float("AG_AMEX_MOONSHOT_SIGNAL_MIN_HITS", 0.0),
        "min_moonshot_score": _env_float("AG_AMEX_MOONSHOT_MIN_SCORE", 62.0),
        "market_policy_override_score": _env_float("AG_AMEX_MOONSHOT_POLICY_OVERRIDE_SCORE", 78.0),
        "sub7_bonus": _env_float("AG_AMEX_MOONSHOT_SUB7_BONUS", 10.0),
        "sub7_breakout_bonus": _env_float("AG_AMEX_MOONSHOT_SUB7_BREAKOUT_BONUS", 8.0),
    }


def resolve_us_hard_filter_gate() -> Dict[str, float]:
    """Resolve US hard-filter thresholds from env with legacy defaults.

    Env:
      - AG_US_HARD_MIN_ALPHA (default: 40)
      - AG_US_HARD_MIN_ALPHA_DOWN (default: 55)
      - AG_US_HARD_AMEX_RS_MIN (default: -5)
    """
    try:
        min_alpha = float(os.getenv("AG_US_HARD_MIN_ALPHA", "40"))
    except Exception:
        min_alpha = 40.0
    try:
        min_alpha_down = float(os.getenv("AG_US_HARD_MIN_ALPHA_DOWN", "55"))
    except Exception:
        min_alpha_down = 55.0
    try:
        amex_rs_min = float(os.getenv("AG_US_HARD_AMEX_RS_MIN", "-5"))
    except Exception:
        amex_rs_min = -5.0

    min_alpha = max(0.0, min(100.0, min_alpha))
    min_alpha_down = max(0.0, min(100.0, min_alpha_down))
    amex_rs_min = max(-50.0, min(50.0, amex_rs_min))
    return {
        "min_alpha": float(min_alpha),
        "min_alpha_down": float(min_alpha_down),
        "amex_rs_min": float(amex_rs_min),
    }


def compute_amex_moonshot_features(
    *,
    df: Any,
    prev_pct_change: float,
    rs_vs_spy: float,
    surge_data: Dict[str, Any],
) -> Dict[str, Any]:
    close_now = _safe_last(df["Close"], 0.0)
    open_now = _safe_last(df["Open"], close_now)
    high_now = _safe_last(df["High"], close_now)
    low_now = _safe_last(df["Low"], close_now)
    volume_now = _safe_last(df["Volume"], 0.0)
    volume_ma20 = _safe_last(df["Volume"].rolling(20, min_periods=5).mean(), max(volume_now, 1.0))
    volume_ratio = volume_now / max(volume_ma20, 1.0)
    range_pct = ((high_now - low_now) / max(close_now, 0.0001)) * 100.0 if close_now > 0 else 0.0
    prev_close = _safe_last(df["Close"].shift(1), close_now)
    gap_pct = ((open_now / prev_close) - 1.0) * 100.0 if prev_close > 0 else 0.0
    prior_high_10 = _safe_last(df["High"].shift(1).rolling(10, min_periods=5).max(), high_now)
    prior_high_20 = _safe_last(df["High"].shift(1).rolling(20, min_periods=10).max(), high_now)
    breakout_10d = bool(close_now >= prior_high_10 * 0.995) if prior_high_10 > 0 else False
    breakout_20d = bool(close_now >= prior_high_20 * 0.995) if prior_high_20 > 0 else False
    close_to_high_pct = ((high_now - close_now) / max(close_now, 0.0001)) * 100.0 if close_now > 0 else 99.0
    strategy_type = str(surge_data.get("strategy_type", "WAIT") or "WAIT").upper()
    is_pre_surge = bool(surge_data.get("is_pre_surge", False))
    preferred_max_price = float(resolve_amex_moonshot_gate().get("preferred_max_price", 7.0))
    is_sub7 = close_now <= preferred_max_price if close_now > 0 else False
    score = 20.0
    if breakout_20d:
        score += 20.0
    elif breakout_10d:
        score += 12.0
    score += min(22.0, max(0.0, (volume_ratio - 1.0) * 12.0))
    score += min(16.0, max(0.0, float(prev_pct_change) - 2.0))
    score += min(12.0, max(0.0, float(range_pct) - 4.0))
    score += min(10.0, max(0.0, float(rs_vs_spy) * 0.8))
    score += 8.0 if close_to_high_pct <= 2.5 else 0.0
    score += 10.0 if is_pre_surge else 0.0
    score += 6.0 if strategy_type == "REVERSAL" else 0.0
    if is_sub7:
        gate = resolve_amex_moonshot_gate()
        score += float(gate.get("sub7_bonus", 10.0))
        if breakout_10d or breakout_20d:
            score += float(gate.get("sub7_breakout_bonus", 8.0))
    return {
        "price": round(close_now, 4),
        "is_sub7": bool(is_sub7),
        "gap_pct": round(gap_pct, 2),
        "range_pct": round(range_pct, 2),
        "volume_ratio": round(volume_ratio, 2),
        "close_to_high_pct": round(close_to_high_pct, 2),
        "breakout_10d": breakout_10d,
        "breakout_20d": breakout_20d,
        "is_pre_surge": is_pre_surge,
        "strategy_type": strategy_type,
        "moonshot_score": round(score, 1),
    }


def get_us_hard_filter_reject_reason(
    alpha_score: float,
    real_trend: str,
    is_amex: bool,
    rs_vs_spy: float,
    strategy_type: str,
    cfg: Optional[Dict[str, float]] = None,
) -> Optional[str]:
    gate = cfg or resolve_us_hard_filter_gate()
    min_alpha = float(gate.get("min_alpha", 40.0))
    min_alpha_down = float(gate.get("min_alpha_down", 55.0))
    amex_rs_min = float(gate.get("amex_rs_min", -5.0))

    if str(real_trend) == "DOWN" and float(alpha_score) < min_alpha_down:
        return "US_HARD_FILTER_TREND_ALPHA"
    if float(alpha_score) < min_alpha:
        return "US_HARD_FILTER_ALPHA_FLOOR"
    if bool(is_amex) and float(rs_vs_spy) < amex_rs_min and str(strategy_type) != "REVERSAL":
        return "US_HARD_FILTER_RS_AMEX"
    return None


def get_amex_moonshot_reject_reason(
    *,
    alpha_score: float,
    real_trend: str,
    rs_vs_spy: float,
    features: Dict[str, Any],
    cfg: Optional[Dict[str, float]] = None,
) -> Optional[str]:
    gate = cfg or resolve_amex_moonshot_gate()
    price = float(features.get("price", 0.0) or 0.0)
    moonshot_score = float(features.get("moonshot_score", 0.0) or 0.0)
    if price < float(gate["min_price"]) or price > float(gate["max_price"]):
        return "AMEX_MOONSHOT_PRICE_BAND_FAIL"
    if str(real_trend) == "DOWN" and float(alpha_score) < float(gate["min_alpha_down"]) and moonshot_score < float(gate["market_policy_override_score"]):
        return "AMEX_MOONSHOT_TREND_ALPHA_FAIL"
    if float(alpha_score) < float(gate["min_alpha"]) and moonshot_score < float(gate["min_moonshot_score"]):
        return "AMEX_MOONSHOT_ALPHA_FLOOR"
    if float(rs_vs_spy) < float(gate["min_rs"]) and moonshot_score < float(gate["market_policy_override_score"]):
        return "AMEX_MOONSHOT_RS_FAIL"
    return None


def resolve_us_strategy_tag(surge_data: Dict[str, Any]) -> Dict[str, Any]:
    is_pre_surge = bool(surge_data.get("is_pre_surge", False))
    strategy_type = str(surge_data.get("strategy_type", "Wait"))
    strategy_tag = "🚀 Momentum"
    if is_pre_surge or strategy_type == "REVERSAL":
        strategy_tag = f"🎣 {surge_data.get('type', 'Bounce')}"
    return {"is_pre_surge": is_pre_surge, "strategy_type": strategy_type, "strategy_tag": strategy_tag}


def passes_us_baseline_filter(strategy_type: str, wr: float, pf: float) -> bool:
    if strategy_type == "PRE_SURGE":
        return pf >= 0.3
    if strategy_type == "REVERSAL":
        return not (wr < 28 and pf < 1.0)
    return not (wr < 38 and pf < 0.7)


def compute_us_relative_strength_vs_spy(df: Any) -> float:
    try:
        from modules.market_data import get_history

        spy_df = get_history("SPY", period="20d", interval="1d")
        if spy_df.empty or "Close" not in spy_df.columns:
            return 0.0
        spy = spy_df["Close"]
        if len(spy) < 10:
            return 0.0
        stock_ret = (float(df["Close"].iloc[-1]) / float(df["Close"].iloc[-10]) - 1) * 100
        spy_ret = (float(spy.iloc[-1]) / float(spy.iloc[-10]) - 1) * 100
        return float(stock_ret - spy_ret)
    except Exception:
        return 0.0


def compute_kr_flow_leader_signal(
    *,
    df: Any,
    ml_prob: float,
    whale_data: Optional[Dict[str, Any]] = None,
    setup: Optional[Dict[str, Any]] = None,
    real_trend: str = "",
    alpha_score: Optional[float] = None,
) -> Dict[str, Any]:
    try:
        import pandas as pd

        close_curr = float(df["Close"].iloc[-1])
        open_curr = float(df["Open"].iloc[-1])
        high_curr = float(df["High"].iloc[-1])
        low_curr = float(df["Low"].iloc[-1])
        prev_close = float(df["Close"].iloc[-2]) if len(df) >= 2 else close_curr
        vol_current = float(df["Volume"].iloc[-1])
        vol_ma20 = float(df["Volume"].rolling(20, min_periods=5).mean().iloc[-1])
        vol_ma20 = vol_ma20 if pd.notna(vol_ma20) and vol_ma20 > 0 else 1.0
        volume_ratio = _safe_numeric((setup or {}).get("Volume Ratio"), vol_current / vol_ma20)
        turnover_today = close_curr * vol_current
        turnover_ma20 = _safe_numeric(((df["Close"] * df["Volume"]).rolling(20, min_periods=5).mean()).iloc[-1], turnover_today)
        turnover_ratio = turnover_today / max(turnover_ma20, 1.0)
        range_size = max(high_curr - low_curr, close_curr * 0.001)
        close_location = (close_curr - low_curr) / range_size
        close_location_score = _clamp_float(close_location * 100.0, 0.0, 100.0)
        recent_high = _safe_numeric(df["High"].rolling(20, min_periods=5).max().shift(1).iloc[-1], close_curr)
        breakout_buffer = close_curr / max(recent_high, 0.001)
        breakout = bool(breakout_buffer >= 0.992)
        breakout_quality = _clamp_float(50.0 + (breakout_buffer - 0.985) * 220.0, 0.0, 100.0)
        day_return_pct = ((close_curr / max(prev_close, 0.001)) - 1.0) * 100.0

        whale = whale_data or {}
        foreigner = _safe_numeric(whale.get("foreigner"), 0.0)
        institution = _safe_numeric(whale.get("institution"), 0.0)
        retail = _safe_numeric(whale.get("retail"), 0.0)
        whale_score = _safe_numeric(whale.get("whale_score"), 50.0)
        whale_net = foreigner + institution
        flow_total_abs = abs(foreigner) + abs(institution) + abs(retail)
        whale_dominance = whale_net / max(flow_total_abs, 1.0)
        flow_consensus = foreigner > 0 and institution > 0
        retail_dominant = retail > 0 and retail > max(abs(whale_net) * 1.4, 1.0)

        score = 28.0
        score += min(22.0, max(-14.0, (whale_score - 50.0) * 0.55))
        score += min(11.0, max(-9.0, whale_dominance * 28.0))
        if flow_consensus:
            score += 8.0
        if retail_dominant:
            score -= 10.0
        score += min(15.0, max(-5.0, (turnover_ratio - 1.0) * 12.0))
        score += min(11.0, max(-4.0, (volume_ratio - 1.0) * 10.0))
        score += min(13.0, max(-10.0, (close_location - 0.5) * 26.0))
        score += min(7.0, max(-9.0, day_return_pct * 1.35))
        score += min(8.0, max(0.0, (float(ml_prob) - 50.0) * 0.22))
        score += min(7.0, max(0.0, ((_safe_numeric(alpha_score, 45.0)) - 45.0) * 0.20))
        if breakout:
            score += 8.0
        trend = str(real_trend or "").upper()
        if trend == "UP":
            score += 5.0
        elif trend == "DOWN":
            score -= 7.0
        if close_curr > open_curr:
            score += 3.0

        leader_score = round(_clamp_float(score, 0.0, 100.0), 1)
        is_market_leader = bool(
            (
                leader_score >= 70.0
                and close_location >= 0.67
                and turnover_ratio >= 1.15
                and whale_net >= 0.0
            )
            or (
                leader_score >= 77.0
                and breakout
                and volume_ratio >= 1.2
                and close_curr > open_curr
            )
        )
        return {
            "is_market_leader": is_market_leader,
            "leader_score": leader_score,
            "volume_ratio": round(float(volume_ratio), 3),
            "turnover_ratio_20d": round(float(turnover_ratio), 3),
            "close_location_score": round(float(close_location_score), 1),
            "breakout_quality_score": round(float(breakout_quality), 1),
            "breakout": bool(breakout),
            "day_return_pct": round(float(day_return_pct), 2),
            "whale_score": round(float(whale_score), 1),
            "whale_net_flow": round(float(whale_net), 1),
            "foreign_flow": round(float(foreigner), 1),
            "institution_flow": round(float(institution), 1),
            "retail_flow": round(float(retail), 1),
            "flow_consensus_buying": bool(flow_consensus),
            "retail_dominant": bool(retail_dominant),
        }
    except Exception:
        return {
            "is_market_leader": False,
            "leader_score": 0.0,
            "volume_ratio": 0.0,
            "turnover_ratio_20d": 0.0,
            "close_location_score": 0.0,
            "breakout_quality_score": 0.0,
            "breakout": False,
            "day_return_pct": 0.0,
            "whale_score": _safe_numeric((whale_data or {}).get("whale_score"), 50.0),
            "whale_net_flow": 0.0,
            "foreign_flow": 0.0,
            "institution_flow": 0.0,
            "retail_flow": 0.0,
            "flow_consensus_buying": False,
            "retail_dominant": False,
        }


def detect_market_leader(
    df: Any,
    ml_prob: float,
    *,
    whale_data: Optional[Dict[str, Any]] = None,
    setup: Optional[Dict[str, Any]] = None,
    real_trend: str = "",
    alpha_score: Optional[float] = None,
) -> bool:
    return bool(
        compute_kr_flow_leader_signal(
            df=df,
            ml_prob=ml_prob,
            whale_data=whale_data,
            setup=setup,
            real_trend=real_trend,
            alpha_score=alpha_score,
        ).get("is_market_leader", False)
    )


def passes_kr_baseline_filter(strategy_type: str, wr: float, pf: float, is_market_leader: bool) -> bool:
    if is_market_leader:
        return True
    if strategy_type == "PRE_SURGE":
        return pf >= 0.5
    if strategy_type == "REVERSAL":
        return not (wr < 30 and pf < 1.5)
    return not (wr < 40 and pf < 0.8)


def resolve_kr_strategy_tag(
    is_market_leader: bool,
    is_pre_surge: bool,
    surge_data: Dict[str, Any],
) -> str:
    if is_market_leader:
        return "👑 주도주 하이패스"
    if is_pre_surge or str(surge_data.get("strategy_type", "")) == "REVERSAL":
        return f"🎣 {surge_data.get('type')}"
    return "🚀 Momentum"


def apply_kr_sector_gate(sym: str, ticker_df: Any, tier: str, tier_sort: int) -> Dict[str, Any]:
    sector_ok = True
    sector_name = "기타"
    adjusted_tier = tier
    adjusted_tier_sort = tier_sort

    try:
        from sector_analysis import SectorRotation

        _sr = SectorRotation(lookback_days=20)
        sector_ok = bool(_sr.is_in_top_sector(sym, n=3, ticker_df=ticker_df))
        sector_name = str(_sr.get_ticker_sector_dynamic(sym, ticker_df=ticker_df))
    except Exception:
        pass

    if not sector_ok and adjusted_tier_sort <= 2:
        adjusted_tier = "T3"
        adjusted_tier_sort = 3

    return {
        "sector_ok": sector_ok,
        "sector_name": sector_name,
        "tier": adjusted_tier,
        "tier_sort": adjusted_tier_sort,
    }


def build_us_scan_outputs(
    sym: str,
    stock_name: str,
    alpha_score: float,
    whale_score: float,
    real_trend: str,
    prev_pct_change: float,
    consec_days: int,
    rs_tag: str,
    setup: Dict[str, Any],
    strategy_tag: str,
    surge_tag: str,
    wr: float,
    position: str,
    news_tag: str,
    prob_5: float,
    prob_clean: float,
    decision_score: float,
    conviction_score: float,
    tier: str,
    tier_sort: int,
    is_amex: bool,
    tech_score: int,
    verdict_label: str,
    market_gate: str,
    kospi_chg: float,
    phase25_variant: Optional[str] = None,
    phase25_prob: Optional[float] = None,
    phase25_shadow_variant: Optional[str] = None,
    phase25_shadow_prob: Optional[float] = None,
    phase25_recommended_threshold: Optional[float] = None,
    model_trace_status: Optional[str] = None,
    model_error: Optional[str] = None,
    theme_context: Optional[Dict[str, Any]] = None,
    leader_metrics: Optional[Dict[str, Any]] = None,
    routing_path: str = "",
    theme_score_adjustment: float = 0.0,
    expected_edge_score: Optional[float] = None,
    expected_return_1d_pct: Optional[float] = None,
    expected_return_3d_pct: Optional[float] = None,
    scan_mode: str = "SWING",
    strategy_family: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """Build US scanner table row + DB payload with legacy field compatibility."""
    curr_fmt = "{:,.2f}"
    volume_ratio = setup.get("Volume Ratio", "?")
    volume_badge = f"{'✅' if setup.get('Volume Confirmed') else '⚠️'} x{volume_ratio}"

    res_data = {
        "Tier": tier,
        "_tier_sort": tier_sort,
        "Ticker": sym,
        "Name": stock_name,
        "Antigrav": int(alpha_score),
        "Whale": f"{whale_score}pts",
        "Trend": real_trend,
        "1D Change": f"{prev_pct_change:+.2f}%",
        "Consecutive": f"{consec_days} UP" if consec_days > 0 else f"{abs(consec_days)} DOWN",
        "RS vs SPY": rs_tag,
        "Entry(-2%)": curr_fmt.format(setup.get("Entry Price", 0)),
        "Target": curr_fmt.format(setup.get("Target Price", 0)),
        "Stop": f"{curr_fmt.format(setup.get('Stop Loss', 0))} ({setup.get('ATR Stop %', '-3%')})",
        "Hold": f"{setup.get('Max Hold Days', 3)}d",
        "Volume": volume_badge,
        "Strategy": strategy_tag,
        "Surge": surge_tag,
        "WR": f"{wr:.0f}%",
        "AI Prob": f"{prob_5:.1f}%",
        "Clean Hit": f"{prob_clean:.1f}%",
        "Conviction": conviction_score,
        "Position": position,
        "Context": news_tag,
        "_prob_5": prob_5,
        "_prob_clean": prob_clean,
        "Decision Score": decision_score,
        "scan_mode": str(scan_mode or "SWING").upper(),
        "strategy_family": strategy_family or resolve_strategy_family("AMEX" if is_amex else "US", is_amex=is_amex),
        "_theme_context": theme_context or {},
        "_leader_metrics": leader_metrics or {},
        "_routing_path": routing_path or "",
        "Theme": (theme_context or {}).get("primary_theme", "-") if isinstance(theme_context, dict) else "-",
        "phase25_variant": phase25_variant,
        "phase25_prob": phase25_prob,
        "phase25_shadow_variant": phase25_shadow_variant,
        "phase25_shadow_prob": phase25_shadow_prob,
        "phase25_recommended_threshold": phase25_recommended_threshold,
        "model_trace_status": model_trace_status,
        "model_error": model_error,
        "expected_edge_score": expected_edge_score,
        "expected_return_1d_pct": expected_return_1d_pct,
        "expected_return_3d_pct": expected_return_3d_pct,
    }

    db_payload = {
        "ticker": sym,
        "name": stock_name,
        "alpha_score": int(alpha_score),
        "tech_score": int(tech_score),
        "ml_prob": round(prob_5, 1),
        "whale_score": int(whale_score),
        "fund_status": "US",
        "initial_trend": real_trend,
        "market_type": "AMEX" if is_amex else "US",
        "note": strategy_tag,
        "position": position,
        "verdict": verdict_label,
        "tier": tier,
        "volume": volume_badge,
        "context": news_tag,
        "surge": surge_tag,
        "win_rate": f"{wr:.0f}%",
        "decision_score": decision_score,
        "market_gate": market_gate,
        "kospi_chg": round(float(kospi_chg), 2),
        "conviction_score": round(float(conviction_score), 1),
        "strategy_family": strategy_family or resolve_strategy_family("AMEX" if is_amex else "US", is_amex=is_amex),
        "phase25_prob": phase25_prob,
        "phase25_variant": phase25_variant,
        "phase25_shadow_variant": phase25_shadow_variant,
        "phase25_shadow_prob": phase25_shadow_prob,
        "phase25_recommended_threshold": phase25_recommended_threshold,
        "model_trace_status": model_trace_status,
        "model_error": model_error,
        "expected_edge_score": expected_edge_score,
        "expected_return_1d_pct": expected_return_1d_pct,
        "expected_return_3d_pct": expected_return_3d_pct,
        "theme_context": theme_context or {},
        "leader_metrics": leader_metrics or {},
        "routing_path": routing_path or "",
        "theme_score_adjustment": round(float(theme_score_adjustment or 0.0), 2),
        **_theme_flat_fields(theme_context),
    }
    return {"res_data": res_data, "db_payload": db_payload}


def build_kr_scan_outputs(
    sym: str,
    stock_name: str,
    alpha_score: float,
    whale_score: float,
    whale_trend: str,
    real_trend: str,
    prev_pct_change: float,
    consec_days: int,
    setup: Dict[str, Any],
    news_tag: str,
    strategy_tag: str,
    surge_tag: str,
    wr: float,
    position: str,
    prob_5: float,
    prob_clean: float,
    decision_score: float,
    conviction_score: float,
    tier: str,
    tier_sort: int,
    tech_score: int,
    fund_ok: bool,
    m_type: str,
    verdict_label: str,
    market_gate: str,
    kospi_chg: float,
    phase25_variant: Optional[str] = None,
    phase25_prob: Optional[float] = None,
    phase25_shadow_variant: Optional[str] = None,
    phase25_shadow_prob: Optional[float] = None,
    phase25_recommended_threshold: Optional[float] = None,
    model_trace_status: Optional[str] = None,
    model_error: Optional[str] = None,
    theme_context: Optional[Dict[str, Any]] = None,
    leader_metrics: Optional[Dict[str, Any]] = None,
    routing_path: str = "",
    theme_score_adjustment: float = 0.0,
    expected_edge_score: Optional[float] = None,
    expected_return_1d_pct: Optional[float] = None,
    expected_return_3d_pct: Optional[float] = None,
    scan_mode: str = "SWING",
    strategy_family: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """Build KR scanner table row + DB payload with legacy field compatibility."""
    curr_fmt = "{:,.0f}"
    volume_ratio = setup.get("Volume Ratio", "?")
    table_volume = f"{'✅' if setup.get('Volume Confirmed') else '⚠️'} {volume_ratio}"
    db_volume = f"{'✅' if setup.get('Volume Confirmed') else '⚠️'} x{volume_ratio}"
    context_text = news_tag if news_tag else "-"

    res_data = {
        "Tier": tier,
        "_tier_sort": tier_sort,
        "티커": sym,
        "종목명": stock_name,
        "Antigrav": int(alpha_score),
        "수급": f"{whale_score}점 {whale_trend}",
        "추세": real_trend,
        "전일비": f"{prev_pct_change:+.2f}%",
        "연속등락": f"{consec_days}일 연속 상승" if consec_days > 0 else f"{abs(consec_days)}일 연속 하락",
        "매수가(-2%)": curr_fmt.format(setup.get("Entry Price", 0)),
        "목표가(+3.5%)": curr_fmt.format(setup.get("Target Price", 0)),
        "손절가": f"{curr_fmt.format(setup.get('Stop Loss', 0))} ({setup.get('ATR Stop %', '-3%')})",
        "보유한도": f"{setup.get('Max Hold Days', 3)}일",
        "거래량": table_volume,
        "시장맥락": context_text,
        "전략": strategy_tag,
        "급등예측": surge_tag,
        "승률": f"{wr:.0f}%",
        "AI확률": f"{prob_5:.1f}%",
        "정밀확률": f"{prob_clean:.1f}%",
        "확신도": conviction_score,
        "위치": position,
        "_prob_5": prob_5,
        "_prob_clean": prob_clean,
        "Decision Score": decision_score,
        "scan_mode": str(scan_mode or "SWING").upper(),
        "strategy_family": strategy_family or resolve_strategy_family(m_type),
        "_theme_context": theme_context or {},
        "_leader_metrics": leader_metrics or {},
        "_routing_path": routing_path or "",
        "테마": (theme_context or {}).get("primary_theme", "-") if isinstance(theme_context, dict) else "-",
        "phase25_variant": phase25_variant,
        "phase25_prob": phase25_prob,
        "phase25_shadow_variant": phase25_shadow_variant,
        "phase25_shadow_prob": phase25_shadow_prob,
        "phase25_recommended_threshold": phase25_recommended_threshold,
        "model_trace_status": model_trace_status,
        "model_error": model_error,
        "expected_edge_score": expected_edge_score,
        "expected_return_1d_pct": expected_return_1d_pct,
        "expected_return_3d_pct": expected_return_3d_pct,
    }

    db_payload = {
        "ticker": sym,
        "name": stock_name,
        "alpha_score": int(alpha_score),
        "tech_score": int(tech_score),
        "ml_prob": round(prob_5, 1),
        "whale_score": int(whale_score),
        "fund_status": "Pass" if fund_ok else "Fail",
        "initial_trend": real_trend,
        "market_type": m_type,
        "note": strategy_tag,
        "position": position,
        "verdict": verdict_label,
        "tier": tier,
        "volume": db_volume,
        "context": context_text,
        "surge": surge_tag,
        "win_rate": f"{wr:.0f}%",
        "decision_score": decision_score,
        "market_gate": market_gate,
        "kospi_chg": round(float(kospi_chg), 2),
        "conviction_score": round(float(conviction_score), 1),
        "strategy_family": strategy_family or resolve_strategy_family(m_type),
        "phase25_prob": phase25_prob,
        "phase25_variant": phase25_variant,
        "phase25_shadow_variant": phase25_shadow_variant,
        "phase25_shadow_prob": phase25_shadow_prob,
        "phase25_recommended_threshold": phase25_recommended_threshold,
        "model_trace_status": model_trace_status,
        "model_error": model_error,
        "expected_edge_score": expected_edge_score,
        "expected_return_1d_pct": expected_return_1d_pct,
        "expected_return_3d_pct": expected_return_3d_pct,
        "theme_context": theme_context or {},
        "leader_metrics": leader_metrics or {},
        "routing_path": routing_path or "",
        "theme_score_adjustment": round(float(theme_score_adjustment or 0.0), 2),
        **_theme_flat_fields(theme_context),
    }
    return {"res_data": res_data, "db_payload": db_payload}


def classify_us_verdict(alpha_score: float, whale_score: float, real_trend: str) -> str:
    if alpha_score >= 90 and whale_score >= 65 and real_trend == "UP":
        return "⚡ Strong Conviction"
    if alpha_score >= 80 and real_trend == "UP":
        return "🟢 Strong Buy"
    if alpha_score >= 70:
        return "🔵 Buy"
    if alpha_score >= 55:
        return "🟡 Watch"
    return "🔴 Weak"


def classify_us_tier(alpha_score: float, whale_score: float, real_trend: str, is_amex: bool) -> Dict[str, Any]:
    whale_t0 = 60 if is_amex else 70
    whale_t1 = 50 if is_amex else 65
    whale_t2 = 40 if is_amex else 55
    alpha_t0 = 88 if is_amex else 90
    alpha_t1 = 72 if is_amex else 75
    alpha_t2 = 62 if is_amex else 65

    if alpha_score >= alpha_t0 and whale_score >= whale_t0 and real_trend == "UP":
        return {"tier": "⚡T0", "tier_sort": 0}
    if alpha_score >= alpha_t1 and whale_score >= whale_t1 and real_trend == "UP":
        return {"tier": "🏆T1", "tier_sort": 1}
    if alpha_score >= alpha_t2 and whale_score >= whale_t2:
        return {"tier": "⭐T2", "tier_sort": 2}
    return {"tier": "T3", "tier_sort": 3}


def passes_us_hard_filters(
    alpha_score: float,
    real_trend: str,
    is_amex: bool,
    rs_vs_spy: float,
    strategy_type: str,
) -> bool:
    return get_us_hard_filter_reject_reason(
        alpha_score=alpha_score,
        real_trend=real_trend,
        is_amex=is_amex,
        rs_vs_spy=rs_vs_spy,
        strategy_type=strategy_type,
    ) is None


def classify_kr_verdict(alpha_score: float, whale_score: float, real_trend: str) -> str:
    if alpha_score >= 90 and whale_score >= 70 and real_trend == "UP":
        return "⚡ 초강력 매수"
    if alpha_score >= 80 and real_trend == "UP":
        return "🟢 강력 매수"
    if alpha_score >= 70:
        return "🔵 매수"
    if alpha_score >= 55:
        return "🟡 관망"
    return "🔴 약세"


def classify_kr_tier(alpha_score: float, whale_score: float, real_trend: str) -> Dict[str, Any]:
    if alpha_score >= 90 and whale_score >= 70 and real_trend == "UP":
        return {"tier": "⚡T0", "tier_sort": 0}
    if alpha_score >= 75 and whale_score >= 65 and real_trend == "UP":
        return {"tier": "🏆T1", "tier_sort": 1}
    if alpha_score >= 65 and whale_score >= 55:
        return {"tier": "⭐T2", "tier_sort": 2}
    return {"tier": "T3", "tier_sort": 3}


def passes_kr_hard_filters(
    alpha_score: float,
    real_trend: str,
    market_type: str | None = None,
    ticker: str | None = None,
    market_gate: str | None = None,
) -> bool:
    market = resolve_profile_market(market_type=market_type, ticker=ticker)
    regime = resolve_profile_regime(market_gate)
    down_min_alpha = 50.0
    base_min_alpha = 40.0
    if market == "KOSDAQ" and regime == "BEAR":
        try:
            down_min_alpha = float(os.getenv("AG_KOSDAQ_BEAR_DOWN_MIN_ALPHA", "45"))
        except Exception:
            down_min_alpha = 45.0
    if real_trend == "DOWN" and alpha_score < down_min_alpha:
        return False
    if alpha_score < base_min_alpha:
        return False
    return True


def _is_nan_like(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(value != value)
    except Exception:
        return False


def evaluate_app_us_candidate(
    sym: str,
    stock_name: str,
    qs: Any,
    is_amex: bool,
    is_exhausted: bool,
    exhaustion_tag: str,
    prev_pct_change: float,
    consec_days: int,
    r_status: str,
    intel_data: Any,
    tech_score: int,
    macro_ctx: Any,
    market_gate: Dict[str, Any],
    rank_adjustment_fn: Callable[..., float],
    news_adjustment_fn: Callable[..., Dict[str, Any]],
    reject_reason_fn: Optional[Callable[[str], None]] = None,
    reject_meta_fn: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Optional[Dict[str, Dict[str, Any]]]:
    def _reject(reason: str, meta: Optional[Dict[str, Any]] = None) -> None:
        if reject_reason_fn is None:
            pass
        else:
            try:
                reject_reason_fn(reason)
            except Exception:
                pass
        if reject_meta_fn is None:
            return
        try:
            payload = {"reason": reason}
            if isinstance(meta, dict):
                payload.update(meta)
            reject_meta_fn(payload)
        except Exception:
            pass

    latest = qs.df.iloc[-1]
    curr_price = float(latest.get("Close", 0) or 0)
    curr_vol = float(latest.get("Volume", 0) or 0)

    min_price = 1.0 if is_amex else 5.0
    min_vol = 50_000 if is_amex else 200_000
    if curr_price < min_price or curr_vol < min_vol:
        _reject("US_MIN_PRICE_VOLUME_FAIL")
        return None

    signal_cfg = resolve_us_signal_window_gate()
    amex_cfg = resolve_amex_moonshot_gate() if is_amex else {}
    lookback = int(amex_cfg.get("signal_lookback", 20)) if is_amex else int(signal_cfg["lookback"])
    min_hits = int(amex_cfg.get("signal_min_hits", 0)) if is_amex else int(signal_cfg["min_hits"])
    if "Signal" not in qs.df.columns:
        _reject(
            "US_SIGNAL_COLUMN_MISSING",
            {
                "lookback": lookback,
                "min_hits": min_hits,
            },
        )
        return None
    sig_window = qs.df["Signal"].tail(lookback)
    sig_hits = int((sig_window.fillna(0) > 0).sum())
    amex_features = compute_amex_moonshot_features(
        df=qs.df,
        prev_pct_change=float(prev_pct_change),
        rs_vs_spy=compute_us_relative_strength_vs_spy(qs.df),
        surge_data=qs.detect_pre_surge_signals(),
    ) if is_amex else {}
    amex_signal_ok = (
        sig_hits >= min_hits
        or bool(amex_features.get("breakout_20d"))
        or (
            float(amex_features.get("volume_ratio", 0.0) or 0.0) >= float(amex_cfg.get("min_volume_ratio", 1.8))
            and float(prev_pct_change) >= float(amex_cfg.get("min_day_change", 4.0))
        )
        or bool(amex_features.get("is_pre_surge"))
        or str(amex_features.get("strategy_type", "")).upper() == "REVERSAL"
        or (
            float(amex_features.get("range_pct", 0.0) or 0.0) >= float(amex_cfg.get("min_range_pct", 6.0))
            and float(amex_features.get("close_to_high_pct", 99.0) or 99.0)
            <= float(amex_cfg.get("max_close_to_high_pct", 2.5))
        )
    ) if is_amex else True
    if (not is_amex and sig_hits < min_hits) or (is_amex and not amex_signal_ok):
        _reject(
            "AMEX_MOONSHOT_SETUP_FAIL" if is_amex else "US_SIGNAL_WINDOW_FAIL",
            {
                "lookback": lookback,
                "min_hits": min_hits,
                "signal_hits": sig_hits,
                "amex_features": amex_features if is_amex else None,
            },
        )
        return None

    stats = qs.backtest()
    surge_data = qs.detect_pre_surge_signals()
    us_strategy = resolve_us_strategy_tag(surge_data)
    strategy_type = str(us_strategy["strategy_type"])
    strategy_tag = str(us_strategy["strategy_tag"])

    metrics = parse_wr_pf(stats)
    wr = float(metrics["wr"])
    pf = float(metrics["pf"])
    if not passes_us_baseline_filter(strategy_type=strategy_type, wr=wr, pf=pf):
        _reject("US_BASELINE_FILTER_FAIL")
        return None

    if qs.check_earnings_risk():
        _reject("US_EARNINGS_RISK_BLOCK")
        return None

    setup = qs.get_trade_setup()
    whale_data = qs.get_investor_flows()
    whale_score = whale_data.get("whale_score", 0)

    alpha_score = qs.calculate_antigravity_score(
        wr / 100.0,
        pf,
        0,
        whale_score=whale_score,
        macro_status=r_status,
    )
    if _is_nan_like(alpha_score):
        _reject("US_ALPHA_SCORE_NAN")
        return None

    real_trend = qs.get_real_trend()
    rs_vs_spy = compute_us_relative_strength_vs_spy(qs.df)

    news_adj = news_adjustment_fn(stock_name, sym, "", intel_data)
    alpha_score = min(100, max(0, float(alpha_score) + float(news_adj.get("score_adjustment", 0))))
    news_tag = "🔥 Beneficiary" if news_adj.get("is_beneficiary") else ("⚠️ Impact" if news_adj.get("is_victim") else "-")

    if is_exhausted:
        strategy_tag = f"{strategy_tag} | {exhaustion_tag}"

    verdict_label = classify_us_verdict(
        alpha_score=float(alpha_score),
        whale_score=float(whale_score),
        real_trend=str(real_trend),
    )
    us_tier = classify_us_tier(
        alpha_score=float(alpha_score),
        whale_score=float(whale_score),
        real_trend=str(real_trend),
        is_amex=bool(is_amex),
    )
    tier = us_tier["tier"]
    tier_sort = int(us_tier["tier_sort"])
    ml_pred = qs.get_ml_prediction() or {}
    pre_profile_overlay = resolve_ticker_profile_overlay(
        ticker=sym,
        market_type="AMEX" if is_amex else "US",
        market_gate=str((market_gate or {}).get("gate", "GREEN")),
        setup={},
    )

    market_policy = evaluate_market_policy(
        alpha_score=float(alpha_score),
        ai_prob=float(ml_pred.get("prob", 50) or 50),
        market_type="AMEX" if is_amex else "US",
        ticker=sym,
        market_gate=str((market_gate or {}).get("gate", "GREEN")),
    )
    hard_gate_cfg = resolve_us_hard_filter_gate()
    hard_reason = (
        get_amex_moonshot_reject_reason(
            alpha_score=float(alpha_score),
            real_trend=str(real_trend),
            rs_vs_spy=float(rs_vs_spy),
            features=amex_features,
            cfg=amex_cfg,
        )
        if is_amex
        else get_us_hard_filter_reject_reason(
            alpha_score=float(alpha_score),
            real_trend=str(real_trend),
            is_amex=bool(is_amex),
            rs_vs_spy=float(rs_vs_spy),
            strategy_type=str(strategy_type),
            cfg=hard_gate_cfg,
        )
    )
    allow_amex_policy_override = bool(is_amex) and (
        float(amex_features.get("moonshot_score", 0.0) or 0.0) >= float(amex_cfg.get("min_moonshot_score", 62.0))
        and (
            bool(amex_features.get("breakout_10d"))
            or bool(amex_features.get("breakout_20d"))
            or bool(amex_features.get("is_pre_surge"))
            or str(amex_features.get("strategy_type", "")).upper() == "REVERSAL"
            or float(amex_features.get("volume_ratio", 0.0) or 0.0) >= float(amex_cfg.get("min_volume_ratio", 1.8))
        )
    )
    if market_policy.get("hard_reject") and not profile_supports_hard_filter_override(pre_profile_overlay) and not allow_amex_policy_override:
        _reject(
            str(market_policy.get("reason") or "MARKET_POLICY_AVOID"),
            {
                "policy": market_policy.get("policy"),
                "alpha_score": round(float(alpha_score), 2),
                "ai_prob": round(float(ml_pred.get("prob", 50) or 50), 2),
                "amex_features": amex_features if is_amex else None,
            },
        )
        return None
    if hard_reason is not None and not profile_supports_hard_filter_override(pre_profile_overlay) and not allow_amex_policy_override:
        _reject(
            hard_reason,
            {
                "alpha_score": round(float(alpha_score), 2),
                "real_trend": str(real_trend),
                "is_amex": bool(is_amex),
                "rs_vs_spy": round(float(rs_vs_spy), 2),
                "strategy_type": str(strategy_type),
                "hard_filter_cfg": hard_gate_cfg,
                "amex_features": amex_features if is_amex else None,
            },
        )
        return None

    position = qs.get_price_position()
    rs_tag = f"+{rs_vs_spy:.1f}% vs SPY" if rs_vs_spy >= 0 else f"{rs_vs_spy:.1f}% vs SPY"

    surge_data_probs = compute_surge_tag_data(
        df=qs.df,
        ml_pred=ml_pred,
    )
    surge_tag = surge_data_probs["surge_tag"]
    prob_5 = float(surge_data_probs["prob_5"])
    prob_clean = float(surge_data_probs["prob_clean"])
    if is_amex:
        prob_5 = max(prob_5, round(min(99.0, 18.0 + float(amex_features.get("moonshot_score", 0.0) or 0.0) * 0.72), 1))
        prob_clean = max(prob_clean, round(min(95.0, 14.0 + float(amex_features.get("moonshot_score", 0.0) or 0.0) * 0.58), 1))
    profile_overlay = resolve_ticker_profile_overlay(
        ticker=sym,
        market_type="AMEX" if is_amex else "US",
        market_gate=str((market_gate or {}).get("gate", "GREEN")),
        setup=setup,
    )
    setup = profile_overlay["setup"]
    if profile_overlay["profile"] is not None:
        strategy_tag = f"{strategy_tag} | Profile:{profile_overlay['overlay'].get('policy', 'NEUTRAL')}"
    conviction_score = compute_conviction_score(
        alpha_score=float(alpha_score),
        whale_score=float(whale_score),
        prob_5=float(prob_5),
        prob_clean=float(prob_clean),
        wr=float(wr),
        pf=float(pf),
        real_trend=str(real_trend),
        position=str(position),
        market_gate=str((market_gate or {}).get("gate", "GREEN")),
        strategy_type=str(strategy_type),
    )
    precision_gate = evaluate_precision_gate(
        conviction_score=float(conviction_score),
        prob_5=float(prob_5),
        prob_clean=float(prob_clean),
        real_trend=str(real_trend),
        market_gate=str((market_gate or {}).get("gate", "GREEN")),
        tier_sort=int(tier_sort),
        market_type="AMEX" if is_amex else "US",
        ticker=sym,
        alpha_score=float(alpha_score),
    )
    if precision_gate["hard_reject"]:
        _reject(
            str(precision_gate["reason"] or "US_PRECISION_GATE_FAIL"),
            {
                "conviction_score": float(conviction_score),
                "prob_5": float(prob_5),
                "prob_clean": float(prob_clean),
                "gate": str((market_gate or {}).get("gate", "GREEN")),
                "tier_sort": int(tier_sort),
                "amex_features": amex_features if is_amex else None,
            },
        )
        return None

    volume_ratio = float(setup.get("Volume Ratio", 1.0) or 1.0)
    edge_adjustment = compute_score_edge_adjustment(
        prob_5=float(prob_5),
        alpha_score=float(alpha_score),
        whale_score=float(whale_score),
        position=str(position),
        strategy_tag=str(strategy_tag),
        volume_ratio=float(volume_ratio),
    )
    decision_score = round(
        (float(alpha_score) * 0.58 + float(whale_score) * 0.10 + float(prob_5) * 0.20 + float(prob_clean) * 0.12)
        + rank_adjustment_fn(
            real_trend,
            position,
            strategy_tag,
            tier,
            whale_score,
            float(volume_ratio),
            macro_ctx=macro_ctx,
            consec_days=consec_days,
        ),
        1,
    )
    if is_amex:
        decision_score = round(
            float(decision_score)
            + float(amex_features.get("moonshot_score", 0.0) or 0.0) * 0.45
            + (8.0 if bool(amex_features.get("breakout_20d")) else 0.0)
            + (5.0 if bool(amex_features.get("is_pre_surge")) else 0.0),
            1,
        )
        sub7_tag = " | Sub-$7" if bool(amex_features.get("is_sub7")) else ""
        strategy_tag = f"🚀 AMEX Moonshot{sub7_tag} | {strategy_tag}"
    decision_score = round(
        float(decision_score)
        + float(edge_adjustment.get("adjustment", 0.0) or 0.0)
        + float(profile_overlay["overlay"].get("score_adjustment", 0.0) or 0.0)
        + float(market_policy.get("score_adjustment", 0.0) or 0.0)
        - float(precision_gate.get("penalty", 0.0) or 0.0)
        + max(0.0, (float(conviction_score) - float(precision_gate.get("min_conviction", 0.0))) * 0.15),
        1,
    )
    theme_overlay = build_theme_overlay(
        sym=sym,
        stock_name=stock_name,
        market_type="AMEX" if is_amex else "US",
        intel_data=intel_data if isinstance(intel_data, dict) else {},
        market_gate=str((market_gate or {}).get("gate", "GREEN")),
        df=qs.df,
        current_price=float(qs.df["Close"].iloc[-1] if qs.df is not None and not qs.df.empty else 0.0),
        volume_ratio=float(volume_ratio),
        decision_score=decision_score,
        scan_mode="SWING",
    )
    decision_score = round(
        float(decision_score) + float(theme_overlay.get("score_adjustment", 0.0) or 0.0),
        1,
    )
    expected_edge = compute_expected_edge_profile(
        prob_5=float(prob_5),
        prob_clean=float(prob_clean),
        decision_score=float(decision_score),
        conviction_score=float(conviction_score),
        real_trend=str(real_trend),
        routing_path=str(theme_overlay.get("routing_path", "core_only") or "core_only"),
        scan_mode="SWING",
        market_gate=str((market_gate or {}).get("gate", "GREEN")),
        theme_context=theme_overlay.get("theme_context", {}),
    )

    outputs = build_us_scan_outputs(
        sym=sym,
        stock_name=stock_name,
        alpha_score=float(alpha_score),
        whale_score=float(whale_score),
        real_trend=str(real_trend),
        prev_pct_change=float(prev_pct_change),
        consec_days=int(consec_days),
        rs_tag=rs_tag,
        setup=setup,
        strategy_tag=str(strategy_tag),
        surge_tag=str(surge_tag),
        wr=float(wr),
        position=str(position),
        news_tag=str(news_tag),
        prob_5=float(prob_5),
        prob_clean=float(prob_clean),
        decision_score=float(decision_score),
        conviction_score=float(conviction_score),
        tier=str(tier),
        tier_sort=int(tier_sort),
        is_amex=bool(is_amex),
        tech_score=int(tech_score),
        verdict_label=str(verdict_label),
        market_gate=str((market_gate or {}).get("gate", "GREEN")),
        kospi_chg=float((market_gate or {}).get("kospi_chg", 0.0)),
        phase25_prob=ml_pred.get("phase25_prob"),
        phase25_variant=ml_pred.get("phase25_variant"),
        phase25_shadow_variant=ml_pred.get("phase25_shadow_variant"),
        phase25_shadow_prob=ml_pred.get("phase25_shadow_prob"),
        phase25_recommended_threshold=ml_pred.get("phase25_recommended_threshold"),
        model_trace_status=ml_pred.get("model_trace_status"),
        model_error=ml_pred.get("model_error"),
        theme_context=theme_overlay.get("theme_context", {}),
        leader_metrics=theme_overlay.get("leader_metrics", {}),
        routing_path=theme_overlay.get("routing_path", "core_only"),
        theme_score_adjustment=theme_overlay.get("score_adjustment", 0.0),
        expected_edge_score=expected_edge.get("expected_edge_score"),
        expected_return_1d_pct=expected_edge.get("expected_return_1d_pct"),
        expected_return_3d_pct=expected_edge.get("expected_return_3d_pct"),
        scan_mode="SWING",
        strategy_family=getattr(qs, "strategy_family", None) or resolve_strategy_family("AMEX" if is_amex else "US", is_amex=is_amex),
    )
    return outputs


def evaluate_app_kr_candidate(
    sym: str,
    stock_name: str,
    qs: Any,
    is_exhausted: bool,
    exhaustion_tag: str,
    prev_pct_change: float,
    consec_days: int,
    r_status: str,
    intel_data: Any,
    tech_score: int,
    market_gate: Dict[str, Any],
    rank_adjustment_fn: Callable[..., float],
    news_adjustment_fn: Callable[..., Dict[str, Any]],
    reject_reason_fn: Optional[Callable[[str], None]] = None,
    reject_meta_fn: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Optional[Dict[str, Dict[str, Any]]]:
    def _reject(reason: str) -> None:
        if reject_reason_fn is None:
            return
        try:
            reject_reason_fn(reason)
        except Exception:
            pass

    def _reject_detail(meta: Dict[str, Any]) -> None:
        if reject_meta_fn is None:
            return
        try:
            reject_meta_fn(meta)
        except Exception:
            pass

    if "Signal" not in qs.df.columns:
        _reject("KR_SIGNAL_COLUMN_MISSING")
        return None
    signal_lookback = 10
    signal_hits = int(qs.df["Signal"].tail(signal_lookback).fillna(0).gt(0).sum())
    if signal_hits <= 0:
        _reject_detail(
            {
                "ticker": sym,
                "stock_name": stock_name,
                "stage": "signal_window",
                "signal_hits": signal_hits,
                "signal_lookback": signal_lookback,
            }
        )
        _reject("KR_SIGNAL_WINDOW_FAIL")
        return None

    stats = qs.backtest()
    surge_data = qs.detect_pre_surge_signals()
    is_pre_surge = bool(surge_data.get("is_pre_surge", False))
    strategy_type = str(surge_data.get("strategy_type", "Wait"))

    ml_pred = qs.get_ml_prediction() or {}
    ml_prob = float(ml_pred.get("prob", 50) or 50)
    setup = qs.get_trade_setup()
    whale_data = qs.get_investor_flows()
    whale_score = whale_data.get("whale_score", 0)
    real_trend = qs.get_real_trend()
    leader_signal = compute_kr_flow_leader_signal(
        df=qs.df,
        ml_prob=ml_prob,
        whale_data=whale_data,
        setup=setup,
        real_trend=str(real_trend),
    )
    is_market_leader = bool(leader_signal.get("is_market_leader", False))

    metrics = parse_wr_pf(stats)
    wr = float(metrics["wr"])
    pf = float(metrics["pf"])
    if not passes_kr_baseline_filter(
        strategy_type=str(strategy_type),
        wr=wr,
        pf=pf,
        is_market_leader=bool(is_market_leader),
    ):
        _reject_detail(
            {
                "ticker": sym,
                "stock_name": stock_name,
                "stage": "baseline_filter",
                "wr": round(float(wr), 2),
                "pf": round(float(pf), 2),
                "strategy_type": str(strategy_type),
                "is_market_leader": bool(is_market_leader),
                "ml_prob": round(float(ml_prob), 2),
                "signal_hits": signal_hits,
                "signal_lookback": signal_lookback,
            }
        )
        _reject("KR_BASELINE_FILTER_FAIL")
        return None
    fund_ok, _fund_note = qs.check_fundamentals()

    alpha_score = qs.calculate_antigravity_score(
        wr / 100.0,
        pf,
        0,
        whale_score=whale_score,
        macro_status=r_status,
    )
    if _is_nan_like(alpha_score):
        _reject("KR_ALPHA_SCORE_NAN")
        return None

    leader_signal = compute_kr_flow_leader_signal(
        df=qs.df,
        ml_prob=ml_prob,
        whale_data=whale_data,
        setup=setup,
        real_trend=str(real_trend),
        alpha_score=float(alpha_score),
    )
    is_market_leader = bool(leader_signal.get("is_market_leader", is_market_leader))

    position = qs.get_price_position()
    strategy_tag = resolve_kr_strategy_tag(
        is_market_leader=bool(is_market_leader),
        is_pre_surge=bool(is_pre_surge),
        surge_data=surge_data,
    )

    news_adj = news_adjustment_fn(stock_name, sym, "", intel_data)
    alpha_score = min(100, max(0, float(alpha_score) + float(news_adj.get("score_adjustment", 0))))

    news_tag = ""
    if is_exhausted:
        strategy_tag = f"{strategy_tag} | {exhaustion_tag}"
    if news_adj.get("is_beneficiary"):
        news_tag = "🔥 수혜"
    elif news_adj.get("is_victim"):
        news_tag = "⚠️ 피해"

    verdict_label = classify_kr_verdict(
        alpha_score=float(alpha_score),
        whale_score=float(whale_score),
        real_trend=str(real_trend),
    )
    m_type = "KR"
    kr_tier = classify_kr_tier(
        alpha_score=float(alpha_score),
        whale_score=float(whale_score),
        real_trend=str(real_trend),
    )
    tier = kr_tier["tier"]
    tier_sort = int(kr_tier["tier_sort"])
    pre_profile_overlay = resolve_ticker_profile_overlay(
        ticker=sym,
        market_type=m_type,
        market_gate=str((market_gate or {}).get("gate", "GREEN")),
        setup={},
    )
    pre_theme_overlay = build_theme_overlay(
        sym=sym,
        stock_name=stock_name,
        market_type="KOSPI" if str(sym).upper().endswith(".KS") else "KOSDAQ",
        intel_data=intel_data if isinstance(intel_data, dict) else {},
        market_gate=str((market_gate or {}).get("gate", "GREEN")),
        df=qs.df,
        current_price=float(qs.df["Close"].iloc[-1] if qs.df is not None and not qs.df.empty else 0.0),
        volume_ratio=float(setup.get("Volume Ratio", 1.0) or 1.0),
        decision_score=float(alpha_score) * 0.65 + float(ml_prob) * 0.35,
        scan_mode="SWING",
    )
    theme_exception_active = bool(pre_theme_overlay.get("exception_allowance", False)) and bool((market_gate or {}).get("theme_exception_allowance", False))
    pre_leader_metrics = pre_theme_overlay.get("leader_metrics", {}) if isinstance(pre_theme_overlay.get("leader_metrics"), dict) else {}
    pre_breakout_quality = float(pre_leader_metrics.get("breakout_quality_score", 0.0) or 0.0)
    pre_close_location = float(pre_leader_metrics.get("close_location_score", 0.0) or 0.0)
    pre_leader_score = float(pre_leader_metrics.get("leader_score", 0.0) or 0.0)
    pre_breakout_quality = max(pre_breakout_quality, float(leader_signal.get("breakout_quality_score", 0.0) or 0.0))
    pre_close_location = max(pre_close_location, float(leader_signal.get("close_location_score", 0.0) or 0.0))
    pre_leader_score = max(pre_leader_score, float(leader_signal.get("leader_score", 0.0) or 0.0))
    phase25_threshold = float(ml_pred.get("phase25_recommended_threshold", 25.0) or 25.0)
    gate_name = str((market_gate or {}).get("gate", "GREEN")).upper()
    min_phase25_support = max(18.0, phase25_threshold - (6.0 if gate_name == "RED" else 8.0))
    theme_exception_strict = (
        theme_exception_active
        and str(real_trend).upper() == "UP"
        and float(alpha_score) >= 34.0
        and float(ml_prob) >= min_phase25_support
        and pre_leader_score >= (74.0 if gate_name == "RED" else 70.0)
        and (pre_breakout_quality >= (48.0 if gate_name == "RED" else 42.0) or pre_close_location >= (76.0 if gate_name == "RED" else 70.0))
    )
    leader_override_active = (
        bool(is_market_leader)
        and str(real_trend).upper() == "UP"
        and float(alpha_score) >= 32.0
        and float(leader_signal.get("leader_score", 0.0) or 0.0) >= (72.0 if gate_name == "RED" else 68.0)
        and float(leader_signal.get("close_location_score", 0.0) or 0.0) >= 64.0
        and not bool(leader_signal.get("retail_dominant", False))
    )

    market_policy = evaluate_market_policy(
        alpha_score=float(alpha_score),
        ai_prob=float(ml_prob),
        market_type=m_type,
        ticker=sym,
        market_gate=str((market_gate or {}).get("gate", "GREEN")),
    )
    if market_policy.get("hard_reject") and not profile_supports_hard_filter_override(pre_profile_overlay) and not theme_exception_strict and not leader_override_active:
        _reject_detail(
            {
                "ticker": sym,
                "stock_name": stock_name,
                "stage": "market_policy",
                "alpha_score": round(float(alpha_score), 2),
                "ai_prob": round(float(ml_prob), 2),
                "market_gate": str((market_gate or {}).get("gate", "GREEN")),
                "policy": market_policy.get("policy"),
                "mode": market_policy.get("mode"),
                "wr": round(float(wr), 2),
                "pf": round(float(pf), 2),
                "real_trend": str(real_trend),
                "signal_hits": signal_hits,
            }
        )
        _reject(str(market_policy.get("reason") or "MARKET_POLICY_AVOID"))
        return None
    kr_hard_filter_pass = passes_kr_hard_filters(
        alpha_score=float(alpha_score),
        real_trend=str(real_trend),
        market_type=m_type,
        ticker=sym,
        market_gate=str((market_gate or {}).get("gate", "GREEN")),
    )
    if not kr_hard_filter_pass and not profile_supports_hard_filter_override(pre_profile_overlay) and not theme_exception_strict and not leader_override_active:
        _reject_detail(
            {
                "ticker": sym,
                "stock_name": stock_name,
                "stage": "hard_filter",
                "alpha_score": round(float(alpha_score), 2),
                "real_trend": str(real_trend),
                "market_gate": str((market_gate or {}).get("gate", "GREEN")),
                "market_type": m_type,
                "wr": round(float(wr), 2),
                "pf": round(float(pf), 2),
                "strategy_type": str(strategy_type),
                "signal_hits": signal_hits,
                "signal_lookback": signal_lookback,
                "tier_sort": int(tier_sort),
                "ml_prob": round(float(ml_prob), 2),
            }
        )
        _reject("KR_HARD_FILTER_FAIL")
        return None
    if theme_exception_strict and (market_policy.get("hard_reject") or not kr_hard_filter_pass):
        strategy_tag = f"{strategy_tag} | ThemeRoute"
    elif leader_override_active and (market_policy.get("hard_reject") or not kr_hard_filter_pass):
        strategy_tag = f"{strategy_tag} | FlowLeader"

    sector_gate = apply_kr_sector_gate(
        sym=sym,
        ticker_df=qs.df,
        tier=str(tier),
        tier_sort=int(tier_sort),
    )
    tier = sector_gate["tier"]
    tier_sort = int(sector_gate["tier_sort"])

    surge_data_probs = compute_surge_tag_data(df=qs.df, ml_pred=ml_pred)
    surge_tag = surge_data_probs["surge_tag"]
    prob_5 = float(surge_data_probs["prob_5"])
    prob_clean = float(surge_data_probs["prob_clean"])
    profile_overlay = resolve_ticker_profile_overlay(
        ticker=sym,
        market_type=m_type,
        market_gate=str((market_gate or {}).get("gate", "GREEN")),
        setup=setup,
    )
    setup = profile_overlay["setup"]
    if profile_overlay["profile"] is not None:
        strategy_tag = f"{strategy_tag} | Profile:{profile_overlay['overlay'].get('policy', 'NEUTRAL')}"
    rank_overlay = predict_rank_overlay(
        market_type="KOSPI" if str(sym).upper().endswith(".KS") else "KOSDAQ",
        market_gate=str((market_gate or {}).get("gate", "GREEN")),
        alpha_score=float(alpha_score),
        ai_prediction=float(prob_5),
        entry_price=float(setup.get("Entry Price", 0) or 0),
        target_price=float(setup.get("Target Price", 0) or 0),
        stop_loss=float(setup.get("Stop Loss", 0) or 0),
    )
    if rank_overlay.get("enabled"):
        strategy_tag = f"{strategy_tag} | Ranker:{rank_overlay.get('prob_up_5d', 0)}%"
    conviction_score = compute_conviction_score(
        alpha_score=float(alpha_score),
        whale_score=float(whale_score),
        prob_5=float(prob_5),
        prob_clean=float(prob_clean),
        wr=float(wr),
        pf=float(pf),
        real_trend=str(real_trend),
        position=str(position),
        market_gate=str((market_gate or {}).get("gate", "GREEN")),
        strategy_type=str(strategy_type),
    )
    precision_gate = evaluate_precision_gate(
        conviction_score=float(conviction_score),
        prob_5=float(prob_5),
        prob_clean=float(prob_clean),
        real_trend=str(real_trend),
        market_gate=str((market_gate or {}).get("gate", "GREEN")),
        tier_sort=int(tier_sort),
        market_type=m_type,
        ticker=sym,
        alpha_score=float(alpha_score),
    )
    theme_precision_override = (
        theme_exception_strict
        and str(precision_gate.get("reason") or "").upper() in {"PRECISION_GATE_RED_MARKET", "PRECISION_GATE_T3_LOW_ML_SUPPORT"}
        and float(conviction_score) >= 52.0
        and float(prob_5) >= 24.0
    )
    leader_precision_override = (
        leader_override_active
        and str(precision_gate.get("reason") or "").upper() in {"PRECISION_GATE_RED_MARKET", "PRECISION_GATE_T3_LOW_ML_SUPPORT", "PRECISION_GATE_LOW_CONVICTION"}
        and float(leader_signal.get("leader_score", 0.0) or 0.0) >= 72.0
        and float(prob_5) >= 20.0
    )
    if precision_gate["hard_reject"] and not theme_precision_override and not leader_precision_override:
        _reject_detail(
            {
                "ticker": sym,
                "stock_name": stock_name,
                "stage": "precision_gate",
                "conviction_score": float(conviction_score),
                "prob_5": float(prob_5),
                "prob_clean": float(prob_clean),
                "alpha_score": float(alpha_score),
                "market_gate": str((market_gate or {}).get("gate", "GREEN")),
                "tier_sort": int(tier_sort),
                "real_trend": str(real_trend),
                "position": str(position),
                "wr": round(float(wr), 2),
                "pf": round(float(pf), 2),
                "strategy_type": str(strategy_type),
            }
        )
        _reject(str(precision_gate["reason"] or "KR_PRECISION_GATE_FAIL"))
        return None

    volume_ratio = float(setup.get("Volume Ratio", 1.0) or 1.0)
    edge_adjustment = compute_score_edge_adjustment(
        prob_5=float(prob_5),
        alpha_score=float(alpha_score),
        whale_score=float(whale_score),
        position=str(position),
        strategy_tag=str(strategy_tag),
        volume_ratio=float(volume_ratio),
    )
    decision_score = round(
        (float(alpha_score) * 0.58 + float(whale_score) * 0.10 + float(prob_5) * 0.20 + float(prob_clean) * 0.12)
        + rank_adjustment_fn(
            real_trend,
            position,
            strategy_tag,
            tier,
            whale_score,
            float(volume_ratio),
            consec_days=consec_days,
        ),
        1,
    )
    decision_score = round(
        float(decision_score)
        + float(edge_adjustment.get("adjustment", 0.0) or 0.0)
        + float(profile_overlay["overlay"].get("score_adjustment", 0.0) or 0.0)
        + float(market_policy.get("score_adjustment", 0.0) or 0.0)
        + float(rank_overlay.get("score_adjustment", 0.0) or 0.0)
        - float(precision_gate.get("penalty", 0.0) or 0.0)
        + max(0.0, (float(conviction_score) - float(precision_gate.get("min_conviction", 0.0))) * 0.15),
        1,
    )
    theme_overlay = build_theme_overlay(
        sym=sym,
        stock_name=stock_name,
        market_type="KOSPI" if str(sym).upper().endswith(".KS") else "KOSDAQ",
        intel_data=intel_data if isinstance(intel_data, dict) else {},
        market_gate=str((market_gate or {}).get("gate", "GREEN")),
        df=qs.df,
        current_price=float(qs.df["Close"].iloc[-1] if qs.df is not None and not qs.df.empty else 0.0),
        volume_ratio=float(volume_ratio),
        decision_score=decision_score,
        scan_mode="SWING",
    )
    if theme_exception_strict or theme_precision_override:
        theme_overlay = _activate_theme_route(
            theme_overlay,
            "THEME_ROUTE_EXCEPTION_APPLIED" if theme_exception_strict else "THEME_ROUTE_PRECISION_OVERRIDE",
        )
    context_adjustment = compute_kr_context_adjustment(
        intel_data=intel_data if isinstance(intel_data, dict) else {},
        news_adj=news_adj,
        theme_overlay=theme_overlay,
        leader_signal=leader_signal,
        market_gate=str((market_gate or {}).get("gate", "GREEN")),
        real_trend=str(real_trend),
    )
    leader_metrics = theme_overlay.get("leader_metrics", {}) if isinstance(theme_overlay.get("leader_metrics"), dict) else {}
    leader_metrics = {
        **leader_metrics,
        "leader_score": round(max(float(leader_metrics.get("leader_score", 0.0) or 0.0), float(leader_signal.get("leader_score", 0.0) or 0.0)), 1),
        "breakout_quality_score": round(max(float(leader_metrics.get("breakout_quality_score", 0.0) or 0.0), float(leader_signal.get("breakout_quality_score", 0.0) or 0.0)), 1),
        "close_location_score": round(max(float(leader_metrics.get("close_location_score", 0.0) or 0.0), float(leader_signal.get("close_location_score", 0.0) or 0.0)), 1),
        "kr_flow_leader": bool(leader_signal.get("is_market_leader", False)),
        "kr_flow_leader_score": round(float(leader_signal.get("leader_score", 0.0) or 0.0), 1),
        "kr_turnover_ratio_20d": round(float(leader_signal.get("turnover_ratio_20d", 0.0) or 0.0), 3),
        "kr_volume_ratio": round(float(leader_signal.get("volume_ratio", 0.0) or 0.0), 3),
        "kr_flow_consensus_buying": bool(leader_signal.get("flow_consensus_buying", False)),
        "kr_retail_dominant": bool(leader_signal.get("retail_dominant", False)),
        "kr_whale_net_flow": round(float(leader_signal.get("whale_net_flow", 0.0) or 0.0), 1),
        "kr_foreign_flow": round(float(leader_signal.get("foreign_flow", 0.0) or 0.0), 1),
        "kr_institution_flow": round(float(leader_signal.get("institution_flow", 0.0) or 0.0), 1),
        "kr_retail_flow": round(float(leader_signal.get("retail_flow", 0.0) or 0.0), 1),
        "kr_context_adjustment": round(float(context_adjustment.get("adjustment", 0.0) or 0.0), 1),
        "kr_context_reasons": list(context_adjustment.get("reasons", []) or []),
        "kr_market_sentiment": str(context_adjustment.get("market_sentiment", "NEUTRAL")),
        "kr_theme_direction": str(context_adjustment.get("theme_direction", "NEUTRAL")),
        "kr_theme_strength_score": round(float(context_adjustment.get("theme_strength_score", 0.0) or 0.0), 1),
    }
    if context_adjustment.get("reasons"):
        theme_context_payload = theme_overlay.get("theme_context", {}) if isinstance(theme_overlay.get("theme_context"), dict) else {}
        theme_reasons = list(theme_context_payload.get("theme_reasons", []) or [])
        for reason in list(context_adjustment.get("reasons", []) or []):
            if reason not in theme_reasons:
                theme_reasons.append(reason)
        theme_context_payload["theme_reasons"] = theme_reasons[:12]
        theme_context_payload["market_sentiment"] = str(context_adjustment.get("market_sentiment", "NEUTRAL"))
        theme_context_payload["context_score_adjustment"] = round(float(context_adjustment.get("adjustment", 0.0) or 0.0), 1)
        theme_overlay["theme_context"] = theme_context_payload
    if float(context_adjustment.get("adjustment", 0.0) or 0.0) >= 3.5:
        strategy_tag = f"{strategy_tag} | ContextTailwind"
    elif float(context_adjustment.get("adjustment", 0.0) or 0.0) <= -3.5:
        strategy_tag = f"{strategy_tag} | ContextRisk"
    decision_score = round(
        _clamp_float(
            float(decision_score)
            + float(theme_overlay.get("score_adjustment", 0.0) or 0.0)
            + float(context_adjustment.get("adjustment", 0.0) or 0.0),
            0.0,
            100.0,
        ),
        1,
    )
    expected_edge = compute_expected_edge_profile(
        prob_5=float(prob_5),
        prob_clean=float(prob_clean),
        decision_score=float(decision_score),
        conviction_score=float(conviction_score),
        real_trend=str(real_trend),
        routing_path=str(theme_overlay.get("routing_path", "core_only") or "core_only"),
        scan_mode="SWING",
        market_gate=str((market_gate or {}).get("gate", "GREEN")),
        theme_context=theme_overlay.get("theme_context", {}),
    )

    outputs = build_kr_scan_outputs(
        sym=sym,
        stock_name=stock_name,
        alpha_score=float(alpha_score),
        whale_score=float(whale_score),
        whale_trend=str(whale_data.get("whale_trend", "")),
        real_trend=str(real_trend),
        prev_pct_change=float(prev_pct_change),
        consec_days=int(consec_days),
        setup=setup,
        news_tag=str(news_tag),
        strategy_tag=str(strategy_tag),
        surge_tag=str(surge_tag),
        wr=float(wr),
        position=str(position),
        prob_5=float(prob_5),
        prob_clean=float(prob_clean),
        decision_score=float(decision_score),
        conviction_score=float(conviction_score),
        tier=str(tier),
        tier_sort=int(tier_sort),
        tech_score=int(tech_score),
        fund_ok=bool(fund_ok),
        m_type=str(m_type),
        verdict_label=str(verdict_label),
        market_gate=str((market_gate or {}).get("gate", "GREEN")),
        kospi_chg=float((market_gate or {}).get("kospi_chg", 0.0)),
        phase25_prob=ml_pred.get("phase25_prob"),
        phase25_variant=ml_pred.get("phase25_variant"),
        phase25_shadow_variant=ml_pred.get("phase25_shadow_variant"),
        phase25_shadow_prob=ml_pred.get("phase25_shadow_prob"),
        phase25_recommended_threshold=ml_pred.get("phase25_recommended_threshold"),
        model_trace_status=ml_pred.get("model_trace_status"),
        model_error=ml_pred.get("model_error"),
        theme_context=theme_overlay.get("theme_context", {}),
        leader_metrics=leader_metrics,
        routing_path=theme_overlay.get("routing_path", "core_only"),
        theme_score_adjustment=theme_overlay.get("score_adjustment", 0.0),
        expected_edge_score=expected_edge.get("expected_edge_score"),
        expected_return_1d_pct=expected_edge.get("expected_return_1d_pct"),
        expected_return_3d_pct=expected_edge.get("expected_return_3d_pct"),
        scan_mode="SWING",
        strategy_family=getattr(qs, "strategy_family", None) or resolve_strategy_family(m_type),
    )
    return outputs
