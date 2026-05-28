from __future__ import annotations

import pandas as pd

from multi_agent.tools.operational_admission_optimizer import LABEL_PROFILES, _label, _metrics, _promotion_flags
from multi_agent.tools.run_internal_retrain_sweep import ORDERED_OUTCOME_PATH_LABEL_VERSION, _load_dataset


def _profile(name: str):
    return next(profile for profile in LABEL_PROFILES if profile.name == name)


def test_ordered_label_uses_target_before_stop_and_mfe_threshold():
    df = pd.DataFrame(
        {
            "trade_date": ["2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04"],
            "target_before_stop_5d": [True, True, False, True],
            "stop_before_target_5d": [False, False, True, False],
            "mfe_5d_pct": [8.2, 6.0, 9.0, 12.0],
            "mae_5d_pct": [-1.0, -2.0, -5.2, -1.5],
            "ordered_mae_before_target_5d_pct": [-1.0, -2.0, None, -1.5],
            "outcome_path_terminal_status": ["target_before_stop", "target_before_stop", "stop_before_target", "target_before_stop"],
            "outcome_path_label_version": [
                ORDERED_OUTCOME_PATH_LABEL_VERSION,
                ORDERED_OUTCOME_PATH_LABEL_VERSION,
                ORDERED_OUTCOME_PATH_LABEL_VERSION,
                "old_version",
            ],
            "return_1d_pct": [1.0, 1.0, -1.0, 2.0],
            "return_5d_pct": [4.0, 3.0, -5.0, 6.0],
        }
    )

    label, valid = _label(df, _profile("ordered_5d_8v5"))

    assert valid.tolist() == [True, True, True, False]
    assert label.tolist() == [True, False, False, True]


def test_ordered_sustain_label_requires_3d_and_5d_positive_closes():
    df = pd.DataFrame(
        {
            "trade_date": ["2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04"],
            "target_before_stop_5d": [True, True, True, True],
            "stop_before_target_5d": [False, False, False, False],
            "mfe_5d_pct": [6.0, 6.0, 6.0, 6.0],
            "mae_5d_pct": [-1.0, -1.0, -1.0, -1.0],
            "ordered_mae_before_target_5d_pct": [-1.0, -1.0, -1.0, -1.0],
            "outcome_path_terminal_status": ["target_before_stop"] * 4,
            "outcome_path_label_version": [
                ORDERED_OUTCOME_PATH_LABEL_VERSION,
                ORDERED_OUTCOME_PATH_LABEL_VERSION,
                ORDERED_OUTCOME_PATH_LABEL_VERSION,
                "old_version",
            ],
            "return_3d_pct": [1.0, -0.1, 1.0, 1.0],
            "return_5d_pct": [2.0, 2.0, -0.1, 2.0],
        }
    )

    label, valid = _label(df, _profile("ordered_5d_5v5_sustain35"))

    assert valid.tolist() == [True, True, True, False]
    assert label.tolist() == [True, False, False, True]


def test_ordered_low_mae_keeps_stop_and_no_touch_rows_as_valid_failures():
    df = pd.DataFrame(
        {
            "trade_date": ["2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04"],
            "target_before_stop_5d": [True, False, False, True],
            "stop_before_target_5d": [False, True, False, False],
            "mfe_5d_pct": [6.0, 2.0, 1.0, 6.0],
            "mae_5d_pct": [-1.0, -4.0, -1.0, -1.0],
            "ordered_mae_before_target_5d_pct": [-1.0, None, None, None],
            "outcome_path_terminal_status": ["target_before_stop", "stop_before_target", "no_touch", "target_before_stop"],
            "outcome_path_label_version": [ORDERED_OUTCOME_PATH_LABEL_VERSION] * 4,
            "return_5d_pct": [2.0, -4.0, 0.5, 2.0],
        }
    )

    label, valid = _label(df, _profile("ordered_5d_5v3_lowmae"))

    assert valid.tolist() == [True, True, True, False]
    assert label.tolist() == [True, False, False, False]


def test_ordered_metrics_drive_promotion_gate():
    df = pd.DataFrame(
        {
            "trade_date": [f"2026-05-{day:02d}" for day in range(1, 31)],
            "target_before_stop_5d": [True] * 24 + [False] * 6,
            "stop_before_target_5d": [False] * 27 + [True] * 3,
            "mfe_5d_pct": [8.0] * 30,
            "mae_5d_pct": [-1.0] * 30,
            "ordered_mfe_until_terminal_5d_pct": [5.0] * 30,
            "ordered_mae_until_terminal_5d_pct": [-1.0] * 30,
            "ordered_mae_before_target_5d_pct": [-1.0] * 24 + [None] * 6,
            "outcome_path_terminal_status": ["target_before_stop"] * 24 + ["no_touch"] * 3 + ["stop_before_target"] * 3,
            "outcome_path_label_version": [ORDERED_OUTCOME_PATH_LABEL_VERSION] * 30,
            "return_1d_pct": [1.0] * 30,
            "return_5d_pct": [4.0] * 30,
        }
    )
    label = pd.Series([True] * 24 + [False] * 6, index=df.index)

    metrics = _metrics(df, df.index, label)
    flags = _promotion_flags(metrics, [75.0, 80.0, 78.0], min_n=30, min_days=10, min_folds=3, require_ordered=True)

    assert metrics["target_before_stop_5d_pct"] == 80.0
    assert metrics["stop_before_target_5d_pct"] == 10.0
    assert metrics["ordered_path_coverage_pct"] == 100.0
    assert flags["promotable"] is True
    assert flags["failed_checks"] == []


def test_ordered_metrics_include_exit_policy_realization():
    df = pd.DataFrame(
        {
            "trade_date": ["2026-05-01", "2026-05-02", "2026-05-03"],
            "target_before_stop_5d": [True, False, False],
            "stop_before_target_5d": [False, True, False],
            "mfe_5d_pct": [7.0, 1.0, 2.0],
            "mae_5d_pct": [-1.0, -4.0, -1.0],
            "ordered_mfe_until_terminal_5d_pct": [5.0, 0.0, 2.0],
            "ordered_mae_until_terminal_5d_pct": [-1.0, -3.0, -1.0],
            "ordered_mae_before_target_5d_pct": [-1.0, None, None],
            "outcome_path_terminal_status": ["target_before_stop", "stop_before_target", "no_touch"],
            "outcome_path_label_version": [ORDERED_OUTCOME_PATH_LABEL_VERSION] * 3,
            "return_1d_pct": [1.0, -1.0, 0.5],
            "return_5d_pct": [4.0, -6.0, 2.0],
        }
    )
    label = pd.Series([True, False, False], index=df.index)

    metrics = _metrics(df, df.index, label, profile=_profile("ordered_5d_5v3_lowmae"))

    assert metrics["exit_policy_target_pct"] == 5.0
    assert metrics["exit_policy_stop_pct"] == -3.0
    assert metrics["win_ordered_exit_5d_pct"] == 66.667
    assert metrics["avg_ordered_exit_5d_pct"] == 1.3333
    assert metrics["min_ordered_exit_5d_pct"] == -3.0


def test_promotion_gate_reports_failed_checks():
    metrics = {
        "n": 41,
        "active_days": 14,
        "ordered_path_coverage_pct": 100.0,
        "ordered_path_label_version": ORDERED_OUTCOME_PATH_LABEL_VERSION,
        "label_win_pct": 73.171,
        "avg_5d_pct": 0.1308,
        "bad_path_pct": 29.268,
        "stop5_pct": 4.878,
        "min_5d_pct": -33.2955,
        "win_ordered_exit_5d_pct": 95.122,
        "avg_ordered_exit_5d_pct": 4.6098,
        "min_ordered_exit_5d_pct": -3.0,
        "outcome_path_warning_pct": 0.0,
    }

    flags = _promotion_flags(metrics, [73.0, 46.667, 80.0], min_n=30, min_days=10, min_folds=3, require_ordered=True)

    assert flags["promotable"] is False
    assert flags["failed_checks"] == ["avg_return_gate", "tail_loss_gate"]
    assert flags["exit_policy_watch"] is True


def test_exit_policy_watch_rejects_high_path_warning_rate():
    metrics = {
        "n": 72,
        "active_days": 16,
        "ordered_path_coverage_pct": 100.0,
        "ordered_path_label_version": ORDERED_OUTCOME_PATH_LABEL_VERSION,
        "label_win_pct": 80.0,
        "avg_5d_pct": 4.0,
        "bad_path_pct": 30.0,
        "stop5_pct": 1.0,
        "min_5d_pct": -10.0,
        "win_ordered_exit_5d_pct": 98.0,
        "avg_ordered_exit_5d_pct": 4.5,
        "min_ordered_exit_5d_pct": -3.0,
        "outcome_path_warning_pct": 70.0,
    }

    flags = _promotion_flags(metrics, [80.0, 82.0, 78.0], min_n=30, min_days=10, min_folds=3, require_ordered=True)

    assert flags["promotable"] is False
    assert flags["failed_checks"] == ["path_warning_gate"]
    assert flags["exit_policy_watch"] is False


def test_load_dataset_prefers_exact_ordered_stop_over_proxy(tmp_path):
    path = tmp_path / "archive.csv"
    pd.DataFrame(
        {
            "ticker": ["005930.KS", "000660.KS"],
            "market": ["KOSPI", "KOSPI"],
            "scan_mode": ["SWING", "SWING"],
            "base_trade_date": ["2026-05-01", "2026-05-01"],
            "priority_rank": [1, 2],
            "return_1d_pct": [1.0, 1.0],
            "return_5d_pct": [2.0, 2.0],
            "min_return_observed_pct": [-8.0, -1.0],
            "target_before_stop_5d": [True, False],
            "stop_before_target_5d": [False, True],
            "outcome_path_terminal_status": ["target_before_stop", "stop_before_target"],
            "outcome_path_label_version": [ORDERED_OUTCOME_PATH_LABEL_VERSION, ORDERED_OUTCOME_PATH_LABEL_VERSION],
            "decision": ["PRIORITY_WATCHLIST", "PRIORITY_WATCHLIST"],
        }
    ).to_csv(path, index=False)

    loaded = _load_dataset(path).sort_values("ticker").reset_index(drop=True)

    first = loaded[loaded["ticker"].eq("005930.KS")].iloc[0]
    second = loaded[loaded["ticker"].eq("000660.KS")].iloc[0]
    assert bool(first["stop5_proxy"]) is False
    assert bool(first["ordered_path_exact"]) is True
    assert bool(second["stop5_proxy"]) is True
