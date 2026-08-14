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


def _fake_ok_command(cmd, cwd):
    return {
        "cmd": cmd,
        "returncode": 0,
        "stdout_tail": "",
        "stderr_tail": "",
        "started_at": "2026-08-14T00:00:00+00:00",
        "finished_at": "2026-08-14T00:00:01+00:00",
        "ok": True,
    }


def _write_resolved(shared_dir: Path, run_id: str, count: int) -> None:
    _write_json(
        shared_dir / run_id / "realized_outcomes.json",
        {
            "run_context": {"market": "KOSPI"},
            "outcomes": [
                {"status": "RESOLVED", "ticker": f"{i:06d}", "priority_rank": i, "decision_bucket": "shadow"}
                for i in range(1, count + 1)
            ],
        },
    )


def _cycle(mode: str, shared_dir: Path, report_dir: Path, state_path: Path, **kw):
    params = dict(
        mode=mode,
        shared_dir=shared_dir,
        report_dir=report_dir,
        state_path=state_path,
        nightly_min_new_resolved=1,
        weekly_min_total_resolved=50,
        weekly_min_new_resolved=10,
    )
    params.update(kw)
    return runner.run_learning_cycle(**params)


def test_nightly_rebaselines_when_resolved_counter_shrinks(monkeypatch, tmp_path):
    """표본 원천 축소(2026-06-14 8180 → ~4100)가 영구 skip이 되지 않아야 한다.

    기존 `max(0, total - previous)`는 카운터 역행을 '새 작업 없음'으로 덮어
    nightly/weekly가 9주간 전부 skip했고, 학습 데이터셋 export와 walk-forward
    릴리스 게이트 리포트가 그동안 한 번도 갱신되지 않았다 (swing-main-7x7h 자매 건).
    """
    monkeypatch.setattr(runner, "_run_command", _fake_ok_command)
    shared_dir, report_dir = tmp_path / "shared", tmp_path / "reports"
    state_path = tmp_path / "state.json"
    _write_json(state_path, {"last_nightly_resolved_total": 8180, "last_weekly_resolved_total": 8180})
    _write_resolved(shared_dir, "RUN-20260814-001", 2)

    report = _cycle("nightly", shared_dir, report_dir, state_path)

    assert report["counter_rebaselined_from"] == 8180
    assert report["total_resolved"] == 2
    assert report["action"] == "skip"          # 재기준선 주기 자체는 아직 새 표본 0
    assert json.loads(state_path.read_text(encoding="utf-8"))["last_nightly_resolved_total"] == 2


def test_nightly_resumes_on_the_cycle_after_rebaseline(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "_run_command", _fake_ok_command)
    shared_dir, report_dir = tmp_path / "shared", tmp_path / "reports"
    state_path = tmp_path / "state.json"
    _write_json(state_path, {"last_nightly_resolved_total": 8180})
    _write_resolved(shared_dir, "RUN-20260814-001", 2)
    _cycle("nightly", shared_dir, report_dir, state_path)

    _write_resolved(shared_dir, "RUN-20260815-001", 3)   # 새 표본 3건
    report = _cycle("nightly", shared_dir, report_dir, state_path)

    assert report["counter_rebaselined_from"] is None
    assert report["new_resolved_since_last_cycle"] == 3
    assert report["action"] == "dataset_refresh"


def test_weekly_rebaselines_and_then_runs_dataset_export(monkeypatch, tmp_path):
    """재학습(AG_PHASE25_RETRAIN)은 2026-07-19 운영자 결정으로 꺼져 있고, 막힌 것은 데이터셋 export다."""
    monkeypatch.setattr(runner, "_run_command", _fake_ok_command)
    monkeypatch.delenv("AG_PHASE25_RETRAIN", raising=False)
    shared_dir, report_dir = tmp_path / "shared", tmp_path / "reports"
    state_path = tmp_path / "state.json"
    _write_json(state_path, {"last_weekly_resolved_total": 8180})
    _write_resolved(shared_dir, "RUN-20260814-001", 60)

    first = _cycle("weekly", shared_dir, report_dir, state_path)
    assert first["counter_rebaselined_from"] == 8180 and first["action"] == "skip"

    _write_resolved(shared_dir, "RUN-20260821-001", 15)
    second = _cycle("weekly", shared_dir, report_dir, state_path)

    assert second["counter_rebaselined_from"] is None
    assert second["new_resolved_since_last_cycle"] == 15
    assert second["action"] == "weekly_dataset_only"     # 모델 재학습은 여전히 꺼져 있다
