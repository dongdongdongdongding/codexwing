from __future__ import annotations

import pandas as pd

from multi_agent.tools.experimental_kospi_ordered_revalidation import (
    CANDIDATES,
    ORDERED_REFINEMENTS,
    evaluate_ordered_refinements,
    select_candidate_rows,
    summarize_labeled,
)


def _base_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "market2": "KOSPI",
                "ticker": "000001.KS",
                "stock_name": "A",
                "trade_date": "2026-04-01",
                "priority_rank": 1,
                "decision": "PRIORITY_WATCHLIST",
                "decision_bucket": "picked",
                "prob_clean": 31.0,
                "decision_score": 100.0,
                "kr_universe_role": "CORE_TREND",
                "core_trend_flag": 0,
                "explosive_leader_flag": 0,
                "ml_prob": 30.0,
            },
            {
                "market2": "KOSPI",
                "ticker": "000002.KS",
                "stock_name": "B",
                "trade_date": "2026-04-01",
                "priority_rank": 2,
                "decision": "PRIORITY_WATCHLIST",
                "decision_bucket": "picked",
                "prob_clean": 31.7,
                "decision_score": 100.0,
                "kr_universe_role": "TRANSITIONAL",
                "core_trend_flag": 0,
                "explosive_leader_flag": 0,
                "ml_prob": 30.0,
            },
            {
                "market2": "KOSPI",
                "ticker": "000003.KS",
                "stock_name": "C",
                "trade_date": "2026-04-01",
                "priority_rank": 4,
                "decision": "PRIORITY_WATCHLIST",
                "decision_bucket": "picked",
                "prob_clean": 35.0,
                "decision_score": 92.0,
                "kr_universe_role": "TRANSITIONAL",
                "core_trend_flag": 0,
                "explosive_leader_flag": 0,
                "ml_prob": 20.0,
            },
            {
                "market2": "KOSPI",
                "ticker": "000004.KS",
                "stock_name": "D",
                "trade_date": "2026-04-01",
                "priority_rank": 1,
                "decision": "EXCEPTION_LEADER",
                "decision_bucket": "exception_leader",
                "prob_clean": 20.0,
                "decision_score": 100.0,
                "kr_universe_role": "CORE_TREND",
                "core_trend_flag": 1,
                "explosive_leader_flag": 0,
                "ml_prob": 10.0,
            },
        ]
    )


def test_select_candidate_rows_keeps_top_rules_and_excludes_exception_leader() -> None:
    selected = select_candidate_rows(_base_rows(), CANDIDATES)

    pairs = set(zip(selected["candidate_id"], selected["ticker"]))
    assert ("strict_top5_core_8v4", "000001.KS") in pairs
    assert ("high_upside_top3_10v5", "000002.KS") in pairs
    assert ("strict_top5_low_ml_10v5", "000003.KS") in pairs
    assert "000004.KS" not in set(selected["ticker"])


def test_summarize_labeled_counts_ordered_target_before_stop() -> None:
    labeled = pd.DataFrame(
        [
            {
                "candidate_id": "x",
                "candidate_description": "desc",
                "candidate_cohort": "Top5",
                "target_pct": 8.0,
                "stop_pct": 4.0,
                "horizon_days": 5,
                "ticker": "000001.KS",
                "ordered_target_before_stop": True,
                "ordered_stop_before_target": False,
                "ordered_terminal_status": "target_before_stop",
                "ordered_mfe_pct": 9.0,
                "ordered_mae_pct": -1.0,
                "return_5d_pct": 4.0,
                "max_high_return_5d_pct": 9.0,
                "min_return_observed_pct": -1.0,
                "source_proxy": '{"fold_weighted_win_pct": 78.947}',
            },
            {
                "candidate_id": "x",
                "candidate_description": "desc",
                "candidate_cohort": "Top5",
                "target_pct": 8.0,
                "stop_pct": 4.0,
                "horizon_days": 5,
                "ticker": "000002.KS",
                "ordered_target_before_stop": False,
                "ordered_stop_before_target": True,
                "ordered_terminal_status": "stop_before_target",
                "ordered_mfe_pct": 2.0,
                "ordered_mae_pct": -4.5,
                "return_5d_pct": -3.0,
                "max_high_return_5d_pct": 2.0,
                "min_return_observed_pct": -4.5,
                "source_proxy": '{"fold_weighted_win_pct": 78.947}',
            },
        ]
    )

    summary = summarize_labeled(labeled)

    assert summary[0]["ordered_labeled_rows"] == 2
    assert summary[0]["ordered_target_before_stop_pct"] == 50.0
    assert summary[0]["ordered_stop_before_target_pct"] == 50.0
    assert summary[0]["avg_ordered_mfe_pct"] == 5.5


def test_evaluate_ordered_refinements_reports_train_test_split() -> None:
    labeled = pd.DataFrame(
        [
            {
                "candidate_id": "high_upside_top3_10v5",
                "ticker": "000001.KS",
                "trade_date": "2026-04-10",
                "prob_clean": 29.0,
                "theme_routing_path": "core_only",
                "ordered_target_before_stop": True,
                "ordered_stop_before_target": False,
                "ordered_terminal_status": "target_before_stop",
                "ordered_mfe_pct": 11.0,
                "ordered_mae_pct": -1.0,
            },
            {
                "candidate_id": "high_upside_top3_10v5",
                "ticker": "000002.KS",
                "trade_date": "2026-04-25",
                "prob_clean": 29.5,
                "theme_routing_path": "core_only",
                "ordered_target_before_stop": False,
                "ordered_stop_before_target": True,
                "ordered_terminal_status": "stop_before_target",
                "ordered_mfe_pct": 3.0,
                "ordered_mae_pct": -5.2,
            },
        ]
    )

    refinements = evaluate_ordered_refinements(labeled, ORDERED_REFINEMENTS[:1])

    assert refinements[0]["all"]["n"] == 2
    assert refinements[0]["all"]["target_before_stop_pct"] == 50.0
    assert refinements[0]["train_before_split"]["target_before_stop_pct"] == 100.0
    assert refinements[0]["test_from_split"]["target_before_stop_pct"] == 0.0
