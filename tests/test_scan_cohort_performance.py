import pandas as pd

from multi_agent.tools.report_scan_cohort_performance import build_report, render_markdown


def test_scan_cohort_performance_groups_by_chase_risk_level():
    report = build_report(
        pd.DataFrame(
            [
                {
                    "ticker": "005930.KS",
                    "scan_mode": "SWING",
                    "priority_rank": 1,
                    "decision_bucket": "picked",
                    "return_1d_pct": 1.0,
                    "return_3d_pct": 2.0,
                    "return_5d_pct": 4.0,
                    "min_return_observed_pct": -1.0,
                    "max_high_return_5d_pct": 6.0,
                    "chase_risk_level": "낮음",
                },
                {
                    "ticker": "000660.KS",
                    "scan_mode": "SWING",
                    "priority_rank": 2,
                    "decision_bucket": "picked",
                    "return_1d_pct": -4.0,
                    "return_3d_pct": -2.0,
                    "return_5d_pct": -1.0,
                    "min_return_observed_pct": -6.0,
                    "max_high_return_5d_pct": 1.0,
                    "chase_risk_level": "높음",
                },
                {
                    "ticker": "091990.KQ",
                    "scan_mode": "SWING",
                    "priority_rank": 1,
                    "decision": "EXCEPTION_LEADER",
                    "return_1d_pct": 0.5,
                    "return_3d_pct": 3.0,
                    "return_5d_pct": 5.0,
                    "min_return_observed_pct": -0.5,
                    "max_high_return_5d_pct": 8.0,
                    "chase_risk_level": "보통",
                },
            ]
        )
    )

    kospi = report["markets"]["KOSPI"]
    assert kospi["by_chase_risk_level"]["낮음"]["horizons"]["5D"]["win_pct"] == 100.0
    assert kospi["cohorts"]["Top5"]["horizons"]["5D"]["min_pct"] == -1.0
    assert kospi["cohorts"]["Top5"]["horizons"]["5D"]["max_pct"] == 4.0
    assert kospi["by_chase_risk_level"]["높음"]["path"]["bad_path_pct"] == 100.0
    assert report["markets"]["KOSDAQ"]["cohorts"]["Exception Leader"]["horizons"]["5D"]["n"] == 1

    markdown = render_markdown(report)
    assert "### Chase Risk Level" in markdown
    assert "min -1.00% / max +4.00%" in markdown
    assert "| 높음 |" in markdown
