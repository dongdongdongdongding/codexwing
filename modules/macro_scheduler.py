"""
Phase 19: Real-Time Macro Scheduler Engine
Fetches VIX, TNX, KRW, SPY every call (with short-lived cache) and returns
a single macro_context dict that the scanner can use to overlay/penalize scores.
"""

import time
from modules.market_data import get_history
from modules.live_scan_context import context_ttl_seconds, normalize_market_key

# ─────────────────────────────────────────────────────────
# Simple In-Memory Cache  (TTL = 10 minutes)
# ─────────────────────────────────────────────────────────
_macro_cache: dict = {}
_macro_cache_ts: dict = {}
CACHE_TTL_SECONDS = 600  # closed-market fallback


def _fetch_change(ticker: str, period: str = "5d") -> tuple:
    """Returns (latest_value, 1d_pct_change). Returns (None, 0) on failure."""
    try:
        hist = get_history(ticker, period=period, interval="1d")
        if len(hist) < 2:
            return None, 0.0
        latest = float(hist["Close"].iloc[-1])
        prev   = float(hist["Close"].iloc[-2])
        chg    = (latest - prev) / prev * 100 if prev != 0 else 0.0
        return latest, chg
    except Exception:
        return None, 0.0


def _fetch_first_change(candidates: list[str], period: str = "5d") -> tuple:
    """Return (symbol, latest_value, 1d_pct_change) for the first usable source."""
    for ticker in candidates:
        latest, change = _fetch_change(ticker, period=period)
        if latest is not None:
            return ticker, latest, change
    return None, None, 0.0


def _safe_change(value) -> float:
    try:
        if value is None:
            return 0.0
        out = float(value)
        if out != out:
            return 0.0
        return out
    except Exception:
        return 0.0


def _compute_us_lead_score(
    *,
    market_group: str,
    qqq_chg: float,
    ixic_chg: float,
    nq_chg: float,
    es_chg: float,
    soxx_chg: float,
    ewy_chg: float,
    koru_chg: float,
) -> tuple[float, str, list]:
    """KR-focused overnight/live US lead score.

    Positive values are supportive, negative values are risk-off. KOSDAQ gets
    more sensitivity to Nasdaq/SOX, KOSPI gets more weight on broad beta/EWY.
    """
    key = str(market_group or "KR").upper()
    nasdaq_cash = qqq_chg if abs(qqq_chg) > 0 else ixic_chg
    korea_beta = ewy_chg
    if abs(korea_beta) < 0.01 and abs(koru_chg) > 0:
        korea_beta = koru_chg / 3.0

    if key == "KOSDAQ":
        score = (
            nasdaq_cash * 5.5
            + nq_chg * 5.0
            + soxx_chg * 4.5
            + es_chg * 2.0
            + korea_beta * 2.0
        )
    elif key == "KOSPI":
        score = (
            nasdaq_cash * 3.0
            + nq_chg * 2.5
            + soxx_chg * 2.0
            + es_chg * 3.5
            + korea_beta * 4.0
        )
    else:
        score = (
            nasdaq_cash * 4.0
            + nq_chg * 3.5
            + soxx_chg * 3.0
            + es_chg * 3.0
            + korea_beta * 3.0
        )

    flags = []
    if nasdaq_cash <= -1.5 or nq_chg <= -1.2:
        flags.append("NASDAQ_LEAD_WEAK")
    elif nasdaq_cash >= 1.2 or nq_chg >= 1.0:
        flags.append("NASDAQ_LEAD_STRONG")
    if soxx_chg <= -2.0:
        flags.append("SOX_LEAD_WEAK")
    elif soxx_chg >= 1.8:
        flags.append("SOX_LEAD_STRONG")
    if korea_beta <= -1.5:
        flags.append("KOREA_BETA_WEAK")
    elif korea_beta >= 1.2:
        flags.append("KOREA_BETA_STRONG")

    if score <= -22:
        state = "RISK_OFF"
    elif score <= -8:
        state = "CAUTION"
    elif score >= 14:
        state = "TAILWIND"
    else:
        state = "NEUTRAL"
    return round(float(score), 2), state, flags


def _compute_kr_derivative_lead_score(
    *,
    market_group: str,
    kospi200_chg: float,
    kodex200_chg: float,
) -> tuple[float, str, list]:
    """Domestic KR beta/derivative lead from direct KOSPI200 and ETF proxy.

    A stable direct night-futures API is not available in this runtime; the
    scanner records source status separately and uses the most stable direct
    KOSPI200 + KODEX200 proxy pair instead of a brittle web scraper.
    """
    key = str(market_group or "KR").upper()
    if abs(kospi200_chg) < 0.01 and abs(kodex200_chg) < 0.01:
        return 0.0, "NEUTRAL", []
    if key == "KOSDAQ":
        score = kospi200_chg * 1.5 + kodex200_chg * 1.0
    elif key == "KOSPI":
        score = kospi200_chg * 4.0 + kodex200_chg * 2.0
    else:
        score = kospi200_chg * 3.0 + kodex200_chg * 1.5

    flags = []
    if kospi200_chg <= -1.2 or kodex200_chg <= -1.2:
        flags.append("KR_DERIVATIVE_LEAD_WEAK")
    elif kospi200_chg >= 1.0 or kodex200_chg >= 1.0:
        flags.append("KR_DERIVATIVE_LEAD_STRONG")

    if score <= -8:
        state = "RISK_OFF"
    elif score <= -3:
        state = "CAUTION"
    elif score >= 6:
        state = "TAILWIND"
    else:
        state = "NEUTRAL"
    return round(float(score), 2), state, flags


def get_macro_context(force_refresh: bool = False, market_group: str = "KR") -> dict:
    """
    Returns current macro environment dict. Cached for 10 minutes.

    Keys:
        macro_state      : "NORMAL" | "CAUTION" | "RISK_OFF" | "CRASH"
        macro_risk_score : 0–100
        macro_multiplier : 0.65–1.0   (multiply Clean Hit P and base Decision)
        macro_penalty    : 0–15       (subtract from final Decision Score)
        flags            : list of active risk flags
        vix              : current VIX level
        vix_change_1d    : 1-day % change in VIX
        tnx              : 10Y yield
        tnx_change_1d    : 1-day change in TNX
        krw              : USD/KRW rate (None if unavailable)
        krw_change_1d    : 1-day % change in KRW
        spy_change_1d    : 1-day % change in SPY (market breadth proxy)
    """
    global _macro_cache, _macro_cache_ts

    now = time.time()
    market_key = normalize_market_key(market_group)
    ttl_seconds = context_ttl_seconds(market_key, open_seconds=180, closed_seconds=CACHE_TTL_SECONDS)
    if not force_refresh and market_key in _macro_cache and (now - float(_macro_cache_ts.get(market_key, 0.0))) < ttl_seconds:
        return _macro_cache[market_key]

    # ── Fetch ──────────────────────────────────────────
    vix,  vix_chg  = _fetch_change("^VIX")
    tnx,  tnx_chg  = _fetch_change("^TNX")
    krw,  krw_chg  = _fetch_change("KRW=X")
    spy,  spy_chg  = _fetch_change("SPY")
    ixic, ixic_chg = _fetch_change("^IXIC")
    qqq, qqq_chg = _fetch_change("QQQ")
    nq_fut, nq_fut_chg = _fetch_change("NQ=F")
    es_fut, es_fut_chg = _fetch_change("ES=F")
    soxx, soxx_chg = _fetch_change("SOXX")
    ewy, ewy_chg = _fetch_change("EWY")
    koru, koru_chg = _fetch_change("KORU")
    kospi200_symbol, kospi200, kospi200_chg = _fetch_first_change(["KS200", "^KS200"])
    kodex200_symbol, kodex200, kodex200_chg = _fetch_first_change(["069500.KS"])
    us_lead_score, us_lead_state, us_lead_flags = _compute_us_lead_score(
        market_group=market_key,
        qqq_chg=_safe_change(qqq_chg),
        ixic_chg=_safe_change(ixic_chg),
        nq_chg=_safe_change(nq_fut_chg),
        es_chg=_safe_change(es_fut_chg),
        soxx_chg=_safe_change(soxx_chg),
        ewy_chg=_safe_change(ewy_chg),
        koru_chg=_safe_change(koru_chg),
    )
    kr_derivative_lead_score, kr_derivative_lead_state, kr_derivative_lead_flags = _compute_kr_derivative_lead_score(
        market_group=market_key,
        kospi200_chg=_safe_change(kospi200_chg),
        kodex200_chg=_safe_change(kodex200_chg),
    )

    # ── Risk Score Calculation ──────────────────────────
    risk_score = 0
    flags = []

    # VIX level
    if vix is not None:
        if vix > 35:
            risk_score += 40; flags.append("VIX_EXTREME")
        elif vix > 25:
            risk_score += 25; flags.append("VIX_HIGH")
        elif vix > 20:
            risk_score += 10; flags.append("VIX_ELEVATED")

    # VIX spike (1-day surge)
    if abs(vix_chg) > 0:
        if vix_chg >= 25:
            risk_score += 25; flags.append("VIX_SPIKE_SEVERE")
        elif vix_chg >= 15:
            risk_score += 15; flags.append("VIX_SPIKE")
        elif vix_chg >= 8:
            risk_score += 5;  flags.append("VIX_RISING")

    # 10Y Yield surge
    if tnx_chg >= 3:
        risk_score += 15; flags.append("YIELD_SURGE")
    elif tnx_chg >= 1.5:
        risk_score += 8;  flags.append("YIELD_RISING")

    # KRW weakness (USD buying; bad for KOSPI)
    if krw is not None and krw_chg >= 1.0:
        risk_score += 10; flags.append("KRW_WEAKNESS")
    elif krw is not None and krw_chg >= 0.5:
        risk_score += 5;  flags.append("KRW_SOFTENING")

    # SPY gap-down
    if spy_chg <= -2.0:
        risk_score += 15; flags.append("GAP_DOWN_SEVERE")
    elif spy_chg <= -1.0:
        risk_score += 8;  flags.append("GAP_DOWN")

    # US lead pressure for KR open/session scans.
    if market_key in {"KR", "KOSPI", "KOSDAQ"}:
        if us_lead_score <= -22:
            risk_score += 12; flags.append("US_LEAD_RISK_OFF")
        elif us_lead_score <= -8:
            risk_score += 6; flags.append("US_LEAD_CAUTION")
        if kr_derivative_lead_score <= -8:
            risk_score += 10; flags.append("KR_DERIVATIVE_LEAD_RISK_OFF")
        elif kr_derivative_lead_score <= -3:
            risk_score += 5; flags.append("KR_DERIVATIVE_LEAD_CAUTION")
        flags.extend([flag for flag in us_lead_flags if flag not in flags])
        flags.extend([flag for flag in kr_derivative_lead_flags if flag not in flags])

    risk_score = min(risk_score, 100)

    # ── State Classification ────────────────────────────
    if risk_score >= 80:
        macro_state = "CRASH"
        macro_multiplier = 0.55
        macro_penalty = 15
    elif risk_score >= 60:
        macro_state = "RISK_OFF"
        macro_multiplier = 0.70
        macro_penalty = 10
    elif risk_score >= 35:
        macro_state = "CAUTION"
        macro_multiplier = 0.85
        macro_penalty = 5
    else:
        macro_state = "NORMAL"
        macro_multiplier = 1.0
        macro_penalty = 0

    _macro_cache[market_key] = {
        "macro_state":      macro_state,
        "macro_risk_score": risk_score,
        "macro_multiplier": macro_multiplier,
        "macro_penalty":    macro_penalty,
        "flags":            flags,
        "vix":              vix,
        "vix_change_1d":    round(vix_chg, 2),
        "tnx":              tnx,
        "tnx_change_1d":    round(tnx_chg, 2),
        "krw":              krw,
        "krw_change_1d":    round(krw_chg, 2),
        "spy_change_1d":    round(spy_chg, 2),
        "ixic_change_1d":   round(ixic_chg, 2),
        "qqq_change_1d":    round(qqq_chg, 2),
        "nq_futures":       nq_fut,
        "nq_futures_change_1d": round(nq_fut_chg, 2),
        "es_futures":       es_fut,
        "es_futures_change_1d": round(es_fut_chg, 2),
        "soxx_change_1d":   round(soxx_chg, 2),
        "ewy_change_1d":    round(ewy_chg, 2),
        "koru_change_1d":   round(koru_chg, 2),
        "kospi200_source":  kospi200_symbol,
        "kospi200":         kospi200,
        "kospi200_change_1d": round(kospi200_chg, 2),
        "kodex200_source":  kodex200_symbol,
        "kodex200":         kodex200,
        "kodex200_change_1d": round(kodex200_chg, 2),
        "kr_night_futures_source_status": "unavailable_stable_api_using_kospi200_kodex200_proxy",
        "kr_derivative_lead_score": kr_derivative_lead_score,
        "kr_derivative_lead_state": kr_derivative_lead_state,
        "kr_derivative_lead_flags": kr_derivative_lead_flags,
        "us_lead_score":    us_lead_score,
        "us_lead_state":    us_lead_state,
        "us_lead_flags":    us_lead_flags,
    }
    _macro_cache_ts[market_key] = now
    return _macro_cache[market_key]


def macro_weather_text(ctx: dict) -> str:
    """Returns a single-line human-readable weather summary for the UI."""
    state = ctx.get("macro_state", "NORMAL")
    icon_map = {
        "NORMAL":   "☀️",
        "CAUTION":  "⛅",
        "RISK_OFF": "🌧️",
        "CRASH":    "🚨",
    }
    vix  = ctx.get("vix")
    tnx  = ctx.get("tnx")
    krw  = ctx.get("krw")
    spy  = ctx.get("spy_change_1d", 0)
    qqq  = ctx.get("qqq_change_1d", 0)
    nq   = ctx.get("nq_futures_change_1d", 0)
    ewy  = ctx.get("ewy_change_1d", 0)
    ks200 = ctx.get("kospi200_change_1d", 0)
    flags = ctx.get("flags", [])

    icon  = icon_map.get(state, "☀️")
    parts = [f"{icon} **{state}** (Risk Score {ctx.get('macro_risk_score', 0)})"]
    if vix  is not None: parts.append(f"VIX {vix:.1f} ({ctx['vix_change_1d']:+.1f}%)")
    if tnx  is not None: parts.append(f"10Y {tnx:.2f}% ({ctx['tnx_change_1d']:+.2f}bps)")
    if krw  is not None: parts.append(f"KRW {krw:,.0f} ({ctx['krw_change_1d']:+.2f}%)")
    parts.append(f"SPY {spy:+.2f}%")
    parts.append(f"QQQ {qqq:+.2f}%")
    parts.append(f"NQ {nq:+.2f}%")
    parts.append(f"EWY {ewy:+.2f}%")
    parts.append(f"KS200 {ks200:+.2f}%")
    if flags:
        parts.append(f"| ⚠️ {', '.join(flags)}")

    return "  ".join(parts)


if __name__ == "__main__":
    ctx = get_macro_context(force_refresh=True)
    print(macro_weather_text(ctx))
    print("\nFull context:", ctx)
