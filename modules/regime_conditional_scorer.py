"""Regime-conditional price-primitive scorer (validated 2026-06-15, multi-regime OOS).

Why this exists
---------------
The rich sidecar feature set is only ~1 month deep (one regime), so no model learned on it
survived OOS (it inverted). Reconstructing PRICE primitives from FDR over a 2.5yr multi-regime
panel removed that limit. Walk-forward verification (train 2024-03..2025-07 -> test 2025-07..
2026-06) showed a regime-conditional rule beats the per-day base OOS: top-decile 54.7% win /
net +2.54% vs base 52.5% / +1.27%, driven by the down/chop oversold-reversal leg (62.6% OOS win).

The factor SIGN flips with the market regime -- this is the structural insight that broke every
single-regime model:
  - UP-trend  (index > 20D MA): momentum  -> reward distance ABOVE the 60D MA (ma60_dist, +).
  - DOWN/chop (index <= 20D MA): reversal -> reward being OVERSOLD vs the 20D high (dist_hi20, -).

Price-derived only (OHLCV + the market index), so it works for any candidate and does not depend
on the sidecar. The edge is THIN (+~2pp win over base) with severe single-name tails (~-48%) ->
it MUST be paired with tail-aware sizing. This is a shadow signal until forward-tracked live.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd


def _ma_dist(close: pd.Series, n: int) -> Optional[float]:
    if close is None or len(close) < n:
        return None
    ma = close.rolling(n).mean().iloc[-1]
    cur = close.iloc[-1]
    if pd.isna(ma) or ma == 0:
        return None
    return float((cur / ma - 1.0) * 100.0)


def _dist_from_high(close: pd.Series, high: pd.Series, n: int) -> Optional[float]:
    if close is None or len(close) < n:
        return None
    hi = high.iloc[-n:].max()
    cur = close.iloc[-1]
    if pd.isna(hi) or hi == 0:
        return None
    return float((cur / hi - 1.0) * 100.0)


def index_regime_up(index_close: pd.Series, ma: int = 20) -> Optional[bool]:
    """True if the market index is above its `ma`-day MA at the most recent (prior) close."""
    if index_close is None or len(index_close) < ma:
        return None
    m = index_close.rolling(ma).mean().iloc[-1]
    cur = index_close.iloc[-1]
    if pd.isna(m):
        return None
    return bool(cur > m)


def compute_regime_score(
    close: pd.Series,
    high: pd.Series,
    index_close: pd.Series,
) -> Dict[str, Any]:
    """Regime-conditional score for one candidate. Higher = better. None on insufficient data.

    All inputs are series ending at the most recent CLOSE known at scan time (causal).
    """
    out: Dict[str, Any] = {"regime": None, "factor": None, "score": None,
                           "ma60_dist": None, "dist_hi20": None, "ok": False}
    up = index_regime_up(index_close)
    ma60 = _ma_dist(close, 60)
    dist20 = _dist_from_high(close, high, 20)
    out["ma60_dist"] = ma60
    out["dist_hi20"] = dist20
    if up is None:
        return out
    out["regime"] = "up" if up else "down_chop"
    if up:
        if ma60 is None:
            return out
        out["factor"] = "ma60_dist"      # momentum: further above 60D MA is better
        out["score"] = ma60
    else:
        if dist20 is None:
            return out
        out["factor"] = "dist_hi20_oversold"  # reversal: more below 20D high is better
        out["score"] = -dist20
    out["ok"] = True
    return out


def compute_regime_score_for_ticker(ticker: str, market: str, *, period: str = "6mo") -> Dict[str, Any]:
    """Fetch price + market index and compute the regime score. Fails safe (ok=False)."""
    index_code = "KS11" if str(market).upper() == "KOSPI" else "KQ11"
    try:
        from modules.market_data import get_history
        px = get_history(str(ticker), period=period, interval="1d")
        idx = get_history(index_code, period=period, interval="1d")
    except Exception:
        return {"ok": False}
    if px is None or getattr(px, "empty", True) or "Close" not in px.columns:
        return {"ok": False}
    if idx is None or getattr(idx, "empty", True) or "Close" not in idx.columns:
        return {"ok": False}
    close = pd.to_numeric(px["Close"], errors="coerce").dropna()
    high = pd.to_numeric(px.get("High", px["Close"]), errors="coerce").dropna()
    iclose = pd.to_numeric(idx["Close"], errors="coerce").dropna()
    return compute_regime_score(close, high, iclose)
