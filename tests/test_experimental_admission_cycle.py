import pandas as pd

from multi_agent.tools.experimental_admission_cycle import build_report


def test_admission_cycle_reports_stable_and_strict_candidates():
    df = pd.DataFrame(
        [
            {
                "ticker": "000001.KS",
                "trade_date": "2026-04-01",
                "market2": "KOSPI",
                "decision": "WATCHLIST",
                "decision_bucket": "watchlist",
                "priority_rank": 1,
                "max_high_return_5d_pct": 12.0,
                "min_return_observed_pct": -1.0,
                "return_5d_pct": 8.0,
            },
            {
                "ticker": "000002.KS",
                "trade_date": "2026-04-02",
                "market2": "KOSPI",
                "decision": "WATCHLIST",
                "decision_bucket": "watchlist",
                "priority_rank": 2,
                "max_high_return_5d_pct": 14.0,
                "min_return_observed_pct": -2.0,
                "return_5d_pct": 9.0,
            },
            {
                "ticker": "000003.KS",
                "trade_date": "2026-04-03",
                "market2": "KOSPI",
                "decision": "WATCHLIST",
                "decision_bucket": "watchlist",
                "priority_rank": 3,
                "max_high_return_5d_pct": 11.0,
                "min_return_observed_pct": -1.5,
                "return_5d_pct": 7.0,
            },
            {
                "ticker": "000004.KS",
                "trade_date": "2026-04-04",
                "market2": "KOSPI",
                "decision": "WATCHLIST",
                "decision_bucket": "watchlist",
                "priority_rank": 4,
                "max_high_return_5d_pct": 13.0,
                "min_return_observed_pct": -2.5,
                "return_5d_pct": 10.0,
            },
        ]
    )

    report = build_report(
        df,
        max_depth=0,
        beam_width=1,
        min_train=2,
        min_test=2,
        max_conditions=1,
        train_ratio=0.5,
        top_n=10,
        run_ml=False,
    )

    assert report["above_70pct_holdout"]
    assert report["stable_60train_70test"]
    assert report["strict_70train_70test"]
    assert report["strict_70train_70test"][0]["test"]["win_rate_pct"] == 100.0
