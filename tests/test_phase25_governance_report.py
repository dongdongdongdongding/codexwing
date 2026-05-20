from multi_agent.tools.report_phase25_governance import build_phase25_governance_report


def test_phase25_governance_report_blocks_weak_oos_segment():
    report = build_phase25_governance_report(
        {
            "generated_at": "source",
            "execution_status": "trained",
            "rows_loaded": 100,
            "backend": "lgb",
            "segments": [
                {
                    "name": "phase25_global",
                    "status": "trained",
                    "rows": 100,
                    "raw_auc": 0.56,
                    "cv_median_auc": 0.57,
                    "signal_direction": "normal",
                    "oos_holdout": {
                        "auc": 0.517,
                        "win_rate_pct": 39.7,
                        "avg_return_pct": -1.89,
                    },
                }
            ],
        },
        generated_at="now",
    )

    assert report["release_ready"] is False
    assert report["weak_segments"] == 1
    assert report["segments"][0]["action"] == "neutralize_probability_and_block_priority"
    assert report["segments"][0]["cv_oos_auc_gap"] == 0.053
    assert report["segments"][0]["weak_oos_reasons"] == [
        "oos_win=39.7%<60.0%",
        "oos_avg=-1.89%<0.0%",
    ]
