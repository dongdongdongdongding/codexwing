import json

from modules.scan_artifact_archive import (
    load_local_scan_archive_rows,
    merge_archive_rows_with_local_artifacts,
)


def test_load_local_scan_archive_rows_normalizes_non_db_artifacts(tmp_path):
    run_dir = tmp_path / "RUN-LOCAL"
    run_dir.mkdir(parents=True)
    (run_dir / "scan_pipeline_summary.json").write_text(
        json.dumps({"run_id": "RUN-LOCAL", "market": "KOSDAQ", "scan_mode": "SWING"}),
        encoding="utf-8",
    )
    (run_dir / "raw_scan_results.json").write_text(
        json.dumps(
            {
                "results_sorted": [
                    {
                        "Ticker": "035900.KQ",
                        "Stock Name": "JYP Ent.",
                        "Decision Score": "91.5",
                        "Strategy": "WATCHLIST",
                        "매수가(-2%)": "77,000",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    rows = load_local_scan_archive_rows(artifact_dir=tmp_path)

    assert len(rows) == 1
    assert rows[0]["run_id"] == "RUN-LOCAL"
    assert rows[0]["ticker"] == "035900.KQ"
    assert rows[0]["stock_name"] == "JYP Ent."
    assert rows[0]["market_type"] == "KR"
    assert rows[0]["decision_score"] == 91.5
    assert rows[0]["entry_reference_price"] == 77000.0
    assert rows[0]["source_ref"] == "local_artifact:RUN-LOCAL:035900.KQ"


def test_merge_archive_rows_with_local_artifacts_adds_only_missing_pairs():
    db_rows = [{"run_id": "RUN-A", "ticker": "005930.KS", "source": "db"}]
    local_rows = [
        {"run_id": "RUN-A", "ticker": "005930.KS", "source": "local_duplicate"},
        {"run_id": "RUN-A", "ticker": "000660.KS", "source": "local_missing"},
    ]

    merged = merge_archive_rows_with_local_artifacts(db_rows, local_rows)

    assert len(merged) == 2
    assert merged[0]["source"] == "db"
    assert merged[1]["ticker"] == "000660.KS"
