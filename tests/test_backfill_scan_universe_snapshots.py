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
