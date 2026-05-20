from multi_agent.tools.report_segment_topn_validation import _aggregate, build_markdown


def test_segment_topn_validation_reports_return_tails():
    summary = _aggregate(
        [
            {
                "scan_date": "2026-05-18",
                "samples": 5.0,
                "positive_rate": 0.8,
                "avg_return_pct": 2.0,
                "min_return_pct": -4.0,
                "max_return_pct": 9.0,
                "hit5_rate": 0.4,
                "hit10_rate": 0.0,
            },
            {
                "scan_date": "2026-05-19",
                "samples": 5.0,
                "positive_rate": 0.6,
                "avg_return_pct": -1.0,
                "min_return_pct": -8.0,
                "max_return_pct": 12.0,
                "hit5_rate": 0.2,
                "hit10_rate": 0.2,
            },
        ]
    )

    assert summary["worst_return_pct"] == -8.0
    assert summary["best_return_pct"] == 12.0
    assert summary["min_daily_avg_return_pct"] == -1.0
    assert summary["max_daily_avg_return_pct"] == 2.0


def test_segment_topn_markdown_includes_tail_metrics():
    block = {
        "days": 1,
        "topn_samples_per_day": 5,
        "positive_rate_pct": 80.0,
        "avg_return_pct": 2.0,
        "worst_return_pct": -4.0,
        "best_return_pct": 9.0,
        "min_daily_avg_return_pct": 2.0,
        "max_daily_avg_return_pct": 2.0,
        "hit5_rate_pct": 40.0,
        "hit10_rate_pct": 0.0,
        "accuracy_gap_to_target_pct": 5.0,
        "return_gap_to_target_pct": -13.0,
    }
    markdown = build_markdown(
        {
            "topn": 5,
            "generated_at": "now",
            "source": "test",
            "targets": {"top5_accuracy_pct": 75.0, "high_conviction_avg_return_pct": 15.0},
            "recent_days": 20,
            "measurement_horizon_by_mode": {"SWING": "return_3d_pct"},
            "fetch_stats": {},
            "segments": {
                "KOSPI:SWING": {
                    "recent_window": block,
                    "all_history": block,
                    "warnings": [],
                }
            },
        }
    )

    assert "recent worst/best candidate return: -4.00% / +9.00%" in markdown
    assert "recent min/max daily avg return: +2.00% / +2.00%" in markdown
