from __future__ import annotations

import json

from multi_agent.tools.report_kis_operational_readiness import build_report, render_markdown


def _write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_kis_operational_readiness_combines_full_and_retry_evidence(tmp_path):
    _write_json(
        tmp_path / "kis_kr_universe_readiness_20260604_100000.json",
        {
            "run_id": "20260604_100000",
            "requested_tickers": [],
            "universe": {
                "KOSPI": {"selected_count": 2},
                "KOSDAQ": {"selected_count": 2},
            },
            "quote_summary": {
                "KOSPI": {
                    "universe_count": 2,
                    "quote_ok_count": 1,
                    "quote_error_count": 1,
                    "quote_success_rate_pct": 50.0,
                    "core_field_missing_count": {"sector_name": 1},
                },
                "KOSDAQ": {
                    "universe_count": 2,
                    "quote_ok_count": 2,
                    "quote_error_count": 0,
                    "quote_success_rate_pct": 100.0,
                    "core_field_missing_count": {"sector_name": 0},
                },
            },
            "feature_checks": [
                {"name": "KOSPI:volume_rank", "ok": True},
                {"name": "KOSPI:005930.KS:investor_flow_snapshot", "ok": False, "error": "TIME LIMIT"},
            ],
        },
    )
    _write_json(
        tmp_path / "kis_kr_universe_readiness_20260604_101000.json",
        {
            "run_id": "20260604_101000",
            "requested_tickers": [{"market": "KOSPI", "ticker": "000001.KS"}],
            "universe": {
                "KOSPI": {"selected_count": 1},
                "KOSDAQ": {"selected_count": 0},
            },
            "quote_summary": {
                "KOSPI": {
                    "universe_count": 1,
                    "quote_ok_count": 1,
                    "quote_error_count": 0,
                    "quote_success_rate_pct": 100.0,
                    "core_field_missing_count": {"sector_name": 0},
                }
            },
            "feature_checks": [],
        },
    )

    report = build_report(tmp_path)

    assert report["quote_coverage"]["total_effective_quote_ok_count"] == 4
    assert report["quote_coverage"]["total_effective_quote_success_rate_pct"] == 100.0
    assert report["endpoint_rollup"]["failed_count"] == 1
    assert report["summary"]["model_lift_status"].startswith("모델 개선 가능성")
    assert "partial_time_gated" in {row["readiness"] for row in report["blockers_or_gaps"]}


def test_kis_operational_readiness_uses_post_close_flow_and_kosdaq_rank_evidence(tmp_path):
    _write_json(
        tmp_path / "kis_kr_universe_readiness_20260605_190000.json",
        {
            "run_id": "20260605_190000",
            "requested_tickers": [],
            "universe": {
                "KOSPI": {"selected_count": 2},
                "KOSDAQ": {"selected_count": 2},
            },
            "quote_summary": {
                "KOSPI": {"universe_count": 2, "quote_ok_count": 2, "quote_error_count": 0},
                "KOSDAQ": {"universe_count": 2, "quote_ok_count": 2, "quote_error_count": 0},
            },
            "feature_checks": [
                {"name": "KOSPI:005930.KS:investor_flow_snapshot", "ok": True, "row_count": 1},
                {"name": "KOSDAQ:035720.KQ:investor_flow_snapshot", "ok": True, "row_count": 1},
                {"name": "KOSDAQ:volume_rank", "ok": True, "row_count": 30},
            ],
        },
    )

    report = build_report(tmp_path)
    readiness = {row["area"]: row["readiness"] for row in report["requirement_matrix"]}

    assert report["post_close_feature_evidence"]["investor_flow_snapshot"]["ok_count"] == 2
    assert report["post_close_feature_evidence"]["kosdaq_volume_rank"]["row_count"] == 30
    assert readiness["investor_flow"] == "ready_post_close_sampled"
    assert readiness["rank_and_market_microstructure"] == "ready_with_verified_kosdaq_params"
    assert "partial_time_gated" not in {row["readiness"] for row in report["blockers_or_gaps"]}


def test_kis_operational_readiness_uses_latest_feature_checks_even_with_older_full_sweep(tmp_path):
    _write_json(
        tmp_path / "kis_kr_universe_readiness_20260604_100000.json",
        {
            "run_id": "20260604_100000",
            "requested_tickers": [],
            "universe": {"KOSPI": {"selected_count": 835}, "KOSDAQ": {"selected_count": 1719}},
            "quote_summary": {
                "KOSPI": {"universe_count": 835, "quote_ok_count": 835, "quote_error_count": 0},
                "KOSDAQ": {"universe_count": 1719, "quote_ok_count": 1719, "quote_error_count": 0},
            },
            "feature_checks": [
                {"name": "KOSDAQ:volume_rank", "ok": True, "row_count": 1},
            ],
        },
    )
    _write_json(
        tmp_path / "kis_kr_universe_readiness_20260605_195145.json",
        {
            "run_id": "20260605_195145",
            "requested_tickers": [],
            "universe": {"KOSPI": {"selected_count": 3}, "KOSDAQ": {"selected_count": 3}},
            "quote_summary": {
                "KOSPI": {"universe_count": 3, "quote_ok_count": 3, "quote_error_count": 0},
                "KOSDAQ": {"universe_count": 3, "quote_ok_count": 3, "quote_error_count": 0},
            },
            "feature_checks": [
                {"name": "KOSPI:005930.KS:investor_flow_snapshot", "ok": True, "row_count": 0},
                {"name": "KOSDAQ:196170.KQ:investor_flow_snapshot", "ok": True, "row_count": 0},
                {"name": "KOSDAQ:volume_rank", "ok": True, "row_count": 30},
            ],
        },
    )

    report = build_report(tmp_path)

    assert report["quote_coverage"]["total_universe_count"] == 2554
    assert report["source_reports"]["feature_checks"].endswith("20260605_195145.json")
    assert report["post_close_feature_evidence"]["kosdaq_volume_rank"]["row_count"] == 30


def test_kis_operational_readiness_markdown_contains_korean_conclusion(tmp_path):
    report = {
        "summary": {
            "operational_replacement_verdict": "Do not switch all KR operations to KIS yet.",
            "smooth_operation_status": "quote works.",
            "model_lift_status": "possible.",
        },
        "quote_coverage": {
            "total_effective_quote_ok_count": 1,
            "total_universe_count": 1,
            "total_effective_quote_success_rate_pct": 100.0,
            "markets": {},
        },
        "endpoint_rollup": {"ok_count": 1, "checked_count": 1, "failed_count": 0, "failed": []},
        "post_close_feature_evidence": {
            "investor_flow_snapshot": {"ok_count": 1, "checked_count": 1},
            "kosdaq_volume_rank": {"row_count": 30},
        },
        "requirement_matrix": [],
        "model_lift_assessment": {
            "verdict": "possible",
            "high_value_candidate_features": ["value_traded"],
            "why_not_proven_yet": ["no archive"],
            "recommended_validation_sequence": ["persist side-by-side"],
        },
    }

    md = render_markdown(report)

    assert "## 결론" in md
    assert "## 모델 개선 가능성" in md
