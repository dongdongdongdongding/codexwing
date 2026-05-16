from __future__ import annotations

import pandas as pd

from multi_agent.tools.experimental_kospi_ordered_candidate_search import (
    OrderedProfile,
    _condition_to_mask,
    _metrics,
    add_search_columns,
    classify_candidates,
    prepare_profile_rows,
)


def test_prepare_profile_rows_dedupes_profile_ticker_date() -> None:
    df = pd.DataFrame(
        [
            {
                "market2": "KOSPI",
                "ticker": "000001.KS",
                "trade_date": "2026-04-01",
                "priority_rank": 2,
                "decision_score": 90,
            },
            {
                "market2": "KOSPI",
                "ticker": "000001.KS",
                "trade_date": "2026-04-01",
                "priority_rank": 1,
                "decision_score": 80,
            },
        ]
    )

    rows = prepare_profile_rows(df, [OrderedProfile("x", 5, 10.0, 5.0)])

    assert len(rows) == 1
    assert rows.iloc[0]["priority_rank"] == 1
    assert rows.iloc[0]["target_pct"] == 10.0


def test_prepare_profile_rows_supports_kosdaq_market() -> None:
    df = pd.DataFrame(
        [
            {
                "market2": "KOSPI",
                "ticker": "000001.KS",
                "trade_date": "2026-04-01",
                "priority_rank": 1,
                "decision_score": 90,
            },
            {
                "market2": "KOSDAQ",
                "ticker": "000001.KQ",
                "trade_date": "2026-04-01",
                "priority_rank": 1,
                "decision_score": 90,
            },
        ]
    )

    rows = prepare_profile_rows(df, [OrderedProfile("x", 5, 5.0, 5.0)], market="KOSDAQ")

    assert len(rows) == 1
    assert rows.iloc[0]["ticker"] == "000001.KQ"
    assert rows.iloc[0]["candidate_cohort"] == "KOSDAQ_ALL"


def test_add_search_columns_marks_immature_no_touch_not_ready() -> None:
    df = pd.DataFrame(
        [
            {
                "candidate_id": "x",
                "ticker": "000001.KS",
                "trade_date": "2026-04-01",
                "priority_rank": 1,
                "decision": "PRIORITY_WATCHLIST",
                "decision_bucket": "picked",
                "ordered_target_before_stop": False,
                "ordered_stop_before_target": False,
                "ordered_terminal_status": "no_touch",
                "ordered_bars_observed": 2,
                "horizon_days": 5,
            },
            {
                "candidate_id": "x",
                "ticker": "000002.KS",
                "trade_date": "2026-04-01",
                "priority_rank": 1,
                "decision": "PRIORITY_WATCHLIST",
                "decision_bucket": "picked",
                "ordered_target_before_stop": True,
                "ordered_stop_before_target": False,
                "ordered_terminal_status": "target_before_stop",
                "ordered_bars_observed": 1,
                "horizon_days": 5,
            },
        ]
    )

    out = add_search_columns(df)

    assert out["ordered_label_ready"].tolist() == [False, True]
    assert out["ordered_win"].tolist() == [False, True]


def test_classify_candidates_excludes_static_theme_from_release_like() -> None:
    row = {
        "profile": "x",
        "conditions": ["primary_theme=방산", "prob_clean>=28"],
        "uses_static_theme": True,
        "all": {"n": 20, "win_pct": 80.0, "avg_mfe_pct": 12.0},
        "train": {"n": 10, "win_pct": 80.0},
        "test": {"n": 10, "win_pct": 80.0, "stop_pct": 10.0},
        "fold_weighted_win_pct": 80.0,
        "fold_min_win_pct": 70.0,
    }

    buckets = classify_candidates([row])

    assert buckets["release_like_non_theme"] == []
    assert buckets["theme_dependent_diagnostics"] == [row]


def test_classify_candidates_promotes_75pct_practical_bucket() -> None:
    row = {
        "profile": "x",
        "conditions": ["prob_clean<=31.8"],
        "uses_static_theme": False,
        "all": {"n": 24, "win_pct": 76.0, "avg_mfe_pct": 9.0},
        "train": {"n": 12, "win_pct": 75.0},
        "test": {
            "n": 9,
            "win_pct": 77.7778,
            "stop_pct": 22.2222,
            "median_close_5d_pct": 7.0,
            "close_loss_5pct_or_worse_pct": 0.0,
        },
        "fold_weighted_win_pct": 69.5652,
        "fold_min_win_pct": 63.6364,
    }

    buckets = classify_candidates([row])

    assert buckets["practical_watch_75pct_non_theme"] == [row]
    assert buckets["practical_candidates_75pct_non_theme"] == [row]
    assert buckets["strong_practical_80pct_non_theme"] == []
    assert buckets["recent_regime_75pct_non_theme"] == []
    assert buckets["promotion_ready_non_theme"] == []


def test_classify_candidates_separates_recent_regime_from_practical() -> None:
    row = {
        "profile": "x",
        "conditions": ["cohort=Top5", "prob_clean<=27.7"],
        "uses_static_theme": False,
        "all": {"n": 23, "win_pct": 65.2174, "avg_mfe_pct": 9.0},
        "train": {"n": 11, "win_pct": 45.4545},
        "test": {
            "n": 12,
            "win_pct": 83.3333,
            "stop_pct": 16.6667,
            "median_close_5d_pct": 1.4568,
            "close_loss_5pct_or_worse_pct": 0.0,
        },
        "fold_weighted_win_pct": 83.3334,
        "fold_min_win_pct": 71.4286,
    }

    buckets = classify_candidates([row])

    assert buckets["practical_watch_75pct_non_theme"] == [row]
    assert buckets["practical_candidates_75pct_non_theme"] == []
    assert buckets["strong_practical_80pct_non_theme"] == []
    assert buckets["recent_regime_75pct_non_theme"] == [row]


def test_condition_to_mask_supports_numeric_band() -> None:
    df = pd.DataFrame({"prob_clean": [27.9, 28.1, 30.0, 31.8, 31.9]})

    mask = _condition_to_mask(df, "prob_clean=[28.1,31.8]")

    assert mask.tolist() == [False, True, True, True, False]


def test_condition_to_mask_top3_is_inclusive_and_excludes_exception() -> None:
    df = pd.DataFrame(
        {
            "priority_rank": [1, 2, 3, 4, 3],
            "decision": ["WATCHLIST", "WATCHLIST", "WATCHLIST", "WATCHLIST", "EXCEPTION_LEADER"],
            "decision_bucket": ["watchlist", "watchlist", "watchlist", "watchlist", "exception_leader"],
        }
    )

    mask = _condition_to_mask(df, "cohort=Top3")

    assert mask.tolist() == [True, True, True, False, False]


def test_metrics_include_ordered_tail_distribution() -> None:
    df = pd.DataFrame(
        {
            "ordered_label_ready": [True, True, True],
            "ordered_win": [True, False, True],
            "ordered_stop": [False, True, False],
            "ordered_terminal_status": ["target_before_stop", "stop_before_target", "target_before_stop"],
            "ordered_mfe_pct": [12.0, 1.0, 9.0],
            "ordered_mae_pct": [-1.0, -7.0, -2.0],
            "return_5d_pct": [8.0, -6.0, 3.0],
        }
    )

    metrics = _metrics(df, pd.Series([True, True, True]))

    assert metrics["n"] == 3
    assert metrics["win_pct"] == 66.6667
    assert metrics["median_close_5d_pct"] == 3.0
    assert metrics["min_close_5d_pct"] == -6.0
    assert metrics["max_close_5d_pct"] == 8.0
    assert metrics["close_loss_5pct_or_worse_pct"] == 33.3333
    assert metrics["min_mae_pct"] == -7.0
