import json
from pathlib import Path

from multi_agent.tools import run_learning_cycle as runner


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_nightly_cycle_can_enqueue_kis_touch5_full_matrix(monkeypatch, tmp_path):
    shared_dir = tmp_path / "shared"
    report_dir = tmp_path / "reports"
    state_path = tmp_path / "state.json"
    _write_json(
        shared_dir / "RUN-20260613-001" / "realized_outcomes.json",
        {
            "run_context": {"market": "KOSPI"},
            "outcomes": [
                {
                    "status": "RESOLVED",
                    "ticker": "000001",
                    "priority_rank": 1,
                    "decision_bucket": "shadow",
                }
            ],
        },
    )
    calls = []

    def fake_run_command(cmd, cwd):
        calls.append(cmd)
        return {
            "cmd": cmd,
            "returncode": 0,
            "stdout_tail": "",
            "stderr_tail": "",
            "started_at": "2026-06-13T00:00:00+00:00",
            "finished_at": "2026-06-13T00:00:01+00:00",
            "ok": True,
        }

    monkeypatch.setattr(runner, "_run_command", fake_run_command)

    report = runner.run_learning_cycle(
        mode="nightly",
        shared_dir=shared_dir,
        report_dir=report_dir,
        state_path=state_path,
        nightly_min_new_resolved=1,
        weekly_min_total_resolved=50,
        weekly_min_new_resolved=10,
        run_kis_touch5_full_matrix=True,
    )

    assert report["action"] == "dataset_refresh"
    assert report["kis_touch5_full_matrix_requested"] is True
    assert [
        "python3",
        "multi_agent/tools/report_kis_touch5_slice_ablation.py",
        "--full-matrix",
    ] in calls
