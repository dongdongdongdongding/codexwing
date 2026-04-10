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
_macro_cache_ts: float = 0.0
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
    ttl_seconds = context_ttl_seconds(normalize_market_key(market_group), open_seconds=180, closed_seconds=CACHE_TTL_SECONDS)
    if not force_refresh and _macro_cache and (now - _macro_cache_ts) < ttl_seconds:
        return _macro_cache

    # ── Fetch ──────────────────────────────────────────
    vix,  vix_chg  = _fetch_change("^VIX")
    tnx,  tnx_chg  = _fetch_change("^TNX")
    krw,  krw_chg  = _fetch_change("KRW=X")
    spy,  spy_chg  = _fetch_change("SPY")

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

    _macro_cache = {
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
    }
    _macro_cache_ts = now
    return _macro_cache


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
    flags = ctx.get("flags", [])

    icon  = icon_map.get(state, "☀️")
    parts = [f"{icon} **{state}** (Risk Score {ctx.get('macro_risk_score', 0)})"]
    if vix  is not None: parts.append(f"VIX {vix:.1f} ({ctx['vix_change_1d']:+.1f}%)")
    if tnx  is not None: parts.append(f"10Y {tnx:.2f}% ({ctx['tnx_change_1d']:+.2f}bps)")
    if krw  is not None: parts.append(f"KRW {krw:,.0f} ({ctx['krw_change_1d']:+.2f}%)")
    parts.append(f"SPY {spy:+.2f}%")
    if flags:
        parts.append(f"| ⚠️ {', '.join(flags)}")

    return "  ".join(parts)


if __name__ == "__main__":
    ctx = get_macro_context(force_refresh=True)
    print(macro_weather_text(ctx))
    print("\nFull context:", ctx)
