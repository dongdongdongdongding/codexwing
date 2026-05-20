import pandas as pd

from multi_agent.tools.report_kospi_swing_gate_holdout import build_report


def test_gate_holdout_marker_counts_use_exact_codes(tmp_path):
    dataset = tmp_path / "archive.csv"
    pd.DataFrame(
        [
            {
                "market": "KOSPI",
                "scan_mode": "SWING",
                "recommended_at": "2026-05-07T00:00:00Z",
                "decision": "PRIORITY_WATCHLIST",
                "theme_risk": "['KOSPI_SWING_PRIORITY_GUARD_SOFT', 'EXPECTED_EDGE_PRIORITY_GUARD_SOFT']",
                "return_3d_pct": "4.0",
                "return_5d_pct": "6.0",
                "max_high_return_5d_pct": "8.0",
            },
            {
                "market": "KOSPI",
                "scan_mode": "SWING",
                "recommended_at": "2026-05-07T00:00:00Z",
                "decision": "WATCHLIST",
                "theme_risk": "['KOSPI_SWING_PRIORITY_GUARD']",
                "return_3d_pct": "-2.0",
                "return_5d_pct": "-4.0",
                "max_high_return_5d_pct": "1.0",
            },
        ]
    ).to_csv(dataset, index=False)

    report = build_report(dataset, "2026-05-06T13:30:00Z", min_priority_30d=1)

    assert report["marker_counts"]["KOSPI_SWING_PRIORITY_GUARD_SOFT"] == 1
    assert report["marker_counts"]["EXPECTED_EDGE_PRIORITY_GUARD_SOFT"] == 1
    assert report["marker_counts"]["KOSPI_SWING_PRIORITY_GUARD"] == 1
    assert report["marker_counts"]["EXPECTED_EDGE_PRIORITY_GUARD"] == 0
