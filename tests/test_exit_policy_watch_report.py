from __future__ import annotations

from multi_agent.tools.report_exit_policy_watch import build_report, render_markdown


def test_exit_policy_watch_report_separates_exit_from_hold():
    optimizer = {
        "generated_at": "2026-05-27T00:00:00Z",
        "evaluated_policies": 1,
        "top_policies": [
            {
                "market": "KOSDAQ",
                "cohort": "ranked_top20",
                "policy_type": "score_baseline",
                "model": "prob_clean",
                "feature_set": "score_column",
                "topn": 3,
                "quality_score": 86.3,
                "label_profile": {"name": "ordered_5d_5v3_lowmae"},
                "metrics": {
                    "n": 41,
                    "active_days": 14,
                    "label_win_pct": 73.171,
                    "avg_5d_pct": 0.1308,
                    "min_5d_pct": -33.2955,
                    "target_before_stop_5d_pct": 95.122,
                    "stop_before_target_5d_pct": 4.878,
                    "win_ordered_exit_5d_pct": 95.122,
                    "avg_ordered_exit_5d_pct": 4.6098,
                    "min_ordered_exit_5d_pct": -3.0,
                },
                "promotion": {
                    "promotable": False,
                    "exit_policy_watch": True,
                    "failed_checks": ["avg_return_gate", "tail_loss_gate"],
                },
            }
        ],
    }
    cohort = {
        "markets": {
            "KOSDAQ": {
                "cohorts": {
                    "Top5": {
                        "horizons": {"5D": {"n": 434, "win_pct": 52.765, "avg_pct": 1.94, "min_pct": -46.31, "max_pct": 65.65}},
                        "path": {"bad_path_pct": 66.59, "clean_riser_pct": 11.521},
                    }
                }
            }
        }
    }

    report = build_report(optimizer, cohort, friction_pct=0.35)
    row = report["watch_rows"][0]

    assert report["watch_count"] == 1
    assert row["state"] == "FORWARD_TRACK_SMALL_SAMPLE"
    assert row["net_exit_avg_5d_pct"] == 4.2598
    assert row["close_min_5d_pct"] == -33.2955
    assert report["baselines"]["KOSDAQ"][0]["cohort"] == "Top5"
    assert "Net Exit Avg" in render_markdown(report)
