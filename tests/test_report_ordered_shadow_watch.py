from __future__ import annotations

import pandas as pd

from multi_agent.tools.report_ordered_shadow_watch import evaluate_watch_rules


def test_evaluate_watch_rules_returns_shadow_metrics_by_split() -> None:
    labeled = pd.DataFrame(
        [
            {
                "candidate_id": "5D_ordered_5v5",
                "ticker": "000001.KQ",
                "trade_date": "2026-05-01",
                "priority_rank": 1,
                "decision": "WATCHLIST",
                "decision_bucket": "watchlist",
                "ordered_label_ready": True,
                "ordered_target_before_stop": True,
                "ordered_stop_before_target": False,
                "ordered_win": True,
                "ordered_stop": False,
                "ordered_terminal_status": "target_before_stop",
                "ordered_mfe_pct": 6.0,
                "ordered_mae_pct": -1.0,
                "return_5d_pct": 5.0,
                "theme_day_avg_volume_ratio": 1.0,
            },
            {
                "candidate_id": "5D_ordered_5v5",
                "ticker": "000002.KQ",
                "trade_date": "2026-05-02",
                "priority_rank": 2,
                "decision": "WATCHLIST",
                "decision_bucket": "watchlist",
                "ordered_label_ready": True,
                "ordered_target_before_stop": False,
                "ordered_stop_before_target": True,
                "ordered_win": False,
                "ordered_stop": True,
                "ordered_terminal_status": "stop_before_target",
                "ordered_mfe_pct": 1.0,
                "ordered_mae_pct": -6.0,
                "return_5d_pct": -6.0,
                "theme_day_avg_volume_ratio": 1.0,
            },
            {
                "candidate_id": "5D_ordered_5v5",
                "ticker": "000003.KQ",
                "trade_date": "2026-05-03",
                "priority_rank": 6,
                "decision": "WATCHLIST",
                "decision_bucket": "watchlist",
                "ordered_label_ready": True,
                "ordered_target_before_stop": True,
                "ordered_stop_before_target": False,
                "ordered_win": True,
                "ordered_stop": False,
                "ordered_terminal_status": "target_before_stop",
                "ordered_mfe_pct": 7.0,
                "ordered_mae_pct": -1.0,
                "return_5d_pct": 6.0,
                "theme_day_avg_volume_ratio": 1.0,
            },
        ]
    )
    rules = [
        {
            "rule_id": "top5_volume_watch",
            "market": "KOSDAQ",
            "profile": "5D_ordered_5v5",
            "conditions": ["cohort=Top5", "theme_day_avg_volume_ratio>=0.9"],
        }
    ]

    split_day, rows = evaluate_watch_rules(labeled, rules)

    assert split_day == "2026-05-02"
    assert rows[0]["rule_id"] == "top5_volume_watch"
    assert rows[0]["status"] == "watch_small_sample"
    assert rows[0]["all"]["n"] == 2
    assert rows[0]["all"]["win_pct"] == 50.0
    assert rows[0]["test"]["stop_pct"] == 100.0
