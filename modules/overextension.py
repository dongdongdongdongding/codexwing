"""Reconstruct entry-time overextension (RSI14 + distance-from-20D-high) from price.

Why this exists
---------------
Exception Leader candidates are FEATURE_MISSING (``position``/``tech_score`` absent), so the
scanner's peak guards (``is_peak``/``EDGE_PEAK_ENTRY_RISK``/``chase_risk_level``), which all key
off ``position``, are *blind* to that stream. RSI and distance-from-high need only OHLCV, which is
always available, so we reconstruct them here and the promotion path can apply a peak-chase guard.

Validated 2026-06-15 (Exception Leader KOSPI SWING, n=139, forward 5D, bootstrap CI; see
docs/research/RESEARCH_LOG.md Step 1): overextension ALONE is not a clean signal, but the
COMBINATION at-high (dist_from_high_20d >= -3%) AND overheated (RSI14 >= 65) degrades the forward
outcome to win 55.6% / avg +2.65% vs 81% / +8.74% for everything else (an upside collapse, not a
tail blow-up). The guard therefore fires ONLY on the combination, and fails OPEN on missing data.

The RSI here is the simple rolling-mean RSI used in that validation (so the >=65 threshold stays
consistent with the slice that justified it), not the scanner's Wilder ``ta.rsi``.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

import pandas as pd


def rsi14_rolling(close: pd.Series, n: int = 14) -> Optional[float]:
    """Simple rolling-mean RSI(14), last value. None if insufficient/degenerate data."""
    if close is None or len(close) < n + 1:
        return None
    delta = close.diff()
    up = delta.clip(lower=0).rolling(n).mean()
    down = (-delta.clip(upper=0)).rolling(n).mean()
    last_up, last_down = up.iloc[-1], down.iloc[-1]
    if pd.isna(last_up) or pd.isna(last_down):
        return None
    if last_down == 0:
        return 100.0
    rs = last_up / last_down
    return float(100.0 - 100.0 / (1.0 + rs))


def peak_chase_verdict(
    rsi14: Optional[float],
    dist_from_high_20d: Optional[float],
    *,
    rsi_min: float = 65.0,
    dist_max: float = -3.0,
) -> bool:
    """True only for the validated peak-chase combination: at-high AND overheated.

    Fails OPEN (returns False) on missing inputs so the guard never suppresses on uncertainty.
    """
    if rsi14 is None or dist_from_high_20d is None:
        return False
    return bool(rsi14 >= rsi_min and dist_from_high_20d >= dist_max)


def compute_overextension(ticker: str, *, period: str = "3mo") -> Dict[str, Any]:
    """Reconstruct overextension for a ticker from price.

    Returns ``{rsi14, dist_from_high_20d, peak_chase, ok}``. ``ok=False`` (and peak_chase=False)
    when price is unavailable — the caller should treat that as "no guard action" (fail open).
    """
    out: Dict[str, Any] = {"rsi14": None, "dist_from_high_20d": None, "peak_chase": False, "ok": False}
    try:
        from modules.market_data import get_history
        df = get_history(str(ticker), period=period, interval="1d")
    except Exception:
        return out
    if df is None or getattr(df, "empty", True) or "Close" not in df.columns:
        return out
    close = pd.to_numeric(df["Close"], errors="coerce").dropna()
    high = pd.to_numeric(df.get("High", df["Close"]), errors="coerce").dropna()
    if len(close) < 16:
        return out
    rsi = rsi14_rolling(close)
    hi20 = float(high.iloc[-20:].max()) if len(high) else None
    cur = float(close.iloc[-1])
    dist = (cur / hi20 - 1.0) * 100.0 if hi20 else None
    rsi_min = float(os.getenv("AG_PEAKCHASE_RSI_MIN", "65"))
    dist_max = float(os.getenv("AG_PEAKCHASE_DIST_MAX", "-3"))
    out.update({
        "rsi14": rsi,
        "dist_from_high_20d": dist,
        "peak_chase": peak_chase_verdict(rsi, dist, rsi_min=rsi_min, dist_max=dist_max),
        "ok": True,
    })
    return out
