import pandas as pd

from multi_agent.tools.train_kis_historical_best_effort_suite import (
    _feature_sets,
    _filter_valid_labels,
    _is_leaky_feature,
    _metric_summary,
    _walk_windows,
)


def test_best_effort_feature_sets_exclude_future_label_columns():
    frame = pd.DataFrame(
        {
            "kis_day_change_pct": [1.2, -0.3],
            "kis_daily_return_5d_pct": [3.0, 4.0],
            "return_5d_pct": [10.0, -10.0],
            "buy_premium_return_5d_pct": [9.0, -9.0],
            "max_high_return_5d_pct": [12.0, 1.0],
            "ticker": ["000001.KS", "000002.KS"],
            "primary_theme": ["A", "B"],
        }
    )

    features = _feature_sets(frame)
    numeric, categorical = features["kis_daily_category"]

    assert "kis_day_change_pct" in numeric
    assert "kis_daily_return_5d_pct" in numeric
    assert "ticker" in categorical
    assert "return_5d_pct" not in numeric
    assert "buy_premium_return_5d_pct" not in numeric
    assert "max_high_return_5d_pct" not in numeric
    assert _is_leaky_feature("buy_premium_target_before_stop_5d")


def test_walk_windows_use_embargo_days_between_train_and_test():
    days = [f"2026-01-{day:02d}" for day in range(1, 21)]

    windows = _walk_windows(days, min_train_days=8, test_days=4, max_folds=2, embargo_days=2)

    assert len(windows) == 2
    first = windows[0]
    assert first.train_days[-1] == "2026-01-10"
    assert first.embargo_days == ["2026-01-11", "2026-01-12"]
    assert first.test_days == ["2026-01-13", "2026-01-14", "2026-01-15", "2026-01-16"]


def test_metric_summary_uses_target_touch_and_stop_first_economics():
    raw = pd.DataFrame(
        {
            "base_trade_date": ["2026-01-10", "2026-01-11", "2026-01-12"],
            "run_id": ["R1", "R2", "R3"],
            "buy_premium_target_before_stop_5d": [True, False, False],
            "buy_premium_target_hit_5d": [True, True, False],
            "buy_premium_stop_hit_5d": [False, True, False],
            "buy_premium_stop_before_target_5d": [False, True, False],
            "buy_premium_return_5d_pct": [1.0, -12.0, -1.0],
            "buy_premium_max_high_return_5d_pct": [6.0, 8.0, 1.5],
            "buy_premium_min_low_return_5d_pct": [-2.0, -13.0, -3.0],
        }
    )
    frame = _filter_valid_labels(raw.assign(market="KOSPI"), start="2026-01-01", end="2026-01-31")

    metrics = _metric_summary(frame, frame.index)

    assert metrics["hit5_dd10_5d_pct"] == 33.3333
    assert metrics["win_5d_pct"] == 66.6667
    assert metrics["stop_before_target_5d_pct"] == 33.3333
    assert metrics["min_min_low_5d_pct"] == -13.0
    assert metrics["avg_ordered_exit_5d_pct"] < 0.0
