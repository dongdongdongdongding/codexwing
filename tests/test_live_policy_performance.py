import pandas as pd

from multi_agent.tools.report_live_policy_performance import build_live_policy_report


def _row(ticker, bucket, ret5, max_ret, **extra):
    row = {
        "ticker": ticker,
        "market_type": "KR",
        "scan_mode": "SWING",
        "decision_bucket": bucket,
        "decision": "",
        "expected_edge_score": None,
        "trend": "UP",
        "return_5d_pct": ret5,
        "max_return_observed_pct": max_ret,
        "validation_excluded": False,
        "is_dummy_data": False,
    }
    row.update(extra)
    return row


def test_live_policy_report_uses_kospi_exception_or_edge_policy():
    df = pd.DataFrame(
        [_row("005930.KS", "watchlist", 6.0, 6.0, expected_edge_score=5.2)]
        + [_row(f"000{i:03d}.KS", "exception_leader", 6.0, 7.0) for i in range(30)]
        + [_row("999999.KS", "watchlist", -5.0, -1.0, expected_edge_score=4.9)]
    )

    report = build_live_policy_report(df)
    kospi = next(row for row in report["policies"] if row["market"] == "KOSPI")

    assert kospi["rows"] == 31
    assert kospi["win_5d_pct"] == 100.0
    assert kospi["hit_5pct_within_observed_5d_pct"] == 100.0
    assert kospi["passes_goal"] is True


def test_live_policy_report_uses_kosdaq_exception_uptrend_policy():
    df = pd.DataFrame(
        [_row(f"100{i:03d}.KQ", "exception_leader", 6.0, 8.0, trend="UP") for i in range(30)]
        + [_row("200000.KQ", "exception_leader", -4.0, -1.0, trend="DOWN")]
        + [_row("300000.KQ", "watchlist", 10.0, 12.0, trend="UP")]
    )

    report = build_live_policy_report(df)
    kosdaq = next(row for row in report["policies"] if row["market"] == "KOSDAQ")

    assert kosdaq["rows"] == 30
    assert kosdaq["win_5d_pct"] == 100.0
    assert kosdaq["hit_5pct_within_observed_5d_pct"] == 100.0
    assert kosdaq["passes_goal"] is True
