import json

from modules.scanner_performance_contract import (
    format_metric,
    latest_section_metric,
    live_policy_summary,
    profile_level,
    slice_metric,
)


def test_latest_section_metric_uses_latest_as_of_date(tmp_path):
    path = tmp_path / "sections.json"
    path.write_text(
        json.dumps(
            [
                {
                    "as_of_date": "2026-05-19",
                    "generated_at": "2026-05-19T00:00:00Z",
                    "market": "KOSPI",
                    "section": "Exception Leader",
                    "horizon_days": 5,
                    "sample_n": 10,
                    "win_rate_pct": 70.0,
                    "avg_return_pct": 4.0,
                    "best_return_pct": 10.0,
                    "worst_return_pct": -2.0,
                },
                {
                    "as_of_date": "2026-05-20",
                    "generated_at": "2026-05-20T00:00:00Z",
                    "market": "KOSPI",
                    "scan_mode": "SWING",
                    "section": "Exception Leader",
                    "horizon_days": 5,
                    "sample_n": 31,
                    "win_rate_pct": 80.0,
                    "avg_return_pct": 7.5,
                    "best_return_pct": 20.0,
                    "worst_return_pct": -5.0,
                },
            ]
        ),
        encoding="utf-8",
    )

    metric = latest_section_metric("KOSPI", "Exception Leader", horizon_days=5, path=path)

    assert metric is not None
    assert metric.sample_n == 31
    assert metric.production_pass is True
    assert profile_level(metric) == "pass"
    assert "win5D 80.0%" in format_metric(metric)


def test_latest_section_metric_filters_scan_mode(tmp_path):
    path = tmp_path / "sections.json"
    path.write_text(
        json.dumps(
            [
                {
                    "as_of_date": "2026-05-20",
                    "generated_at": "2026-05-20T00:00:00Z",
                    "market": "KOSPI",
                    "scan_mode": "SWING",
                    "section": "Top5",
                    "horizon_days": 5,
                    "sample_n": 30,
                    "win_rate_pct": 80.0,
                    "avg_return_pct": 5.0,
                },
                {
                    "as_of_date": "2026-05-20",
                    "generated_at": "2026-05-20T00:00:00Z",
                    "market": "KOSPI",
                    "scan_mode": "INTRADAY",
                    "section": "Top5",
                    "horizon_days": 5,
                    "sample_n": 30,
                    "win_rate_pct": 20.0,
                    "avg_return_pct": -5.0,
                },
            ]
        ),
        encoding="utf-8",
    )

    swing = latest_section_metric("KOSPI", "Top5", horizon_days=5, path=path)
    intraday = latest_section_metric("KOSPI", "Top5", horizon_days=5, scan_mode="INTRADAY", path=path)

    assert swing is not None
    assert intraday is not None
    assert swing.scan_mode == "SWING"
    assert swing.win_rate_pct == 80.0
    assert intraday.scan_mode == "INTRADAY"
    assert intraday.win_rate_pct == 20.0


def test_live_policy_summary_reads_selected_quality_scope(tmp_path, monkeypatch):
    observed = tmp_path / "observed.json"
    strict = tmp_path / "strict.json"
    payload = {
        "quality_scope": "observed_archive",
        "policies": [
            {
                "market": "KOSDAQ",
                "policy": "exception_leader AND trend=UP",
                "target_rows": 102,
                "win_5d_pct": 59.649,
                "avg_return_5d_pct": 2.4293,
                "loss_5pct_or_worse_5d_pct": 32.456,
                "passes_goal": True,
                "close_5d_quality_pass": False,
            }
        ],
    }
    observed.write_text(json.dumps(payload), encoding="utf-8")
    strict.write_text(json.dumps({"quality_scope": "strict_feature_complete", "policies": []}), encoding="utf-8")
    monkeypatch.setattr("modules.scanner_performance_contract.LIVE_POLICY_OBSERVED_PATH", observed)
    monkeypatch.setattr("modules.scanner_performance_contract.LIVE_POLICY_STRICT_PATH", strict)

    summary = live_policy_summary("KOSDAQ", strict_quality_gate=False)

    assert summary["validated_win"] == "59.6%"
    assert summary["validated_return"] == "+2.43%"
    assert summary["sample"] == "n=102 · loss5 32.5%"
    assert summary["validation_pass"] is False


def test_slice_metric_reads_validation_slice(tmp_path, monkeypatch):
    path = tmp_path / "kospi_slice.json"
    path.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-20T00:00:00Z",
                "slices": [
                    {
                        "slice": "rank_top5__edge_ge_7",
                        "n": 55,
                        "win_5d_pct": 80.0,
                        "avg_5d_pct": 8.99,
                        "median_5d_pct": 7.1,
                        "min_5d_pct": -8.0,
                        "max_5d_pct": 30.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setitem(
        __import__("modules.scanner_performance_contract", fromlist=["SLICE_VALIDATION_PATHS"]).SLICE_VALIDATION_PATHS,
        "KOSPI",
        path,
    )

    metric = slice_metric("KOSPI", "rank_top5__edge_ge_7")

    assert metric is not None
    assert metric.sample_n == 55
    assert profile_level(metric) == "pass"
