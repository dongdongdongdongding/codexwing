import pandas as pd

from multi_agent.tools.analyze_close_return_failure_traits import build_report, prepare_failure_frame


def _fixture_frame() -> pd.DataFrame:
    frame = pd.DataFrame(
        [
            {
                "ticker": "AAA.KQ",
                "market": "KOSDAQ",
                "trade_date": "2026-04-01",
                "run_id": "r1",
                "max_high_return_5d_pct": 7.2,
                "min_low_return_5d_pct": -1.0,
                "return_1d_pct": 0.5,
                "return_5d_pct": 1.0,
                "day_return_pct": 9.0,
                "volume_ratio": 4.0,
                "primary_theme": "EV",
                "decision_bucket": "Top5",
            },
            {
                "ticker": "BBB.KQ",
                "market": "KOSDAQ",
                "trade_date": "2026-04-01",
                "run_id": "r1",
                "max_high_return_5d_pct": 8.0,
                "min_low_return_5d_pct": -1.0,
                "return_1d_pct": 1.0,
                "return_5d_pct": 6.0,
                "day_return_pct": 1.0,
                "volume_ratio": 1.0,
                "primary_theme": "BIO",
                "decision_bucket": "Top5",
            },
            {
                "ticker": "CCC.KQ",
                "market": "KOSDAQ",
                "trade_date": "2026-04-02",
                "run_id": "r2",
                "max_high_return_5d_pct": 12.0,
                "min_low_return_5d_pct": -2.0,
                "return_1d_pct": 0.0,
                "return_5d_pct": -3.0,
                "day_return_pct": 8.0,
                "volume_ratio": 3.0,
                "primary_theme": "EV",
                "decision_bucket": "Top5",
            },
            {
                "ticker": "DDD.KQ",
                "market": "KOSDAQ",
                "trade_date": "2026-04-02",
                "run_id": "r2",
                "max_high_return_5d_pct": 10.0,
                "min_low_return_5d_pct": -0.5,
                "return_1d_pct": 1.0,
                "return_5d_pct": 8.0,
                "day_return_pct": 0.5,
                "volume_ratio": 1.2,
                "primary_theme": "BIO",
                "decision_bucket": "Top5",
            },
            {
                "ticker": "EEE.KQ",
                "market": "KOSDAQ",
                "trade_date": "2026-04-03",
                "run_id": "r3",
                "max_high_return_5d_pct": 4.0,
                "min_low_return_5d_pct": -2.0,
                "return_1d_pct": -1.0,
                "return_5d_pct": -2.0,
                "day_return_pct": 2.0,
                "volume_ratio": 1.5,
                "primary_theme": "EV",
                "decision_bucket": "Top5",
            },
            {
                "ticker": "FFF.KQ",
                "market": "KOSDAQ",
                "trade_date": "2026-04-03",
                "run_id": "r3",
                "max_high_return_5d_pct": 12.0,
                "min_low_return_5d_pct": -8.0,
                "return_1d_pct": 1.0,
                "return_5d_pct": 6.0,
                "day_return_pct": 5.0,
                "volume_ratio": 5.0,
                "primary_theme": "RISK",
                "decision_bucket": "Exception",
            },
        ]
    )
    frame["bad_path"] = [True, False, True, False, True, True]
    frame["first_touch_5d"] = ["target_first", "target_first", "target_first", "target_first", "none", "stop_first"]
    return frame


def test_prepare_failure_frame_uses_buy_premium_for_touch_and_close_loss():
    prepared = prepare_failure_frame(_fixture_frame(), buy_premium_pct=2.0)

    first = prepared.iloc[0]
    assert round(first["_adj_max_high_return_5d_pct"], 6) == 5.098039
    assert round(first["_adj_return_5d_pct"], 6) == -0.980392
    assert bool(first["_touch5_5d_bool"]) is True
    assert bool(first["_touch5_close_loss_bool"]) is True
    assert bool(first["_close_defense_5d_bool"]) is False

    no_touch = prepared.iloc[4]
    assert bool(no_touch["_touch5_5d_bool"]) is False
    assert bool(no_touch["_no_touch_close_loss_bool"]) is True


def test_build_report_surfaces_numeric_and_categorical_failure_traits_without_outcome_leakage():
    report = build_report(_fixture_frame(), min_support=1, max_traits=10, max_categories=20)
    all_segment = next(segment for segment in report["segments"] if segment["segment"] == "ALL")

    assert all_segment["n_failure"] == 2
    assert all_segment["n_control"] == 2
    assert report["overall"]["conditional_rates"]["close_loss_given_touch5_pct"] == 40.0

    numeric = {row["feature"]: row for row in all_segment["numeric_failure_traits"]}
    assert "day_return_pct" in numeric
    assert numeric["day_return_pct"]["direction"] == "higher_in_failures"
    assert "return_5d_pct" not in numeric
    assert "max_high_return_5d_pct" not in numeric

    risky_categories = all_segment["categorical_failure_traits"]["risky_categories"]
    categorical_features = all_segment["categorical_failure_traits"]["features_evaluated"]
    assert "bad_path" not in categorical_features
    assert "first_touch_5d" not in categorical_features
    ev = next(row for row in risky_categories if row["feature"] == "primary_theme" and row["category"] == "EV")
    assert ev["failure_rate_pct"] == 100.0
    assert ev["failure_lift"] > 2.0

    assert report["actionable_hypotheses"]
