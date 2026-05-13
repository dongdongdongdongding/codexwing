import json

from modules.scan_artifact_archive import load_local_scan_archive_rows
from modules.scan_persistence import persist_scan_run_artifacts


class FakeMemory:
    def __init__(self, root):
        self.root = root

    def artifact_store(self, run_id):
        path = self.root / str(run_id)
        path.mkdir(parents=True, exist_ok=True)
        return path


def test_persist_scan_run_artifacts_writes_archive_contract(tmp_path):
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
            }
        ],
        total_scans=835,
        diagnostics={"filtered_count": 834, "worker_error_count": 0, "executor_exception_count": 0},
        bridge_info={"planner_handoff": "runtime_state/shared_working/RUN-WEB/planner_handoff.json"},
        top_deep_reports={"count": 1, "local_path": str(tmp_path / "top_deep" / "RUN-WEB.json")},
        memory=FakeMemory(tmp_path / "artifacts"),
    )

    assert result["ok"] is True
    summary = json.loads((tmp_path / "artifacts" / "RUN-WEB" / "scan_pipeline_summary.json").read_text(encoding="utf-8"))
    raw = json.loads((tmp_path / "artifacts" / "RUN-WEB" / "raw_scan_results.json").read_text(encoding="utf-8"))

    assert summary["run_id"] == "RUN-WEB"
    assert summary["result_count"] == 1
    assert summary["total_scans"] == 835
    assert summary["manifest_paths"]["planner_handoff"].endswith("planner_handoff.json")
    assert raw["results_sorted"][0]["ticker"] == "005490.KS"

    archive_rows = load_local_scan_archive_rows(artifact_dir=tmp_path / "artifacts")
    assert len(archive_rows) == 1
    assert archive_rows[0]["run_id"] == "RUN-WEB"
    assert archive_rows[0]["market"] == "KOSPI"
