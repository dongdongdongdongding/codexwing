import pandas as pd

from multi_agent.tools.train_scan_universe_admission_challenger import (
    LABEL_SPECS,
    candidate_verdict,
    current_top_indices,
    label_series,
    metrics,
    prepare_dataset,
    top_indices_by_run,
)


def _spec(name):
    return next(item for item in LABEL_SPECS if item.name == name)


def test_prepare_dataset_and_labels_use_scan_universe_path_fields():
    raw = pd.DataFrame(
        [
            {
                "id": 1,
                "run_id": "RUN-A",
                "ticker": "000001.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "base_trade_date": "2026-05-20",
                "row_role": "emitted",
                "priority_rank": 1,
                "return_1d_pct": 1.0,
                "return_3d_pct": 2.0,
                "return_5d_pct": 3.0,
                "min_low_return_5d_pct": -2.0,
                "target_before_stop_5d": True,
                "stop_before_target_5d": False,
            },
            {
                "id": 2,
                "run_id": "RUN-A",
                "ticker": "000002.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "base_trade_date": "2026-05-20",
                "row_role": "rejected",
                "return_1d_pct": -1.0,
                "return_3d_pct": -2.0,
                "return_5d_pct": -3.0,
                "min_low_return_5d_pct": -6.0,
                "target_before_stop_5d": False,
                "stop_before_target_5d": True,
            },
        ]
    )

    df, sanity = prepare_dataset(raw)
    target, valid = label_series(df, _spec("target_first_sustain_5d"))
    clean, clean_valid = label_series(df, _spec("sustain_1_3_5_lowdd"))

    assert sanity["removed_rows"] == 0
    assert valid.tolist() == [True, True]
    assert target.tolist() == [True, False]
    assert clean_valid.tolist() == [True, True]
    assert clean.tolist() == [True, False]
    assert df["bad_path"].tolist() == [False, True]


def test_top_indices_and_metrics_report_all_horizons():
    raw = pd.DataFrame(
        [
            {
                "id": 1,
                "run_id": "RUN-A",
                "ticker": "000001.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "base_trade_date": "2026-05-20",
                "row_role": "emitted",
                "priority_rank": 1,
                "decision_score": 10,
                "return_1d_pct": 1.0,
                "return_3d_pct": 3.0,
                "return_5d_pct": 5.0,
                "min_low_return_5d_pct": -1.0,
                "max_high_return_5d_pct": 7.0,
                "target_before_stop_5d": True,
                "stop_before_target_5d": False,
            },
            {
                "id": 2,
                "run_id": "RUN-A",
                "ticker": "000002.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "base_trade_date": "2026-05-20",
                "row_role": "emitted",
                "priority_rank": 2,
                "decision_score": 20,
                "return_1d_pct": -2.0,
                "return_3d_pct": -4.0,
                "return_5d_pct": -6.0,
                "min_low_return_5d_pct": -8.0,
                "max_high_return_5d_pct": 1.0,
                "target_before_stop_5d": False,
                "stop_before_target_5d": True,
            },
        ]
    )
    df, _sanity = prepare_dataset(raw)
    label, _valid = label_series(df, _spec("pos_5d"))
    idx = top_indices_by_run(df, pd.Series([0.9, 0.1], index=df.index), 1)
    current_idx = current_top_indices(df, 1, include_exception=False)

    got = metrics(df, idx, label)
    current = metrics(df, current_idx, label)

    assert got["n"] == 1
    assert got["win_1d_pct"] == 100.0
    assert got["avg_5d_pct"] == 5.0
    assert got["min_5d_pct"] == 5.0
    assert got["max_5d_pct"] == 5.0
    assert got["target_before_stop_5d_pct"] == 100.0
    assert current["avg_5d_pct"] == 5.0


def test_prepare_dataset_filters_impossible_kr_return_labels():
    raw = pd.DataFrame(
        [
            {
                "id": 1,
                "run_id": "RUN-A",
                "ticker": "000001.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "base_trade_date": "2026-05-20",
                "return_1d_pct": 1.0,
                "return_3d_pct": 2.0,
                "return_5d_pct": 3.0,
            },
            {
                "id": 2,
                "run_id": "RUN-A",
                "ticker": "000002.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "base_trade_date": "2026-05-20",
                "return_1d_pct": 900.0,
                "return_3d_pct": 900.0,
                "return_5d_pct": 900.0,
            },
        ]
    )

    df, sanity = prepare_dataset(raw)

    assert df["ticker"].tolist() == ["000001.KS"]
    assert sanity["removed_rows"] == 1
    assert sanity["column_violations"]["return_1d_pct"] == 1


def test_prepare_dataset_empty_result_still_returns_sanity_tuple():
    raw = pd.DataFrame(
        [
            {
                "ticker": "AAPL",
                "market": "NASDAQ",
                "scan_mode": "SWING",
                "base_trade_date": "2026-05-20",
            }
        ]
    )

    df, sanity = prepare_dataset(raw)

    assert df.empty
    assert sanity["removed_rows"] == 0


def test_candidate_verdict_blocks_sparse_high_score_candidate():
    sparse = {
        "topn": 1,
        "metrics": {
            "n": 7,
            "active_runs": 7,
            "active_days": 3,
            "win_3d_pct": 100.0,
            "win_5d_pct": 100.0,
            "avg_3d_pct": 10.0,
            "avg_5d_pct": 10.0,
            "min_1d_pct": -1.0,
            "min_5d_pct": 1.0,
            "stop5_pct": 0.0,
        },
    }
    stable = {
        "topn": 1,
        "metrics": {
            "n": 18,
            "active_runs": 15,
            "active_days": 8,
            "win_3d_pct": 90.0,
            "win_5d_pct": 90.0,
            "avg_3d_pct": 7.0,
            "avg_5d_pct": 8.0,
            "min_1d_pct": 0.0,
            "min_5d_pct": -4.0,
            "stop5_pct": 0.0,
        },
    }

    assert candidate_verdict(sparse)["promotable"] is False
    assert "sample_too_small" in candidate_verdict(sparse)["blocking_reasons"]
    assert candidate_verdict(stable)["promotable"] is True
