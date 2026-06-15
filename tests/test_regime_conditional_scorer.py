"""Unit tests for the regime-conditional price scorer (network-free).

Locks the validated factor-sign-by-regime rule: momentum (above-60D-MA) in up-trends,
oversold-reversal (below-20D-high) in down/chop.
"""
import numpy as np
import pandas as pd

from modules.regime_conditional_scorer import compute_regime_score, index_regime_up


def _series(vals):
    return pd.Series(vals, dtype="float")


def test_index_regime_up_and_down():
    rising = _series(list(range(1, 60)))          # clearly above its MA
    falling = _series(list(range(60, 1, -1)))     # clearly below its MA
    assert index_regime_up(rising) is True
    assert index_regime_up(falling) is False


def test_up_regime_uses_momentum_factor():
    close = _series([100 + i for i in range(80)])   # uptrend, above 60D MA
    high = close * 1.01
    idx = _series(list(range(1, 80)))               # index up-regime
    r = compute_regime_score(close, high, idx)
    assert r["ok"] and r["regime"] == "up"
    assert r["factor"] == "ma60_dist"
    assert r["score"] == r["ma60_dist"]              # higher above MA60 -> higher score
    assert r["score"] > 0


def test_down_regime_uses_oversold_reversal_factor():
    # stock pulled well below its 20D high; index in down regime
    close = _series([100 + i for i in range(60)] + [160 - 4 * i for i in range(20)])
    high = _series([100 + i for i in range(60)] + [160 for _ in range(20)])
    idx = _series(list(range(80, 0, -1)))            # index down-regime
    r = compute_regime_score(close, high, idx)
    assert r["ok"] and r["regime"] == "down_chop"
    assert r["factor"] == "dist_hi20_oversold"
    # more oversold (more negative dist_hi20) -> higher score
    assert r["score"] == -r["dist_hi20"]
    assert r["score"] > 0


def test_insufficient_data_fails_safe():
    short = _series([1, 2, 3])
    r = compute_regime_score(short, short, short)
    assert r["ok"] is False
