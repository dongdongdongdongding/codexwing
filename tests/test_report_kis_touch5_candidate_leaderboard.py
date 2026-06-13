from __future__ import annotations

import json
from pathlib import Path

from multi_agent.tools import report_kis_touch5_candidate_leaderboard as tool


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _candidate(
    *,
    market: str,
    rule: str,
    n: int,
    active_days: int,
    active_runs: int,
    hit5: float,
    avg5: float,
    low5: float,
    feature_set: str = "kis_sidecar_failure_risk_augmented",
) -> dict:
    return {
        "market": market,
        "label": "touch5_dd10_5d",
        "feature_set": feature_set,
        "model": "lightgbm",
        "selection_rule": rule,
        "topn": 1,
        "metrics": {
            "n": n,
            "active_days": active_days,
            "active_runs": active_runs,
            "buy_premium_pct": 2.0,
            "hit5_dd10_5d_pct": hit5,
            "hit10_5d_pct": hit5,
            "avg_5d_pct": avg5,
            "min_min_low_5d_pct": low5,
            "avg_max_high_5d_pct": max(avg5, 5.0),
            "target_before_stop_5d_pct": hit5,
            "stop_before_target_5d_pct": max(100.0 - hit5, 0.0),
        },
    }


def _current_comparison(path: Path) -> None:
    _write_json(
        path,
        {
            "markets": {
                "KOSDAQ": {
                    "source_path": "current.json",
                    "current_kis_model": {
                        "identity": {
                            "market": "KOSDAQ",
                            "label": "touch5_dd10_5d",
                            "feature_set": "kis_sidecar_failure_risk_augmented",
                            "model": "lightgbm",
                            "selection_rule": "top1_p0p75_tail0p85",
                            "topn": 1,
                        },
                        "metrics": _candidate(
                            market="KOSDAQ",
                            rule="top1_p0p75_tail0p85",
                            n=19,
                            active_days=9,
                            active_runs=19,
                            hit5=100.0,
                            avg5=15.45,
                            low5=-7.0,
                        )["metrics"],
                    },
                }
            }
        },
    )


def test_leaderboard_finds_shadow_upgrade_when_sample_progress_improves(tmp_path) -> None:
    source = tmp_path / "scan_universe_admission_challenger_touch5_dd10_kis_tailgate.json"
    current = tmp_path / "kis_model_market_comparison.json"
    _current_comparison(current)
    _write_json(
        source,
        {
            "top_results": [
                _candidate(
                    market="KOSDAQ",
                    rule="top2_p0p50_tail0p90",
                    n=40,
                    active_days=11,
                    active_runs=20,
                    hit5=100.0,
                    avg5=20.41,
                    low5=-9.3,
                )
            ]
        },
    )

    report = tool.build_report(report_paths=[source], current_comparison_path=current)

    assert report["decision"]["status"] == "shadow_upgrade_candidate_found"
    market = report["markets"]["KOSDAQ"]
    assert market["verified_upgrade_candidate"]["identity"]["selection_rule"] == "top2_p0p50_tail0p90"
    assert market["verified_upgrade_candidate"]["sample_progress"]["completion_pct"] > market["current"]["sample_progress"]["completion_pct"]
    assert report["decision"]["production_replacement_ready"] is False


def test_leaderboard_marks_production_candidate_separately(tmp_path) -> None:
    source = tmp_path / "kis_sidecar_threshold_sweep_touch5_dd10.json"
    current = tmp_path / "kis_model_market_comparison.json"
    _current_comparison(current)
    _write_json(
        source,
        {
            "market_reports": [
                {
                    "results": [
                        _candidate(
                            market="KOSDAQ",
                            rule="top1_ready",
                            n=60,
                            active_days=24,
                            active_runs=24,
                            hit5=78.0,
                            avg5=12.0,
                            low5=-9.8,
                        )
                    ]
                }
            ]
        },
    )

    report = tool.build_report(report_paths=[source], current_comparison_path=current)

    assert report["decision"]["status"] == "production_candidate_found"
    assert report["decision"]["production_replacement_ready"] is True
    assert report["markets"]["KOSDAQ"]["production_ready_count"] == 1


def test_leaderboard_surfaces_high_precision_sample_only_candidate(tmp_path) -> None:
    source = tmp_path / "kis_sidecar_threshold_sweep_touch5_dd10.json"
    current = tmp_path / "kis_model_market_comparison.json"
    _current_comparison(current)
    _write_json(
        source,
        {
            "top_results": [
                _candidate(
                    market="KOSDAQ",
                    rule="sample_progress_candidate",
                    n=50,
                    active_days=12,
                    active_runs=50,
                    hit5=80.0,
                    avg5=6.0,
                    low5=-8.0,
                ),
                _candidate(
                    market="KOSDAQ",
                    rule="high_precision_candidate",
                    n=50,
                    active_days=10,
                    active_runs=50,
                    hit5=95.0,
                    avg5=7.0,
                    low5=-7.0,
                ),
            ]
        },
    )

    report = tool.build_report(report_paths=[source], current_comparison_path=current, tracked_sources_only=False)
    market = report["markets"]["KOSDAQ"]

    assert report["tracked_sources_only"] is False
    assert report["inputs"]["source_mode"] == "all_files"
    assert market["best_sample_only_shadow"]["identity"]["selection_rule"] == "sample_progress_candidate"
    assert market["best_high_precision_shadow"]["identity"]["selection_rule"] == "high_precision_candidate"


def test_leaderboard_rejects_sample_progress_when_avg5_regresses(tmp_path) -> None:
    source = tmp_path / "scan_universe_admission_challenger_touch5_dd10_kis_tailgate.json"
    current = tmp_path / "kis_model_market_comparison.json"
    _current_comparison(current)
    _write_json(
        source,
        {
            "top_results": [
                _candidate(
                    market="KOSDAQ",
                    rule="top2_more_sample_lower_avg",
                    n=40,
                    active_days=11,
                    active_runs=20,
                    hit5=100.0,
                    avg5=10.0,
                    low5=-8.0,
                )
            ]
        },
    )

    report = tool.build_report(report_paths=[source], current_comparison_path=current)

    assert report["decision"]["status"] == "keep_current_shadow"
    assert report["markets"]["KOSDAQ"]["verified_upgrade_candidate"] is None


def test_discover_report_paths_excludes_untracked_noise_by_name(tmp_path) -> None:
    kept = tmp_path / "scan_universe_admission_challenger_touch5_dd10_kis_tailgate.json"
    excluded = tmp_path / "kis_shadow_admission_model_deployment_touch5_dd10.json"
    kept.write_text("{}", encoding="utf-8")
    excluded.write_text("{}", encoding="utf-8")

    paths = tool.discover_report_paths(tmp_path, tracked_only=False)

    assert paths == [kept]
