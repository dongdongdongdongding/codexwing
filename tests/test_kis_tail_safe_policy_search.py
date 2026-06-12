import pandas as pd

from multi_agent.tools.search_kis_tail_safe_policy import (
    SCORE_SPECS,
    PolicyRule,
    _prepare_policy_columns,
    _rule_mask,
    evaluate_adaptive_policy,
)
from multi_agent.tools.train_kis_historical_best_effort_suite import Window, _filter_valid_labels


def _labeled_frame(rows):
    raw = pd.DataFrame(rows)
    return _prepare_policy_columns(_filter_valid_labels(raw, start="2026-01-01", end="2026-01-31"))


def test_rule_mask_uses_real_kis_and_prior_columns():
    frame = _prepare_policy_columns(
        pd.DataFrame(
            {
                "kis_daily_return_5d_pct": [3.0, 18.0],
                "kis_daily_close_location_pct": [75.0, 85.0],
                "kis_daily_volume_ratio_20d": [1.4, 2.1],
                "close_failure_prior_ticker_risk_score": [18.0, 70.0],
                "close_failure_prior_theme_stop5_rate_pct": [20.0, 60.0],
                "close_failure_prior_ticker_avg_mae_5d_pct": [-4.0, -12.0],
                "kis_daily_pct_from_52w_high": [-10.0, -65.0],
            }
        )
    )
    rule = PolicyRule(
        r5_min=-5.0,
        r5_max=8.0,
        close_location_min=60.0,
        volume_ratio_min=1.0,
        ticker_risk_max=30.0,
        theme_stop_max=30.0,
        ticker_avg_mae_min=-6.0,
        pct_from_52w_high_min=-25.0,
    )

    assert _rule_mask(frame, rule).tolist() == [True, False]


def test_adaptive_policy_prefers_tail_safe_rows_out_of_sample():
    rows = []
    for day in range(1, 11):
        date = f"2026-01-{day:02d}"
        rows.append(
            {
                "base_trade_date": date,
                "trade_date": date,
                "run_id": f"R{day}",
                "ticker": f"GOOD{day:02d}",
                "market": "KOSPI",
                "kis_daily_return_5d_pct": 3.0,
                "kis_daily_close_location_pct": 78.0,
                "kis_daily_volume_ratio_20d": 1.6,
                "kis_whale_score": 30.0,
                "kis_daily_pct_from_52w_high": -9.0,
                "close_failure_prior_ticker_risk_score": 15.0,
                "close_failure_prior_theme_stop5_rate_pct": 18.0,
                "close_failure_prior_ticker_avg_mae_5d_pct": -4.0,
                "buy_premium_target_before_stop_5d": True,
                "buy_premium_target_hit_5d": True,
                "buy_premium_stop_hit_5d": False,
                "buy_premium_stop_before_target_5d": False,
                "buy_premium_return_5d_pct": 6.0,
                "buy_premium_max_high_return_5d_pct": 8.0,
                "buy_premium_min_low_return_5d_pct": -4.0,
            }
        )
        rows.append(
            {
                "base_trade_date": date,
                "trade_date": date,
                "run_id": f"R{day}",
                "ticker": f"BAD{day:02d}",
                "market": "KOSPI",
                "kis_daily_return_5d_pct": 22.0,
                "kis_daily_close_location_pct": 92.0,
                "kis_daily_volume_ratio_20d": 2.6,
                "kis_whale_score": 5.0,
                "kis_daily_pct_from_52w_high": -70.0,
                "close_failure_prior_ticker_risk_score": 85.0,
                "close_failure_prior_theme_stop5_rate_pct": 75.0,
                "close_failure_prior_ticker_avg_mae_5d_pct": -16.0,
                "buy_premium_target_before_stop_5d": False,
                "buy_premium_target_hit_5d": False,
                "buy_premium_stop_hit_5d": True,
                "buy_premium_stop_before_target_5d": True,
                "buy_premium_return_5d_pct": -13.0,
                "buy_premium_max_high_return_5d_pct": 2.0,
                "buy_premium_min_low_return_5d_pct": -18.0,
            }
        )
    frame = _labeled_frame(rows)
    windows = [
        Window(
            fold=1,
            train_days=[f"2026-01-{day:02d}" for day in range(1, 7)],
            embargo_days=["2026-01-07"],
            test_days=["2026-01-08", "2026-01-09", "2026-01-10"],
        )
    ]

    rows = evaluate_adaptive_policy(
        market="KOSPI",
        frame=frame,
        windows=windows,
        topn_values=[1],
        score_names=["risk_adjusted_momentum"],
        min_train_n=3,
        min_train_active_days=3,
    )

    assert set(SCORE_SPECS).issuperset({"risk_adjusted_momentum"})
    assert len(rows) == 1
    metrics = rows[0]["metrics"]
    assert metrics["n"] == 3
    assert metrics["hit5_dd10_5d_pct"] == 100.0
    assert metrics["min_min_low_5d_pct"] == -4.0
    assert rows[0]["latest_recommended_rule"]["rule"]["ticker_risk_max"] <= 30.0
