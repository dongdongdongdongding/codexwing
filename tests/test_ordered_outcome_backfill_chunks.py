from pathlib import Path

from multi_agent.tools import run_ordered_outcome_backfill_chunks as chunks


def test_chunk_run_ids_respects_chunk_size():
    assert chunks.chunk_run_ids(["RUN-1", "RUN-2", "RUN-3"], 2) == [["RUN-1", "RUN-2"], ["RUN-3"]]


def test_aggregate_reports_sums_counts_and_failures():
    report = chunks.aggregate_reports(
        [
            {
                "rows_seen": 3,
                "rows_updated": 1,
                "db_rows_upserted": 3,
                "intraday_fetch_failures": {"empty_response": 2},
            },
            {
                "rows_seen": 4,
                "rows_updated": 2,
                "db_rows_upserted": 4,
                "intraday_fetch_failures": {"other_exc": 1},
            },
        ]
    )

    assert report["rows_seen"] == 7
    assert report["rows_updated"] == 3
    assert report["db_rows_upserted"] == 7
    assert report["intraday_fetch_failures"]["empty_response"] == 2
    assert report["intraday_fetch_failures"]["other_exc"] == 1


def test_run_chunks_resumes_completed_runs(tmp_path, monkeypatch):
    shared = tmp_path / "shared"
    for run_id in ["RUN-A", "RUN-B", "RUN-C"]:
        (shared / run_id).mkdir(parents=True)
    output = tmp_path / "state.json"
    chunks._write_json(output, {"completed_run_ids": ["RUN-A"], "chunk_reports": [], "failures": []})
    called = []

    def fake_run_update(*, run_ids, **_kwargs):
        called.append(list(run_ids))
        return {
            "runs_seen": len(run_ids),
            "rows_seen": len(run_ids) * 10,
            "rows_updated": len(run_ids),
            "intraday_fetch_failures": {},
        }

    monkeypatch.setattr(chunks, "run_update", fake_run_update)

    report = chunks.run_chunks(
        shared_dir=shared,
        run_ids=[],
        limit_runs=0,
        chunk_size=1,
        max_chunks=1,
        retries=0,
        sleep_seconds=0,
        dry_run=False,
        scan_mode_filter="SWING",
        output=output,
        resume=True,
    )

    assert called == [["RUN-B"]]
    assert "RUN-A" in report["completed_run_ids"]
    assert "RUN-B" in report["completed_run_ids"]
    assert Path(output).exists()
