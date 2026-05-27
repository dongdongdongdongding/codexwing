from __future__ import annotations

import pandas as pd

from multi_agent.tools.mine_significant_feature_combinations import build_report


def test_feature_combination_mining_reports_search_diagnostics():
    rows = []
    for idx in range(100):
        day = (idx % 20) + 1
        rows.append(
            {
                "market2": "KOSPI",
                "trade_date": f"2026-05-{day:02d}",
                "priority_rank": (idx % 20) + 1,
                "alpha_score": 50 + (idx % 40),
                "tech_score": 55 + (idx % 30),
                "prob_clean": 20 + (idx % 50),
                "volume_ratio": 0.5 + ((idx % 12) / 10),
                "trend": "UP" if idx % 3 else "DOWN",
                "market_gate": "GREEN" if idx % 4 else "YELLOW",
                "return_1d_pct": 1.0 if idx % 2 else -1.0,
                "return_3d_pct": 2.0 if idx % 3 else -2.0,
                "return_5d_pct": 4.0 if idx % 4 else -3.0,
                "min_return_observed_pct": -2.0 if idx % 5 else -6.0,
                "stop5_proxy": bool(idx % 5 == 0),
                "bad_path": bool(idx % 5 == 0 or idx % 4 == 0),
                "exception_leader": bool(idx % 17 == 0),
                "core_trend_flag_bool": bool(idx % 3 != 0),
                "explosive_leader_flag_bool": bool(idx % 11 == 0),
            }
        )
    report = build_report(
        pd.DataFrame(rows),
        markets=["KOSPI"],
        scopes=["market_all"],
        horizons=["5d"],
        train_ratio=0.7,
        min_train=8,
        min_test=5,
        min_days=3,
        min_support=6,
        beam_width=6,
        max_terms=2,
        include_primary_theme=False,
        exact_exhaustive_max_predicates=300,
        exact_exhaustive_max_combos=200,
    )

    diagnostics = report["diagnostics"]
    summary = diagnostics["summary"]
    scope = diagnostics["scopes"][0]

    assert summary["scope_count"] == 1
    assert summary["candidate_features"]["total"] > 0
    assert summary["predicates"]["unique"] > 0
    assert summary["predicates"]["after_support_screen"] > 0
    assert scope["singleton_filters"]["5d"]["evaluated"] > 0
    assert "5d" in scope["beam_pruning"]
    assert summary["exact_exhaustive"]["enabled_scopes"] == 1
    assert summary["exact_exhaustive"]["checked_combinations"] > 0
