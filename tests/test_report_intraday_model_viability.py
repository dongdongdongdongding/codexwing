from __future__ import annotations

import numpy as np
import pandas as pd

from multi_agent.tools.report_intraday_model_viability import (
    _derive_market_subtype,
    _promotion_gate,
    _threshold_sweep,
)


def test_derive_market_subtype_prefers_kr_ticker_suffix() -> None:
    df = pd.DataFrame(
        [
            {"ticker": "000001.KS", "market": "", "market_type": "KR"},
            {"ticker": "000002.KQ", "market": "", "market_type": "KR"},
            {"ticker": "ABC", "market": "KOSDAQ", "market_type": "KR"},
        ]
    )

    assert _derive_market_subtype(df).tolist() == ["KOSPI", "KOSDAQ", "KOSDAQ"]


def test_threshold_sweep_reports_min_and_max_return() -> None:
    prob = np.array([0.9, 0.85, 0.2, 0.1])
    returns = np.array([3.0, -2.0, 5.0, -1.0])
    target = np.array([1, 0, 1, 0])

    rows, best = _threshold_sweep(prob, returns, target)

    first = next(row for row in rows if row["threshold"] == 0.5)
    assert first["picks"] == 2
    assert first["min_pct"] == -2.0
    assert first["max_pct"] == 3.0
    assert best is None


def test_promotion_gate_requires_auc_win_avg_and_loss_floor() -> None:
    gate = _promotion_gate(
        {
            "auc": 0.57,
            "best_threshold_row": {
                "win_pct": 72.0,
                "avg_pct": 2.0,
                "min_pct": -4.9,
            },
        }
    )

    assert gate["pass"] is True

    failed = _promotion_gate(
        {
            "auc": 0.55,
            "best_threshold_row": {
                "win_pct": 72.0,
                "avg_pct": 2.0,
                "min_pct": -8.0,
            },
        }
    )

    assert failed["pass"] is False
    assert "auc_below_0.56" in failed["reasons"]
    assert "min_loss_below_-5.0" in failed["reasons"]
