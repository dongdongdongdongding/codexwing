import csv
import json
from pathlib import Path

from multi_agent.tools.backfill_scan_universe_snapshots import build_snapshot_rows


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_build_snapshot_rows_includes_emitted_and_rejected_symbols(tmp_path):
    artifact_dir = tmp_path / "artifacts"
    shared_dir = tmp_path / "shared_working"
    reject_csv = tmp_path / "reject_outcomes.csv"
    run_dir = artifact_dir / "RUN-TEST"

    _write_json(
        run_dir / "scan_pipeline_summary.json",
        {
            "run_id": "RUN-TEST",
            "market": "KOSPI",
            "scan_mode": "SWING",
            "created_at": "2026-05-20T09:35:00+09:00",
        },
    )
    _write_json(
        run_dir / "raw_scan_results.json",
        {
            "results_sorted": [
                {
                    "ticker": "000001.KS",
                    "stock_name": "통과",
                    "priority_rank": 1,
                    "decision": "PRIORITY_WATCHLIST",
                    "decision_bucket": "picked",
                    "alpha_score": 91,
                    "decision_score": 88,
                    "foreigner_1d": 100,
                    "institution_1d": 50,
                    "retail_1d": -150,
                    "foreigner_3d": 250,
                    "institution_3d": 100,
                    "retail_3d": -350,
                    "entry_reference_price": 10000,
                }
            ],
            "scan_result": {
                "total_scans": 3,
                "diagnostics": {
                    "filtered_count": 2,
                    "reject_reasons_by_symbol": {
                        "000002.KS": "LIQUIDITY_FILTER_FAIL",
                        "000003.KS": "KR_SIGNAL_WINDOW_FAIL",
                    },
                    "reject_details_by_symbol": {
                        "000002.KS": [
                            {
                                "stage": "liquidity_gate",
                                "curr_price": 5000,
                                "turnover": 100000000,
                                "volume_ratio": 0.4,
                            }
                        ],
                        "000003.KS": [
                            {
                                "stage": "signal_window",
                                "curr_price": 7000,
                                "alpha_score": 72,
                            }
                        ],
                    },
                },
            },
        },
    )
    _write_json(
        shared_dir / "RUN-TEST" / "realized_outcomes.json",
        {
            "run_id": "RUN-TEST",
            "outcomes": [
                {
                    "ticker": "000001.KS",
                    "return_1d_pct": 1.5,
                    "return_3d_pct": 3.0,
                    "return_5d_pct": 4.0,
                    "entry_reference_price": 10000,
                }
            ],
        },
    )
    with reject_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "run_id",
                "ticker",
                "market",
                "base_trade_date",
                "entry_reference_price",
                "outcome_available",
                "return_1d_pct",
                "return_3d_pct",
                "return_5d_pct",
                "backfill_version",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "run_id": "RUN-TEST",
                "ticker": "000002.KS",
                "market": "KOSPI",
                "base_trade_date": "2026-05-20",
                "entry_reference_price": "5000",
                "outcome_available": "true",
                "return_1d_pct": "-1",
                "return_3d_pct": "2",
                "return_5d_pct": "5",
                "backfill_version": "fixture",
            }
        )

    rows, summary = build_snapshot_rows(
        artifact_dir=artifact_dir,
        shared_dir=shared_dir,
        reject_outcome_csv=reject_csv,
        limit_runs=0,
        market_filter="ALL",
        scan_mode_filter="ALL",
    )

    assert summary["rows_built"] == 3
    assert summary["emitted_rows"] == 1
    assert summary["rejected_rows"] == 2
    assert summary["outcome_available_rows"] == 2

    by_ticker = {row["ticker"]: row for row in rows}
    assert by_ticker["000001.KS"]["passed_current_model"] is True
    assert by_ticker["000001.KS"]["return_5d_pct"] == 4.0
    assert by_ticker["000001.KS"]["has_actual_flow"] is True
    assert by_ticker["000001.KS"]["flow_asof"] == "2026-05-20"
    assert by_ticker["000001.KS"]["flow_consensus_buying"] is True
    assert by_ticker["000001.KS"]["whale_trend"] == "accumulation"
    assert by_ticker["000002.KS"]["passed_current_model"] is False
    assert by_ticker["000002.KS"]["reject_reason"] == "LIQUIDITY_FILTER_FAIL"
    assert by_ticker["000002.KS"]["return_5d_pct"] == 5.0
    assert by_ticker["000003.KS"]["reject_stage"] == "signal_window"
    assert by_ticker["000003.KS"]["has_actual_flow"] is False
    assert "investor_flow_missing_in_scan_archive" in by_ticker["000003.KS"]["flow_warnings"]


def test_build_snapshot_rows_parses_runtime_display_and_nested_features(tmp_path):
    artifact_dir = tmp_path / "artifacts"
    shared_dir = tmp_path / "shared_working"
    reject_csv = tmp_path / "reject_outcomes.csv"
    run_dir = artifact_dir / "RUN-DISPLAY"

    _write_json(
        run_dir / "scan_pipeline_summary.json",
        {
            "run_id": "RUN-DISPLAY",
            "market": "KOSPI",
            "scan_mode": "SWING",
            "created_at": "2026-05-21T09:35:00+09:00",
        },
    )
    _write_json(
        run_dir / "raw_scan_results.json",
        {
            "results_sorted": [
                {
                    "ticker": "000004.KS",
                    "종목명": "표시행",
                    "Antigrav": 84,
                    "AI확률": "53.5%",
                    "정밀확률": "49.2%",
                    "수급": "67점 축적",
                    "거래량": "✅ 2.35",
                    "전일비": "+3.8%",
                    "매수가(-2%)": "12,300",
                    "Decision Score": 81.4,
                    "leader_metrics": {
                        "kr_foreign_flow": -120.5,
                        "kr_institution_flow": 310.25,
                        "kr_retail_flow": -189.75,
                        "kr_volume_ratio": 2.35,
                        "kr_turnover": 9876543210,
                        "kr_flow_consensus_buying": True,
                    },
                    "flow": {
                        "foreigner_3d": 40.0,
                        "institution_3d": 80.0,
                        "retail_3d": -120.0,
                        "foreigner_10d": 100.0,
                        "institution_10d": 150.0,
                        "retail_10d": -250.0,
                    },
                    "theme_context": {
                        "primary_theme": "전력기기",
                        "theme_source": "dynamic",
                        "theme_inference_status": "resolved",
                    },
                }
            ],
            "scan_result": {"total_scans": 1, "diagnostics": {"filtered_count": 0}},
        },
    )

    rows, summary = build_snapshot_rows(
        artifact_dir=artifact_dir,
        shared_dir=shared_dir,
        reject_outcome_csv=reject_csv,
        limit_runs=0,
        market_filter="ALL",
        scan_mode_filter="ALL",
    )

    assert summary["rows_built"] == 1
    row = rows[0]
    assert row["alpha_score"] == 84.0
    assert row["tech_score"] == 84.0
    assert row["ml_prob"] == 53.5
    assert row["prob_clean"] == 49.2
    assert row["whale_score"] == 67.0
    assert row["volume_ratio"] == 2.35
    assert row["turnover"] == 9876543210.0
    assert row["day_return_pct"] == 3.8
    assert row["entry_reference_price"] == 12300.0
    assert row["foreigner_1d"] == -120.5
    assert row["institution_1d"] == 310.25
    assert row["retail_1d"] == -189.75
    assert row["whale_flow_1d"] == 189.75
    assert row["whale_flow_3d"] == 120.0
    assert row["whale_flow_10d"] == 250.0
    assert row["primary_theme"] == "전력기기"
    assert row["feature_coverage_score"] > 0.9


def test_build_snapshot_rows_preserves_kis_prefilter_feature_snapshot(tmp_path):
    artifact_dir = tmp_path / "artifacts"
    shared_dir = tmp_path / "shared_working"
    reject_csv = tmp_path / "reject_outcomes.csv"
    run_dir = artifact_dir / "RUN-KIS-PREFILTER"

    _write_json(
        run_dir / "scan_pipeline_summary.json",
        {
            "run_id": "RUN-KIS-PREFILTER",
            "market": "KOSPI",
            "scan_mode": "SWING",
            "created_at": "2026-06-05T09:35:00+09:00",
            "kis_operational_prefilter": {
                "contract_version": "kis_operational_prefilter_v1",
                "selected": [
                    {
                        "ticker": "000001.KS",
                        "feature_origin": "kis_openapi_prefilter",
                        "is_dummy_data": False,
                        "sources": ["volume_rank", "vi_status"],
                        "rank": {"volume_rank": 1},
                        "selection_score": 123.4,
                        "score_components": {"value_traded": 20.0, "vi_triggered": 8.0},
                        "vi_triggered": True,
                        "quote": {"value_traded": 100000000000, "prev_volume_ratio": 180.0},
                    }
                ],
            },
        },
    )
    _write_json(
        run_dir / "raw_scan_results.json",
        {
            "results_sorted": [
                {
                    "ticker": "000001.KS",
                    "stock_name": "KIS통과",
                    "priority_rank": 1,
                    "decision": "PRIORITY_WATCHLIST",
                    "decision_score": 88,
                }
            ],
            "scan_result": {"total_scans": 1, "diagnostics": {"filtered_count": 0}},
        },
    )

    rows, summary = build_snapshot_rows(
        artifact_dir=artifact_dir,
        shared_dir=shared_dir,
        reject_outcome_csv=reject_csv,
        limit_runs=0,
        market_filter="ALL",
        scan_mode_filter="ALL",
    )

    assert summary["rows_built"] == 1
    assert summary["kis_prefilter_feature_rows"] == 1
    feature = rows[0]["feature_snapshot"]["kis_operational_prefilter"]
    assert feature["selection_score"] == 123.4
    assert feature["quote"]["value_traded"] == 100000000000
    assert feature["snapshot_feature_version"] == "kis_operational_prefilter_snapshot_v1"
    assert rows[0]["feature_origin"] == "raw_scan_results+kis_openapi_prefilter"
