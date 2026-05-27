from __future__ import annotations

import pandas as pd

from multi_agent.tools.report_intraday_learning_readiness import build_report, load_intraday_rows


def test_load_intraday_rows_derives_kr_market_and_dates(tmp_path) -> None:
    path = tmp_path / "archive.csv"
    pd.DataFrame(
        [
            {
                "ticker": "000001.KS",
                "scan_mode": "INTRADAY",
                "recommended_at": "2026-05-20T09:40:00+09:00",
                "priority_rank": 1,
                "return_1d_pct": 2.0,
            },
            {
                "ticker": "000002.KQ",
                "scan_mode": "INTRADAY",
                "base_trade_date": "2026-05-20",
                "priority_rank": 2,
                "return_1d_pct": -1.0,
            },
            {
                "ticker": "000003.KS",
                "scan_mode": "SWING",
                "base_trade_date": "2026-05-20",
                "priority_rank": 1,
                "return_1d_pct": 3.0,
            },
        ]
    ).to_csv(path, index=False)

    rows = load_intraday_rows(path)

    assert rows["market2"].tolist() == ["KOSDAQ", "KOSPI"]
    assert rows["trade_date"].tolist() == ["2026-05-20", "2026-05-20"]


def test_build_report_computes_intraday_cohort_metrics(tmp_path) -> None:
    path = tmp_path / "archive.csv"
    pd.DataFrame(
        [
            {
                "ticker": "000001.KS",
                "scan_mode": "INTRADAY",
                "base_trade_date": "2026-05-20",
                "priority_rank": 1,
                "decision": "PRIORITY_WATCHLIST",
                "return_1d_pct": 2.0,
                "return_3d_pct": 5.0,
            },
            {
                "ticker": "000002.KS",
                "scan_mode": "INTRADAY",
                "base_trade_date": "2026-05-21",
                "priority_rank": 4,
                "decision": "WATCHLIST",
                "return_1d_pct": -1.0,
                "return_3d_pct": -2.0,
            },
        ]
    ).to_csv(path, index=False)

    report = build_report(path)
    kospi = next(row for row in report["markets"] if row["market"] == "KOSPI")

    assert kospi["rows"] == 2
    assert kospi["return_1d_rows"] == 2
    assert kospi["model_ready"] is False
    assert kospi["latest_data_lag_days"] is not None
    assert kospi["operational_ready"] is False
    assert kospi["cohorts"]["Top5"]["return_1d_pct"]["win_pct"] == 50.0
    assert kospi["cohorts"]["Top1"]["return_3d_pct"]["avg_pct"] == 5.0
