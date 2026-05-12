from datetime import date

import pandas as pd

from multi_agent.tools.update_outcome_return_metrics import _compute_row_returns


def _hist(closes, highs):
    return pd.DataFrame(
        {
            "Close": closes,
            "High": highs,
            "trade_date": [date(2026, 5, 1 + i) for i in range(len(closes))],
        }
    )


def test_compute_row_returns_marks_forward_high_5d_touch():
    row = {
        "ticker": "005930.KS",
        "scan_mode": "SWING",
        "recommended_at": "2026-05-01T09:00:00+09:00",
    }
    hist = _hist(
        closes=[100, 101, 102, 103, 104, 102, 101],
        highs=[101, 102, 104, 106, 103, 102, 101],
    )

    assert _compute_row_returns(row, hist, "KOSPI") is True

    assert row["return_5d_pct"] == 2.0
    assert row["max_high_return_5d_pct"] == 6.0
    assert row["hit_5pct_within_5d"] is True
    assert row["hit_5pct_within_5d_at"] == "2026-05-04"
    assert row["swing_target_label_version"] == "forward_high_within_5d_v1"


def test_compute_row_returns_does_not_false_label_immature_5d_window():
    row = {
        "ticker": "005930.KS",
        "scan_mode": "SWING",
        "recommended_at": "2026-05-01T09:00:00+09:00",
    }
    hist = _hist(
        closes=[100, 101, 102],
        highs=[101, 107, 102],
    )

    assert _compute_row_returns(row, hist, "KOSPI") is True

    assert row.get("return_5d_pct") is None
    assert row["max_high_return_5d_pct"] is None
    assert row["hit_5pct_within_5d"] is None
    assert row["hit_5pct_within_5d_at"] is None
    assert row["swing_target_label_version"] is None


def test_compute_row_returns_marks_mature_non_touch_as_false():
    row = {
        "ticker": "005930.KS",
        "scan_mode": "SWING",
        "recommended_at": "2026-05-01T09:00:00+09:00",
    }
    hist = _hist(
        closes=[100, 101, 102, 103, 104, 104, 103],
        highs=[101, 102, 103, 104, 104.5, 104.9, 103],
    )

    assert _compute_row_returns(row, hist, "KOSPI") is True

    assert row["max_high_return_5d_pct"] == 4.9
    assert row["hit_5pct_within_5d"] is False
    assert row["hit_5pct_within_5d_at"] is None
    assert row["swing_target_label_version"] == "forward_high_within_5d_v1"
