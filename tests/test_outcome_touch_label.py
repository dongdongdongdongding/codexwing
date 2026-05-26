from datetime import date

import json
import pandas as pd

from multi_agent.tools import update_outcome_return_metrics as outcome_metrics
from multi_agent.tools.update_outcome_return_metrics import (
    _compute_intraday_row_returns,
    _compute_path_risk_labels,
    _compute_row_returns,
)


def _hist(closes, highs, lows=None):
    low_values = lows if lows is not None else highs
    return pd.DataFrame(
        {
            "Close": closes,
            "High": highs,
            "Low": low_values,
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


def test_compute_intraday_returns_applies_to_swing_rows(monkeypatch):
    row = {
        "ticker": "005930.KS",
        "scan_mode": "SWING",
        "recommended_at": "2026-05-01T09:40:00+09:00",
        "entry_reference_price": 100.0,
    }
    idx = pd.DatetimeIndex(
        [
            "2026-05-01T09:30:00+09:00",
            "2026-05-01T10:00:00+09:00",
            "2026-05-01T10:30:00+09:00",
            "2026-05-01T15:00:00+09:00",
        ]
    )
    hist = pd.DataFrame(
        {
            "Close": [99.0, 103.0, 104.0, 105.0],
            "High": [101.0, 104.0, 105.0, 106.0],
            "Low": [98.0, 102.0, 103.0, 104.0],
        },
        index=idx,
    )

    monkeypatch.setattr(outcome_metrics, "_fetch_intraday_history", lambda *args, **kwargs: hist)

    assert _compute_intraday_row_returns(row, "KOSPI") is True

    assert row["return_10m_pct"] == -1.0
    assert row["return_30m_pct"] == 3.0
    assert row["return_1h_pct"] == 4.0
    assert row["return_close_pct"] == 5.0
    assert row["mfe_intraday_pct"] == 6.0
    assert row["mae_intraday_pct"] == -2.0


def test_daily_return_update_preserves_scan_entry_for_intraday_path(monkeypatch):
    row = {
        "ticker": "005930.KS",
        "scan_mode": "SWING",
        "recommended_at": "2026-05-01T09:40:00+09:00",
        "entry_reference_price": 98.0,
    }
    hist = _hist(closes=[100, 101, 102], highs=[101, 102, 103])
    idx = pd.DatetimeIndex(["2026-05-01T10:00:00+09:00", "2026-05-01T15:00:00+09:00"])
    intraday = pd.DataFrame({"Close": [99.0, 100.0], "High": [100.0, 101.0], "Low": [98.5, 99.0]}, index=idx)

    monkeypatch.setattr(outcome_metrics, "_fetch_intraday_history", lambda *args, **kwargs: intraday)

    assert _compute_row_returns(row, hist, "KOSPI") is True
    assert row["entry_reference_price"] == 100.0
    assert row["scan_entry_reference_price"] == 98.0

    assert _compute_intraday_row_returns(row, "KOSPI") is True
    assert row["return_30m_pct"] == 1.020408
    assert row["return_close_pct"] == 2.040816


def test_run_update_fills_intraday_even_when_daily_history_missing(tmp_path, monkeypatch):
    shared = tmp_path / "shared_working"
    run_dir = shared / "RUN-TEST"
    run_dir.mkdir(parents=True)
    (run_dir / "scanner_handoff.json").write_text(
        json.dumps(
            {
                "run_context": {"market": "KOSPI"},
                "summary": {"input_meta": {"scan_mode": "SWING"}},
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "realized_outcomes.json").write_text(
        json.dumps(
            {
                "outcomes": [
                    {
                        "ticker": "005930.KS",
                        "market": "KOSPI",
                        "scan_mode": "SWING",
                        "recommended_at": "2026-05-01T09:40:00+09:00",
                        "entry_reference_price": 100.0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    idx = pd.DatetimeIndex(
        [
            "2026-05-01T10:00:00+09:00",
            "2026-05-01T10:30:00+09:00",
            "2026-05-01T15:00:00+09:00",
        ]
    )
    intraday = pd.DataFrame(
        {"Close": [103.0, 104.0, 105.0], "High": [104.0, 105.0, 106.0], "Low": [99.0, 102.0, 103.0]},
        index=idx,
    )

    class FakeDB:
        client = None

    monkeypatch.setattr(outcome_metrics, "_fetch_history", lambda *args, **kwargs: None)
    monkeypatch.setattr(outcome_metrics, "_fetch_intraday_history", lambda *args, **kwargs: intraday)
    monkeypatch.setattr("modules.db_manager.DBManager", FakeDB)

    stats = outcome_metrics.run_update(
        shared_dir=shared,
        run_ids=["RUN-TEST"],
        limit_runs=0,
        dry_run=False,
        scan_mode_filter="ALL",
    )

    updated = json.loads((run_dir / "realized_outcomes.json").read_text(encoding="utf-8"))["outcomes"][0]
    assert stats["rows_without_daily_history"] == 1
    assert stats["intraday_rows_attempted"] == 1
    assert stats["intraday_rows_updated"] == 1
    assert updated["return_30m_pct"] == 3.0
    assert updated["return_1h_pct"] == 4.0
    assert updated["return_close_pct"] == 5.0
    assert updated["return_10m_pct"] == 3.0


def test_run_update_recovers_scan_entry_from_top_deep_for_intraday(tmp_path, monkeypatch):
    shared = tmp_path / "shared_working"
    run_dir = shared / "RUN-TEST"
    run_dir.mkdir(parents=True)
    top_deep_dir = tmp_path / "runtime_state" / "reports" / "top_deep"
    top_deep_dir.mkdir(parents=True)
    (top_deep_dir / "RUN-TEST.json").write_text(
        json.dumps(
            [
                {
                    "ticker": "005930.KS",
                    "trade_plan": {"entry_reference_price": 95.0},
                }
            ]
        ),
        encoding="utf-8",
    )
    (run_dir / "scanner_handoff.json").write_text(
        json.dumps(
            {
                "run_context": {"market": "KOSPI"},
                "summary": {"input_meta": {"scan_mode": "SWING"}},
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "realized_outcomes.json").write_text(
        json.dumps(
            {
                "outcomes": [
                    {
                        "ticker": "005930.KS",
                        "market": "KOSPI",
                        "scan_mode": "SWING",
                        "recommended_at": "2026-05-01T09:40:00+09:00",
                        "entry_reference_price": 100.0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    idx = pd.DatetimeIndex(["2026-05-01T10:00:00+09:00", "2026-05-01T15:00:00+09:00"])
    intraday = pd.DataFrame({"Close": [105.0, 104.5], "High": [106.0, 105.0], "Low": [104.0, 103.0]}, index=idx)

    class FakeDB:
        client = None

    monkeypatch.setattr(outcome_metrics, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(outcome_metrics, "_fetch_history", lambda *args, **kwargs: None)
    monkeypatch.setattr(outcome_metrics, "_fetch_intraday_history", lambda *args, **kwargs: intraday)
    monkeypatch.setattr("modules.db_manager.DBManager", FakeDB)

    stats = outcome_metrics.run_update(
        shared_dir=shared,
        run_ids=["RUN-TEST"],
        limit_runs=0,
        dry_run=False,
        scan_mode_filter="ALL",
    )

    updated = json.loads((run_dir / "realized_outcomes.json").read_text(encoding="utf-8"))["outcomes"][0]
    assert stats["intraday_rows_updated"] == 1
    assert updated["entry_reference_price"] == 100.0
    assert updated["scan_entry_reference_price"] == 95.0
    assert updated["return_30m_pct"] == 10.526316
    assert updated["return_close_pct"] == 10.0


def test_compute_path_risk_labels_marks_stop_first_with_daily_ohlc():
    row = {
        "ticker": "005930.KS",
        "scan_mode": "SWING",
        "recommended_at": "2026-05-01T09:40:00+09:00",
        "scan_entry_reference_price": 100.0,
        "target_tp_pct": 5.0,
        "stop_sl_pct": -3.0,
    }
    hist = _hist(
        closes=[100, 99, 102, 104, 103, 101],
        highs=[101, 103, 106, 105, 104, 103],
        lows=[99, 96, 101, 102, 101, 100],
    )

    assert _compute_path_risk_labels(row, hist, "KOSPI") is True

    assert row["mfe_5d_pct"] == 6.0
    assert row["mae_5d_pct"] == -4.0
    assert row["target_before_stop_5d"] is False
    assert row["stop_before_target_5d"] is True
    assert row["stop_hit_at_5d"] == "2026-05-02"
    assert row["outcome_path_terminal_status"] == "stop_before_target"
    assert row["outcome_path_label_version"] == "scan_entry_forward_hybrid_30m_daily_stop_first_v2"


def test_compute_path_risk_labels_uses_post_scan_intraday_before_daily():
    row = {
        "ticker": "005930.KS",
        "scan_mode": "SWING",
        "recommended_at": "2026-05-01T09:40:00+09:00",
        "scan_entry_reference_price": 100.0,
        "target_tp_pct": 5.0,
        "stop_sl_pct": -3.0,
    }
    hist = _hist(
        closes=[100, 103, 104, 103, 102, 101],
        highs=[120, 106, 104, 103, 102, 101],
        lows=[80, 99, 100, 100, 100, 100],
    )
    idx = pd.DatetimeIndex(["2026-05-01T09:30:00+09:00", "2026-05-01T15:00:00+09:00"])
    intraday = pd.DataFrame(
        {"Close": [98.0, 99.0], "High": [101.0, 100.0], "Low": [96.0, 98.0]},
        index=idx,
    )

    assert _compute_path_risk_labels(row, hist, "KOSPI", intraday_hist=intraday) is True

    assert row["target_before_stop_5d"] is False
    assert row["stop_before_target_5d"] is True
    assert row["stop_hit_at_5d"] == "2026-05-01"
    assert row["ordered_stop_hit_at"] == "2026-05-01T10:00:00+09:00"
    assert row["mfe_5d_pct"] == 6.0
    assert row["mae_5d_pct"] == -4.0
    assert row["ordered_mfe_until_terminal_5d_pct"] == 1.0
    assert row["ordered_mae_until_terminal_5d_pct"] == -4.0
    assert row["outcome_path_source"] == "intraday_30m+daily_ohlc"
    assert "partial_intraday_bar_contains_pre_scan_range" in row["outcome_path_warnings"]


def test_compute_path_risk_labels_records_mae_before_target():
    row = {
        "ticker": "005930.KS",
        "scan_mode": "SWING",
        "recommended_at": "2026-05-01T09:40:00+09:00",
        "scan_entry_reference_price": 100.0,
        "target_tp_pct": 5.0,
        "stop_sl_pct": -5.0,
    }
    hist = _hist(
        closes=[100, 104, 103, 102, 101, 100],
        highs=[101, 104, 103, 102, 101, 100],
        lows=[99, 100, 100, 100, 100, 100],
    )
    idx = pd.DatetimeIndex(["2026-05-01T10:00:00+09:00"])
    intraday = pd.DataFrame(
        {"Close": [105.0], "High": [106.0], "Low": [99.0]},
        index=idx,
    )

    assert _compute_path_risk_labels(row, hist, "KOSPI", intraday_hist=intraday) is True

    assert row["target_before_stop_5d"] is True
    assert row["target_hit_at_5d"] == "2026-05-01"
    assert row["ordered_target_hit_at"] == "2026-05-01T10:30:00+09:00"
    assert row["ordered_mae_before_target_5d_pct"] == -1.0
    assert row["ordered_mfe_until_terminal_5d_pct"] == 6.0
