"""Regression tests for the KR cohort release gate (EV+tail philosophy).

Locks the operator-approved design decision: the hard promotion gate is
sample-sufficiency + expected-value (avg 5D return lower bound clears friction) +
tail safety (avoid_down lower bound). Raw win-rate is reported but is NOT a hard
gate, so a cohort that lets winners run can pass at sub-50% win-rate.
"""
from __future__ import annotations

import pandas as pd

from multi_agent.tools.report_kr_cohort_release_gate import build_report


THRESHOLDS = {
    "min_active_days": 12,
    "min_avg_return_lower": 0.4,
    "min_positive_lower": 0.5,
    "min_avoid_down_lower": 0.5,
    "min_precision_hit10_lower": 0.0,
}


def _exception_leader_df(daily_returns: list[float], days: int = 15) -> pd.DataFrame:
    """Build a synthetic KOSPI SWING Exception Leader cohort dataframe.

    Each day repeats the same ``daily_returns`` so the cohort outcome is deterministic.
    """
    rows = []
    for d in range(days):
        date = f"2026-05-{d + 1:02d}"
        for i, ret in enumerate(daily_returns):
            rows.append({
                "ticker": f"00{d:02d}{i}.KS",
                "scan_mode": "SWING",
                "decision_bucket": "exception_leader",
                "decision": "EXCEPTION_LEADER",
                "base_trade_date": date,
                "trade_date": date,
                "return_1d_pct": ret / 3.0,
                "return_3d_pct": ret / 1.5,
                "return_5d_pct": ret,
                "max_high_return_5d_pct": max(ret, 0.0) + 2.0,
                "is_dummy_data": False,
            })
    return pd.DataFrame(rows)


def test_sub_50_winrate_cohort_passes_on_ev_and_tail():
    # 40% win rate (4 of 10 > 0), but avg strongly positive and avoid_down >= 50%.
    daily = [15.0, 15.0, 15.0, 15.0, 0.0, 0.0, -1.0, -1.0, -1.0, -1.0]
    df = _exception_leader_df(daily)
    report = build_report(df, "KOSPI", confidence=0.95, bootstrap_iters=500, thresholds=THRESHOLDS)
    cohort = report["cohorts"]["EXCEPTION_LEADER"]

    # Win-rate is sub-50 and reported as a non-gating info FAIL...
    win_check = next(c for c in cohort["checks"] if c["code"].endswith("POSITIVE_5D_LOWER"))
    assert win_check["gate"] is False
    assert win_check["passed"] is False
    # ...but EV + tail gates pass, so the cohort is promotable.
    assert cohort["passed"] is True
    assert cohort["avg_return"]["lower"] >= THRESHOLDS["min_avg_return_lower"]


def test_losing_cohort_fails_ev_gate():
    daily = [-3.0] * 10
    df = _exception_leader_df(daily)
    report = build_report(df, "KOSPI", confidence=0.95, bootstrap_iters=500, thresholds=THRESHOLDS)
    cohort = report["cohorts"]["EXCEPTION_LEADER"]

    assert cohort["passed"] is False
    avg_check = next(c for c in cohort["checks"] if c["code"].endswith("AVG_5D_LOWER"))
    assert avg_check["gate"] is True
    assert avg_check["passed"] is False


def test_insufficient_active_days_fails():
    daily = [10.0, 10.0, 10.0, 0.0, 0.0]
    df = _exception_leader_df(daily, days=5)  # below min_active_days=12
    report = build_report(df, "KOSPI", confidence=0.95, bootstrap_iters=500, thresholds=THRESHOLDS)
    cohort = report["cohorts"]["EXCEPTION_LEADER"]

    assert cohort["passed"] is False
    days_check = next(c for c in cohort["checks"] if c["code"].endswith("MIN_ACTIVE_DAYS"))
    assert days_check["gate"] is True
    assert days_check["passed"] is False
