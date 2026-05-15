import json

from modules.scan_artifact_archive import load_local_scan_archive_rows
from modules.scan_integrity import build_observed_factor_snapshots
from modules.scan_persistence import persist_scan_run_artifacts


class FakeMemory:
    def __init__(self, root):
        self.root = root

    def artifact_store(self, run_id):
        path = self.root / str(run_id)
        path.mkdir(parents=True, exist_ok=True)
        return path


def test_persist_scan_run_artifacts_writes_archive_contract(tmp_path):
    top_deep_path = tmp_path / "top_deep" / "RUN-WEB.json"
    top_deep_path.parent.mkdir(parents=True, exist_ok=True)
    top_deep_path.write_text("[]", encoding="utf-8")

    result = persist_scan_run_artifacts(
        run_id="RUN-WEB",
        market="KOSPI",
        scan_mode="SWING",
        results=[
            {
                "ticker": "005490.KS",
                "종목명": "POSCO홀딩스",
                "Decision Score": 92.5,
                "매수가(-2%)": "560,000",
                "alpha_score": 88,
                "tech_score": 77,
                "ml_prob": 61,
                "whale_score": 72,
                "volume_ratio": 2.3,
                "day_return_pct": 1.7,
                "initial_trend": "UP",
            }
        ],
        total_scans=835,
        diagnostics={"filtered_count": 834, "worker_error_count": 0, "executor_exception_count": 0},
        bridge_info={"planner_handoff": "runtime_state/shared_working/RUN-WEB/planner_handoff.json"},
        top_deep_reports={"count": 1, "local_path": str(top_deep_path)},
        memory=FakeMemory(tmp_path / "artifacts"),
    )

    assert result["ok"] is True
    summary = json.loads((tmp_path / "artifacts" / "RUN-WEB" / "scan_pipeline_summary.json").read_text(encoding="utf-8"))
    raw = json.loads((tmp_path / "artifacts" / "RUN-WEB" / "raw_scan_results.json").read_text(encoding="utf-8"))

    assert summary["run_id"] == "RUN-WEB"
    assert summary["result_count"] == 1
    assert summary["total_scans"] == 835
    assert summary["manifest_paths"]["planner_handoff"].endswith("planner_handoff.json")
    assert summary["persistence_contract"]["observed_factor_snapshots"] is True
    assert summary["persistence_contract"]["scan_integrity_report"] is True
    assert summary["scan_integrity"]["report"]["snapshot_count"] == 1
    assert "FACTOR_COMPLETENESS_BELOW_95" in summary["scan_integrity"]["report"]["quality_flags"]
    assert raw["results_sorted"][0]["ticker"] == "005490.KS"

    observed = json.loads((tmp_path / "artifacts" / "RUN-WEB" / "observed_factor_snapshots.json").read_text(encoding="utf-8"))
    integrity = json.loads((tmp_path / "artifacts" / "RUN-WEB" / "scan_integrity_report.json").read_text(encoding="utf-8"))
    assert observed["snapshots"][0]["factors"]["decision_score"] == 92.5
    assert integrity["run_id"] == "RUN-WEB"
    assert integrity["raw_result_count"] == 1

    archive_rows = load_local_scan_archive_rows(artifact_dir=tmp_path / "artifacts")
    assert len(archive_rows) == 1
    assert archive_rows[0]["run_id"] == "RUN-WEB"
    assert archive_rows[0]["market"] == "KOSPI"


def test_observed_factor_snapshots_include_planner_only_exception_leader(tmp_path):
    planner_path = tmp_path / "planner_handoff.json"
    planner_path.write_text(
        json.dumps(
            {
                "decisions": [
                    {
                        "ticker": "005930.KS",
                        "stock_name": "삼성전자",
                        "priority_rank": 1,
                        "decision": "PRIORITY_WATCHLIST",
                        "decision_score": 91.2,
                    }
                ],
                "watchlist_meta": [
                    {
                        "ticker": "000660.KS",
                        "stock_name": "SK하이닉스",
                        "priority_rank": 1,
                        "decision": "EXCEPTION_LEADER",
                        "decision_bucket": "exception_leader",
                        "expected_edge_score": 7.5,
                        "whale_score": 74,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    snapshots = build_observed_factor_snapshots(
        run_id="RUN-EL",
        market="KOSPI",
        scan_mode="SWING",
        created_at="2026-05-16T00:00:00+00:00",
        results=[
            {
                "ticker": "005930.KS",
                "name": "삼성전자",
                "Decision Score": 91.2,
            }
        ],
        bridge_info={"planner_handoff": str(planner_path)},
    )

    by_ticker = {row["ticker"]: row for row in snapshots}
    assert sorted(by_ticker) == ["000660.KS", "005930.KS"]
    assert by_ticker["005930.KS"]["raw_scan_present"] is True
    assert by_ticker["000660.KS"]["raw_scan_present"] is False
    assert by_ticker["000660.KS"]["planner_present"] is True
    assert by_ticker["000660.KS"]["decision_bucket"] == "exception_leader"
    assert by_ticker["000660.KS"]["factors"]["expected_edge_score"] == 7.5
