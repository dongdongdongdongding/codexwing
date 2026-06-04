from __future__ import annotations

import json

from multi_agent.tools.report_kis_consumer_parity import build_report, render_markdown


def _write_run(shared_dir, run_id, *, candidate):
    run_dir = shared_dir / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "scanner_handoff.json").write_text(
        json.dumps(
            {
                "run_context": {"run_id": run_id, "market": "KOSPI"},
                "candidates": [candidate],
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "planner_handoff.json").write_text(
        json.dumps(
            {
                "run_context": {"run_id": run_id, "market": "KOSPI"},
                "decisions": [{"ticker": candidate["ticker"], "priority_rank": 1}],
            }
        ),
        encoding="utf-8",
    )


def test_consumer_parity_report_accepts_matching_sidecar_locations(tmp_path):
    sidecar = {
        "feature_origin": "kis_openapi_sidecar",
        "coverage": {"quote_snapshot": True, "daily_ohlcv": True},
        "model_candidate_features": {"kis_value_traded": 123.0},
        "replacement_readiness": {"model_sidecar_ready": True, "production_replacement_ready": True},
    }
    _write_run(
        tmp_path,
        "RUN-KIS",
        candidate={
            "ticker": "005930.KS",
            "leader_metrics": {"kis_sidecar": sidecar},
            "feature_snapshot": {
                "kis_sidecar": sidecar,
                "leader_metrics": {"kis_sidecar": sidecar},
            },
        },
    )

    report = build_report(shared_dir=tmp_path, limit_runs=5)

    assert report["summary"]["scanner_candidate_count"] == 1
    assert report["summary"]["scanner_sidecar_candidate_count"] == 1
    assert report["summary"]["scanner_sidecar_model_ready_candidate_count"] == 1
    assert report["summary"]["scanner_sidecar_production_ready_candidate_count"] == 1
    assert report["summary"]["error_count"] == 0
    assert report["db_contract"]["payload_preserves_feature_snapshot"] is True
    assert report["db_contract"]["payload_preserves_leader_metrics"] is True


def test_consumer_parity_report_blocks_dummy_marker(tmp_path):
    sidecar = {
        "feature_origin": "kis_openapi_sidecar",
        "is_dummy_data": True,
    }
    _write_run(
        tmp_path,
        "RUN-DUMMY",
        candidate={
            "ticker": "005930.KS",
            "leader_metrics": {"kis_sidecar": sidecar},
            "feature_snapshot": {
                "kis_sidecar": sidecar,
                "leader_metrics": {"kis_sidecar": sidecar},
            },
        },
    )

    report = build_report(shared_dir=tmp_path, limit_runs=5)
    markdown = render_markdown(report)

    assert report["summary"]["error_count"] >= 1
    assert any(issue["code"] == "DUMMY_MARKER_PRESENT" for issue in report["issues"])
    assert "DUMMY_MARKER_PRESENT" in markdown


def test_consumer_parity_report_blocks_empty_kis_sidecar(tmp_path):
    sidecar = {
        "feature_origin": "kis_openapi_sidecar",
        "coverage": {"quote_snapshot": False, "daily_ohlcv": False},
        "replacement_readiness": {"model_sidecar_ready": False, "production_replacement_ready": False},
        "warnings": ["price_snapshot_ready=false", "scanner_daily_ready=false"],
    }
    _write_run(
        tmp_path,
        "RUN-EMPTY-SIDECAR",
        candidate={
            "ticker": "005930.KS",
            "leader_metrics": {"kis_sidecar": sidecar},
            "feature_snapshot": {
                "kis_sidecar": sidecar,
                "leader_metrics": {"kis_sidecar": sidecar},
            },
        },
    )

    report = build_report(shared_dir=tmp_path, limit_runs=5)

    assert report["summary"]["scanner_sidecar_candidate_count"] == 1
    assert report["summary"]["scanner_sidecar_model_ready_candidate_count"] == 0
    assert any(issue["code"] == "KIS_SIDECAR_MINIMUM_COVERAGE_MISSING" for issue in report["issues"])


def test_consumer_parity_report_warns_when_recent_runs_have_no_sidecar(tmp_path):
    _write_run(
        tmp_path,
        "RUN-LEGACY",
        candidate={
            "ticker": "005930.KS",
            "leader_metrics": {},
            "feature_snapshot": {},
        },
    )

    report = build_report(shared_dir=tmp_path, limit_runs=5)

    assert report["summary"]["scanner_sidecar_candidate_count"] == 0
    assert any(issue["code"] == "NO_LIVE_KIS_SIDECAR_ARTIFACTS_YET" for issue in report["issues"])
