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


def test_live_policy_report_prefers_forward_high_touch_and_excludes_null_targets():
    df = pd.DataFrame(
        [_row(f"010{i:03d}.KS", "exception_leader", -1.0, -1.0, max_high_return_5d_pct=6.0, hit_5pct_within_5d=True) for i in range(30)]
        + [_row("019999.KS", "exception_leader", 10.0, 10.0, max_high_return_5d_pct=None, hit_5pct_within_5d=None)]
    )

    report = build_live_policy_report(df)
    kospi = next(row for row in report["policies"] if row["market"] == "KOSPI")

    assert kospi["rows"] == 31
    assert kospi["target_rows"] == 30
    assert kospi["target_definition"] == "forward_high_within_5d"
    assert kospi["win_5d_pct"] < 70.0
    assert kospi["hit_5pct_within_5d_high_pct"] == 100.0
    assert kospi["avg_max_high_return_5d_pct"] == 6.0
    assert kospi["passes_goal"] is True
    assert kospi["close_5d_quality_pass"] is False
