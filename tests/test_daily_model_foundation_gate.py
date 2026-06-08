from __future__ import annotations

import json
from datetime import datetime, timezone

from multi_agent.tools.report_daily_model_foundation_gate import build_report, render_markdown


NOW = datetime(2026, 6, 9, 0, 0, tzinfo=timezone.utc)


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _base_reports(tmp_path, *, dummy_rows: int = 0, production_ready: bool = False) -> None:
    reports = tmp_path
    _write_json(
        reports / "learning" / "learning_cycle_nightly.json",
        {
            "generated_at": "2026-06-08T14:00:00+00:00",
            "action": "dataset_refresh",
            "new_resolved_since_last_cycle": 10,
            "total_resolved": 100,
        },
    )
    _write_json(
        reports / "learning" / "learning_cycle_weekly.json",
        {
            "generated_at": "2026-06-07T00:00:00+00:00",
            "action": "weekly_retrain",
            "new_resolved_since_last_cycle": 20,
            "total_resolved": 100,
        },
    )
    _write_json(
        reports / "learning" / "retrain_v2_report.json",
        {
            "generated_at": "2026-06-07T09:00:00+00:00",
            "execution_status": "trained",
            "rows_loaded": 5000,
            "segments": [
                {
                    "name": "unit",
                    "auc": 0.56,
                    "best_threshold_row": {
                        "threshold": 0.6,
                        "picks": 20,
                        "avg_return": 1.2 if production_ready else -1.2,
                    },
                    "oos_holdout": {
                        "avg_return_pct": 0.7 if production_ready else -0.7,
                        "win_rate_pct": 55.0,
                        "auc": 0.57,
                    },
                }
            ],
        },
    )
    _write_json(
        reports / "validation" / "supabase_scan_data_quality.json",
        {
            "generated_at": "2026-06-08T23:00:00+00:00",
            "kr_swing_rows": 100,
            "kr_swing_dummy_rows": dummy_rows,
            "schema_missing_required_columns": [],
            "kr_swing_computed_complete_rows": 90,
            "kr_swing_computed_complete_with_return3d_rows": 80,
        },
    )
    _write_json(
        reports / "learning" / "kis_model_market_comparison.json",
        {
            "promotion_decision": {
                "status": "production_replacement_candidate" if production_ready else "shadow_only",
                "all_required_markets_production_ready": production_ready,
                "all_required_markets_shadow_display_allowed": True,
                "no_dummy_data": True,
                "market_gate_rows": {
                    "KOSPI": {
                        "production_ready": production_ready,
                        "production_blocking_reasons": [] if production_ready else ["n_lt_30"],
                    },
                    "KOSDAQ": {
                        "production_ready": production_ready,
                        "production_blocking_reasons": [] if production_ready else ["bad_path_gt_15"],
                    },
                },
            }
        },
    )
    for market in ("kospi", "kosdaq"):
        _write_json(
            reports / "validation" / f"kr_walkforward_release_gate_{market}.json",
            {
                "release_ready": production_ready,
                "confidence_level": 0.98,
                "all_checks": []
                if production_ready
                else [{"code": "AVG_RETURN_LOWER", "passed": False}],
            },
        )
    _write_json(
        reports / "validation" / "kr_promotion_challenger_gate.json",
        {
            "summary": {
                "promotion_review_candidate_count": 1 if production_ready else 0,
                "near_candidate_count": 3,
            }
        },
    )


def test_daily_foundation_gate_keeps_kis_shadow_when_promotion_blocks_remain(tmp_path):
    _base_reports(tmp_path, production_ready=False)

    report = build_report(tmp_path, now=NOW)

    assert report["daily_verification_ready"] is True
    assert report["production_promotion_ready"] is False
    assert report["status"] == "shadow_only"
    hard_production = set(report["blocking_reasons"]["hard_production"])
    assert {
        "KIS_PROMOTION_READY",
        "KOSPI_WALKFORWARD_RELEASE",
        "KOSDAQ_WALKFORWARD_RELEASE",
        "PROMOTION_CHALLENGER_CANDIDATE",
        "RETRAIN_THRESHOLD_RETURN_POSITIVE",
        "RETRAIN_OOS_RETURN_POSITIVE",
    } <= hard_production
    assert report["recommended_action"] == "keep_existing_production_and_run_daily_shadow_verification"


def test_daily_foundation_gate_allows_production_only_when_every_gate_passes(tmp_path):
    _base_reports(tmp_path, production_ready=True)

    report = build_report(tmp_path, now=NOW)

    assert report["daily_verification_ready"] is True
    assert report["production_promotion_ready"] is True
    assert report["status"] == "production_ready"
    assert report["blocking_reasons"]["hard_daily"] == []
    assert report["blocking_reasons"]["hard_production"] == []
    markdown = render_markdown(report)
    assert "Daily Model Foundation Gate" in markdown
    assert "production_promotion_ready: True" in markdown


def test_daily_foundation_gate_blocks_daily_when_dummy_rows_exist(tmp_path):
    _base_reports(tmp_path, dummy_rows=2, production_ready=True)

    report = build_report(tmp_path, now=NOW)

    assert report["daily_verification_ready"] is False
    assert report["production_promotion_ready"] is False
    assert report["status"] == "blocked"
    assert report["no_dummy_data"] is False
    assert "NO_DUMMY_SCAN_ROWS" in report["blocking_reasons"]["hard_daily"]
