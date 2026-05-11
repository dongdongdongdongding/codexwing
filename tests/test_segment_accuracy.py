import json

from modules import segment_accuracy


def test_segment_accuracy_uses_live_archive_rows_for_multi_horizon(tmp_path, monkeypatch):
    dataset = tmp_path / "scan_archive_learning_dataset_all.json"
    rows = [
        {
            "ticker": "005930.KS",
            "market": "KOSPI",
            "scan_mode": "SWING",
            "decision_bucket": "picked",
            "outcome_status": "RESOLVED",
            "return_1d_pct": 1.0,
            "return_5d_pct": 2.0,
            "return_14d_pct": -1.0,
            "created_at": "2026-05-01T09:00:00",
        },
        {
            "ticker": "000660.KS",
            "market": "KOSPI",
            "scan_mode": "SWING",
            "decision_bucket": "picked",
            "outcome_status": "RESOLVED",
            "return_1d_pct": -1.0,
            "return_5d_pct": 3.0,
            "return_14d_pct": 4.0,
            "created_at": "2026-05-02T09:00:00",
        },
        {
            "ticker": "035420.KS",
            "market": "KOSPI",
            "scan_mode": "SWING",
            "decision_bucket": "picked",
            "outcome_status": "PENDING",
            "return_5d_pct": 10.0,
            "created_at": "2026-05-03T09:00:00",
        },
    ]
    dataset.write_text(json.dumps(rows), encoding="utf-8")

    monkeypatch.setattr(segment_accuracy, "_DATASET_PATH", dataset)
    monkeypatch.setattr(segment_accuracy, "_MIN_SAMPLE_SIZE", 1)
    monkeypatch.setenv("AG_SEGMENT_ACCURACY_SOURCE", "archive")
    segment_accuracy.force_reload()

    assert segment_accuracy.lookup_segment_win_rate("PRIORITY_WATCHLIST", "KOSPI", "SWING", horizon_days=5) == 100.0
    assert segment_accuracy.lookup_segment_win_rate("PRIORITY_WATCHLIST", "KOSPI", "SWING", horizon_days=1) == 50.0
    assert segment_accuracy.lookup_segment_win_rate("PRIORITY_WATCHLIST", "KOSPI", "SWING", horizon_days=14) == 50.0
    assert segment_accuracy.get_segment_sample_size("PRIORITY_WATCHLIST", "KOSPI", "SWING", horizon_days=5) == 2

    snapshot = segment_accuracy.get_segment_accuracy_snapshot()
    assert snapshot["source"] == "archive"
    assert snapshot["rows_loaded"] == 3
    assert snapshot["resolved_rows"] == 2
    assert snapshot["horizon_counts"][5] == 2


def test_segment_accuracy_respects_min_sample_size(tmp_path, monkeypatch):
    dataset = tmp_path / "scan_archive_learning_dataset_all.json"
    dataset.write_text(
        json.dumps(
            [
                {
                    "ticker": "322310.KQ",
                    "market": "KOSDAQ",
                    "scan_mode": "SWING",
                    "decision_bucket": "exception_leader",
                    "outcome_status": "RESOLVED",
                    "return_5d_pct": 12.0,
                }
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(segment_accuracy, "_DATASET_PATH", dataset)
    monkeypatch.setattr(segment_accuracy, "_MIN_SAMPLE_SIZE", 2)
    monkeypatch.setenv("AG_SEGMENT_ACCURACY_SOURCE", "archive")
    segment_accuracy.force_reload()

    assert segment_accuracy.lookup_segment_win_rate("EXCEPTION_LEADER", "KOSDAQ", "SWING", horizon_days=5) is None
    assert segment_accuracy.get_segment_sample_size("EXCEPTION_LEADER", "KOSDAQ", "SWING", horizon_days=5) == 1
