from datetime import datetime, timezone

import pandas as pd

from multi_agent.tools.report_dynamic_theme_entry_profiles import _profile_level, build_report


def test_profile_level_relaxed_watch_is_observation_only_level():
    assert (
        _profile_level(
            {
                "sample_n": 18,
                "win5_pct": 66.7,
                "practical_win_pct": 66.7,
                "bad_path_pct": 33.3,
                "avg_5d_pct": 5.0,
            }
        )
        == "watch"
    )
    assert (
        _profile_level(
            {
                "sample_n": 18,
                "win5_pct": 50.0,
                "practical_win_pct": 50.0,
                "bad_path_pct": 66.7,
                "avg_5d_pct": 1.0,
            }
        )
        == "fail"
    )


def test_build_report_includes_non_promoting_watch_profile_counts():
    rows = []
    scan_date = datetime(2026, 5, 26, tzinfo=timezone.utc)
    for idx in range(12):
        rows.append(
            {
                "ticker": f"000{idx:03d}.KS",
                "scan_mode": "SWING",
                "market2": "KOSPI",
                "primary_theme": "자동차",
                "scan_date": scan_date,
                "return_1d_pct": 0.0,
                "return_3d_pct": 2.0,
                "return_5d_pct": 8.0,
                "min_return_observed_pct": -1.0,
            }
        )
    for idx in range(6):
        rows.append(
            {
                "ticker": f"001{idx:03d}.KS",
                "scan_mode": "SWING",
                "market2": "KOSPI",
                "primary_theme": "자동차",
                "scan_date": scan_date,
                "return_1d_pct": -2.0,
                "return_3d_pct": -1.0,
                "return_5d_pct": -1.0,
                "min_return_observed_pct": -3.0,
            }
        )

    report = build_report(pd.DataFrame(rows), lookback_days=60)
    kospi = report["markets"]["KOSPI"]

    assert kospi["selected_theme_count"] == 1
    assert kospi["profile_level_counts"]["watch"] == 1
    assert kospi["themes"]["자동차"]["level"] == "watch"
