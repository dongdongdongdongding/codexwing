from multi_agent.tools.build_paper_trade_ledger import (
    simulate_close_proxy_trade,
    summarize_ledger,
)


def test_close_proxy_trade_takes_profit_on_first_realized_close_trigger():
    row = {
        "run_id": "RUN-TEST",
        "ticker": "123456.KQ",
        "market": "KOSDAQ",
        "scan_mode": "SWING",
        "priority_rank": 1,
        "decision": "PRIORITY_WATCHLIST",
        "entry_reference_price": 10000,
        "return_1d_pct": 2.0,
        "return_2d_pct": 12.0,
        "return_3d_pct": 8.0,
    }

    trade = simulate_close_proxy_trade(row, fee_bps=1.0, slippage_bps=2.0)

    assert trade["trade_status"] == "CLOSED"
    assert trade["exit_day"] == 2
    assert trade["exit_reason"] == "TAKE_PROFIT_CLOSE_PROXY"
    assert trade["gross_return_pct"] == 10.0
    assert trade["net_return_pct"] == 9.94


def test_close_proxy_trade_leaves_missing_outcome_unresolved():
    row = {
        "run_id": "RUN-TEST",
        "ticker": "005930.KS",
        "market": "KOSPI",
        "scan_mode": "SWING",
        "priority_rank": 1,
        "decision": "PRIORITY_WATCHLIST",
        "entry_reference_price": 70000,
    }

    trade = simulate_close_proxy_trade(row)

    assert trade["trade_status"] == "UNRESOLVED"
    assert trade["exit_reason"] == "NO_REALIZED_RETURN"
    assert "NO_RETURN_WITHIN_HOLD" in trade["data_warnings"]


def test_summarize_ledger_reports_rank_floor_and_upside():
    ledger = [
        {"trade_status": "CLOSED", "market": "KOSPI", "priority_rank": 1, "exit_reason": "TIME_EXIT", "net_return_pct": 5.0},
        {"trade_status": "CLOSED", "market": "KOSPI", "priority_rank": 1, "exit_reason": "TIME_EXIT", "net_return_pct": -3.0},
        {"trade_status": "UNRESOLVED", "market": "KOSPI", "priority_rank": 2, "exit_reason": "NO_REALIZED_RETURN", "net_return_pct": None},
    ]

    summary = summarize_ledger(ledger)
    market = [row for row in summary["groups"] if row.get("market") == "KOSPI" and "priority_rank" not in row][0]

    assert summary["rows"] == 3
    assert summary["closed_rows"] == 2
    assert summary["unresolved_rows"] == 1
    assert market["avg_pct"] == 1.0
    assert market["max_pct"] == 5.0
    assert market["min_pct"] == -3.0
