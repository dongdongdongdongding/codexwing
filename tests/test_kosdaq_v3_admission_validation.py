from modules.kosdaq_v3_admission_validation import (
    build_kosdaq_v3_admission_validation_report,
    is_kosdaq_v3_admission_row,
    is_kosdaq_v3_floor_row,
)


def _row(**overrides):
    base = {
        "ticker": "123456.KQ",
        "stock_name": "테스트",
        "market": "KOSDAQ",
        "scan_mode": "SWING",
        "priority_rank": "1",
        "decision": "WATCHLIST_ONLY",
        "relative_rank_model": "kosdaq_floor_win_relative_v5",
        "rationale": "['kosdaq_relative_admission_floor:no_tradeable_candidate']",
        "theme_risk": "['KOSDAQ_RELATIVE_ADMISSION_FLOOR']",
        "base_trade_date": "2026-05-12",
        "return_1d_pct": "1.0",
        "return_3d_pct": "2.0",
        "return_5d_pct": "6.0",
        "return_7d_pct": "8.0",
        "return_14d_pct": "10.0",
        "return_30d_pct": "12.0",
    }
    base.update(overrides)
    return base


def test_kosdaq_v3_admission_row_detects_model_or_floor_trace():
    assert is_kosdaq_v3_admission_row(_row()) is True
    assert is_kosdaq_v3_floor_row(_row()) is True
    assert is_kosdaq_v3_admission_row(_row(relative_rank_model="", rationale="", theme_risk="")) is False
    assert is_kosdaq_v3_admission_row(_row(market="KOSPI", ticker="123456.KS")) is False
    assert is_kosdaq_v3_admission_row(_row(scan_mode="INTRADAY")) is False


def test_report_tracks_rank1_top5_horizons_and_baseline_verdict():
    rows = [
        _row(ticker="A.KQ", priority_rank="1", return_5d_pct="6.0"),
        _row(ticker="B.KQ", priority_rank="2", return_5d_pct="-7.0"),
        _row(ticker="C.KQ", priority_rank="6", return_5d_pct="3.0"),
        _row(ticker="OLD.KQ", relative_rank_model="", rationale="", theme_risk="", return_5d_pct="30.0"),
    ]

    report = build_kosdaq_v3_admission_validation_report(
        rows,
        as_of_date="2026-05-19",
        generated_at="now",
        min_matured_5d=3,
    )

    assert report["source"]["v3_rows"] == 3
    assert report["source"]["v3_relative_floor_rows"] == 3
    assert report["groups"]["v3_rank1"]["5d"]["sample_n"] == 1
    assert report["groups"]["v3_top5"]["5d"]["sample_n"] == 2
    assert report["groups"]["v3_top5"]["5d"]["worst_return_pct"] == -7.0
    assert report["groups"]["v3_top5"]["5d"]["loss5_rate_pct"] == 50.0
    assert report["policy_verdict"]["status"] == "insufficient_sample"
