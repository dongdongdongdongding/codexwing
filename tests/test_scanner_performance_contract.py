import json

from modules.scanner_performance_contract import (
    PerformanceMetric,
    format_metric,
    latest_section_metric,
    live_policy_summary,
    min_samples_for_horizon,
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


def test_live_policy_summary_prefers_practical_gate_for_strict_operator_view(tmp_path, monkeypatch):
    cohort_path = tmp_path / "scan_cohort.json"
    cohort_path.write_text(
        json.dumps(
            {
                "markets": {
                    "KOSPI": {
                        "cohorts": {
                            "Practical 80 Gate": {
                                "horizons": {
                                    "5D": {
                                        "n": 42,
                                        "win_pct": 81.25,
                                        "avg_pct": 8.1234,
                                    }
                                },
                                "path": {"bad_path_pct": 12.5},
                            }
                        }
                    },
                    "KOSDAQ": {
                        "cohorts": {
                            "Practical 80 Gate": {
                                "horizons": {
                                    "5D": {
                                        "n": 14,
                                        "win_pct": 92.857,
                                        "avg_pct": 19.9478,
                                    }
                                },
                                "path": {"bad_path_pct": 7.143},
                            }
                        }
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("modules.scanner_performance_contract.SCAN_COHORT_PERFORMANCE_PATH", cohort_path)

    kospi = live_policy_summary("KOSPI", strict_quality_gate=True)
    kosdaq = live_policy_summary("KOSDAQ", strict_quality_gate=True)

    assert kospi["policy"] == "Practical 80 Gate"
    assert kospi["validated_win"] == "81.2%"
    assert kospi["validated_return"] == "+8.12%"
    assert kospi["sample"] == "n=42 · bad 12.5%"
    assert kospi["quality_scope"] == "scan_cohort_practical_gate"
    assert kospi["validation_pass"] is True
    assert kosdaq["sample"] == "n=14 · bad 7.1% · small_sample"
    assert kosdaq["validation_pass"] is False


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


def test_long_horizon_metrics_require_mature_samples_and_active_days():
    immature_30d = PerformanceMetric(
        market="KOSPI",
        scan_mode="SWING",
        section="Top5",
        horizon_days=30,
        sample_n=179,
        win_rate_pct=90.0,
        avg_return_pct=9.0,
        median_return_pct=8.0,
        avg_win_return_pct=None,
        avg_loss_return_pct=None,
        best_return_pct=25.0,
        worst_return_pct=-3.0,
        source="test",
        active_day_n=20,
    )
    mature_14d = PerformanceMetric(
        market="KOSDAQ",
        scan_mode="SWING",
        section="Exception Leader",
        horizon_days=14,
        sample_n=120,
        win_rate_pct=75.0,
        avg_return_pct=6.0,
        median_return_pct=5.0,
        avg_win_return_pct=None,
        avg_loss_return_pct=None,
        best_return_pct=18.0,
        worst_return_pct=-4.0,
        source="test",
        active_day_n=8,
    )
    active_day_immature_14d = PerformanceMetric(
        market="KOSDAQ",
        scan_mode="SWING",
        section="Exception Leader",
        horizon_days=14,
        sample_n=140,
        win_rate_pct=75.0,
        avg_return_pct=6.0,
        median_return_pct=5.0,
        avg_win_return_pct=None,
        avg_loss_return_pct=None,
        best_return_pct=18.0,
        worst_return_pct=-4.0,
        source="test",
        active_day_n=7,
    )

    assert min_samples_for_horizon(30) == 180
    assert immature_30d.production_pass is False
    assert profile_level(immature_30d) == "immature"
    assert "gate n 179/180" in format_metric(immature_30d, horizon_label="30D")

    assert mature_14d.production_pass is True
    assert profile_level(mature_14d) == "pass"

    assert active_day_immature_14d.production_pass is False
    assert profile_level(active_day_immature_14d) == "immature"
