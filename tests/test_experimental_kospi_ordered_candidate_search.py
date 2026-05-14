from __future__ import annotations

import pandas as pd

from multi_agent.tools.experimental_kospi_ordered_candidate_search import (
    OrderedProfile,
    _condition_to_mask,
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
