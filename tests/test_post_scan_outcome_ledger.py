import json

from modules.post_scan_outcome_ledger import build_post_scan_ledger_rows, summarize_post_scan_ledger, write_run_post_scan_ledger


def test_build_post_scan_ledger_preserves_section_and_path_metrics():
    rows = build_post_scan_ledger_rows(
        [
            {
                "ticker": "005930.KS",
                "stock_name": "삼성전자",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "priority_rank": 1,
                "decision": "PRIORITY_WATCHLIST",
                "decision_bucket": "picked",
                "recommended_at": "2026-05-19T09:30:00+09:00",
                "scan_entry_reference_price": 100.0,
                "entry_reference_price": 101.0,
                "return_10m_pct": -0.5,
                "return_30m_pct": 1.2,
                "return_1h_pct": 2.3,
                "return_close_pct": 3.4,
                "return_1d_pct": 4.5,
                "return_3d_pct": 6.7,
                "return_5d_pct": 8.9,
                "mfe_5d_pct": 10.0,
                "mae_5d_pct": -1.5,
                "target_before_stop_5d": True,
                "stop_before_target_5d": False,
            }
        ],
        run_id="RUN-TEST",
        top_deep_section_map={
            "005930.KS": {
                "section": "Top5",
                "section_rank": 1,
                "scan_entry_reference_price": 99.0,
            }
        },
    )

    assert rows[0]["ledger_key"] == "RUN-TEST:005930.KS:1:post_scan_outcome_ledger_v1"
    assert rows[0]["section"] == "Top5"
    assert rows[0]["scan_entry_reference_price"] == 100.0
    assert rows[0]["return_10m_pct"] == -0.5
    assert rows[0]["mfe_5d_pct"] == 10.0
    assert rows[0]["mae_5d_pct"] == -1.5
    assert rows[0]["ledger_status"] == "MATURED_5D"


def test_summarize_post_scan_ledger_reports_win_avg_min_max_and_stop_first():
    summary = summarize_post_scan_ledger(
        [
            {
                "market": "KOSPI",
                "scan_mode": "SWING",
                "section": "Top5",
                "return_5d_pct": 5.0,
                "mfe_5d_pct": 8.0,
                "mae_5d_pct": -2.0,
                "stop_before_target_5d": False,
                "ledger_status": "MATURED_5D",
            },
            {
                "market": "KOSPI",
                "scan_mode": "SWING",
                "section": "Top5",
                "return_5d_pct": -3.0,
                "mfe_5d_pct": 1.0,
                "mae_5d_pct": -6.0,
                "stop_before_target_5d": True,
                "ledger_status": "MATURED_5D",
            },
        ]
    )

    group = summary["groups"][0]
    assert summary["rows"] == 2
    assert summary["matured_5d_rows"] == 2
    assert group["5d_n"] == 2
    assert group["5d_win_pct"] == 50.0
    assert group["5d_avg_pct"] == 1.0
    assert group["5d_min_pct"] == -3.0
    assert group["5d_max_pct"] == 5.0
    assert group["avg_mfe_5d_pct"] == 4.5
    assert group["avg_mae_5d_pct"] == -4.0
    assert group["stop_first_5d_pct"] == 50.0


def test_write_run_post_scan_ledger_is_candidate_only_and_no_raw_bars(tmp_path):
    run_dir = tmp_path / "RUN-TEST"
    run_dir.mkdir()
    report_dir = tmp_path / "top_deep"
    report_dir.mkdir()
    (report_dir / "RUN-TEST.json").write_text(
        json.dumps(
            [
                {
                    "ticker": "005930.KS",
                    "selection_alignment": {"analysis_section": "Exception Leader", "analysis_section_rank": 1},
                    "trade_plan": {"entry_reference_price": 100.0},
                }
            ]
        ),
        encoding="utf-8",
    )

    payload = write_run_post_scan_ledger(
        run_dir=run_dir,
        outcomes=[{"ticker": "005930.KS", "market": "KOSPI", "scan_mode": "SWING"}],
        report_dir=report_dir,
    )
    saved = json.loads((run_dir / "post_scan_outcome_ledger.json").read_text(encoding="utf-8"))

    assert payload["summary"]["rows"] == 1
    assert saved["storage_policy"]["raw_intraday_bars_persisted"] is False
    assert saved["storage_policy"]["scope"] == "emitted_candidates_only"
    assert saved["rows"][0]["section"] == "Exception Leader"
    assert "raw_bars" not in saved["rows"][0]
