import json
import shutil
from pathlib import Path

import pytest

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


def _roll_window(shared_dir: Path, night: int, window: int, per_run: int) -> None:
    """매 밤 새 RUN을 넣고 창 밖으로 나간 RUN을 지운다 — total_resolved가 평평해진다."""
    _write_resolved(shared_dir, f"RUN-2026081{night:01d}-001", per_run)
    stale = shared_dir / f"RUN-2026081{night - window:01d}-001"
    if stale.exists():
        shutil.rmtree(stale)


def test_nightly_rolling_window_with_flat_counter_is_not_a_permanent_skip(monkeypatch, tmp_path):
    """F-1 회귀: 카운터가 '감소'가 아니라 '정체'해도 새 표본을 세어야 한다.

    `_collect_outcomes`는 매번 shared_dir 전체를 재스캔한다. 즉 total_resolved는
    누적 카운터가 아니라 **현재 창의 개수**다. 정리가 주기적이면(매일 N건 추가 / N건 제거)
    total은 줄지 않고 평평해지고, `max(0, total - previous)` 델타 게이트는 영구히 0을 낸다.
    그러면 사이클이 영원히 skip인데 counter_rebaselined_from은 null이라
    리포트에 아무 이상도 안 뜬다 — ede9706이 고쳤다고 선언한 "9주간 조용한 skip"과
    증상·가시성이 완전히 동일하다.

    수정 전 실측 (창=3런 × 3건):
        night4~6: total=9 new=0 rebase_from=None action=skip  <- 영구
    """
    monkeypatch.setattr(runner, "_run_command", _fake_ok_command)
    shared_dir, report_dir = tmp_path / "shared", tmp_path / "reports"
    state_path = tmp_path / "state.json"

    reports = []
    for night in range(1, 7):
        _roll_window(shared_dir, night, window=3, per_run=3)
        reports.append(_cycle("nightly", shared_dir, report_dir, state_path))

    # 창이 가득 찬 뒤(4번째 밤부터) total은 9로 평평하지만 매 밤 3건이 새로 들어온다.
    assert [r["total_resolved"] for r in reports[3:]] == [9, 9, 9]
    assert [r["new_resolved_since_last_cycle"] for r in reports[3:]] == [3, 3, 3]
    assert [r["action"] for r in reports[3:]] == ["dataset_refresh"] * 3

    # 창 밖으로 빠져나간 표본도 리포트에 드러나야 한다 (조용한 정리 금지).
    assert reports[-1]["dropped_resolved_since_last_cycle"] == 3
    assert reports[-1]["new_resolved_measurement_basis"] == "outcome_key_set"


def test_nightly_skip_streak_is_reported_instead_of_being_silent(monkeypatch, tmp_path):
    """F-1 회귀(신호): 진짜로 새 표본이 없을 때도 침묵하지 말아야 한다.

    9주간 아무도 몰랐던 이유는 skip이 '정상 상태'와 구분되지 않았기 때문이다.
    연속 skip 횟수를 리포트와 상태파일에 남겨 누적 침묵이 보이게 한다.
    """
    monkeypatch.setattr(runner, "_run_command", _fake_ok_command)
    shared_dir, report_dir = tmp_path / "shared", tmp_path / "reports"
    state_path = tmp_path / "state.json"
    _write_resolved(shared_dir, "RUN-20260814-001", 5)

    first = _cycle("nightly", shared_dir, report_dir, state_path)
    assert first["action"] == "dataset_refresh"
    assert first["consecutive_skip_cycles"] == 0

    streak = [_cycle("nightly", shared_dir, report_dir, state_path) for _ in range(3)]

    assert [r["action"] for r in streak] == ["skip"] * 3
    assert [r["consecutive_skip_cycles"] for r in streak] == [1, 2, 3]
    assert json.loads(state_path.read_text(encoding="utf-8"))["consecutive_nightly_skip_cycles"] == 3
    assert "consecutive_skip_cycles: 3" in (report_dir / "learning_cycle_nightly.md").read_text(encoding="utf-8")


def test_weekly_baseline_advances_even_when_retraining_is_disabled(monkeypatch, tmp_path):
    """F-3 회귀: weekly 기준선이 재학습이 꺼진 지금도 전진해야 한다.

    `last_weekly_resolved_total`은 `action == "weekly_retrain"`이고 재학습이 성공했을 때만
    갱신됐다. 그런데 2026-07-19 운영자 결정으로 AG_PHASE25_RETRAIN=0이 기본이라
    action은 항상 `weekly_dataset_only`다 → 기준선이 **영원히 고착**되고
    `new_resolved_since_last_cycle`은 "직전 주기 이후"가 아니라 "마지막 성공 재학습 이후"라
    무한 증가하는 거짓 라벨이 된다. 게이트 `weekly_min_new_resolved`도 첫 통과 후 영구 무력화된다.

    수정 전 실측:
        wk2: total=75 new=15  wk3: total=76 new=16  wk4: total=77 new=17  (기준선 60 고착)
    """
    monkeypatch.setattr(runner, "_run_command", _fake_ok_command)
    monkeypatch.delenv("AG_PHASE25_RETRAIN", raising=False)
    shared_dir, report_dir = tmp_path / "shared", tmp_path / "reports"
    state_path = tmp_path / "state.json"
    _write_resolved(shared_dir, "RUN-20260807-001", 60)

    wk1 = _cycle("weekly", shared_dir, report_dir, state_path)
    assert wk1["action"] == "weekly_dataset_only"   # total 60 >= 50, new 60 >= 10

    _write_resolved(shared_dir, "RUN-20260814-001", 15)
    wk2 = _cycle("weekly", shared_dir, report_dir, state_path)
    assert wk2["action"] == "weekly_dataset_only"
    assert wk2["new_resolved_since_last_cycle"] == 15

    # 여기가 핵심 — 재학습이 꺼져 있어도 기준선은 wk2에서 전진했어야 한다.
    _write_resolved(shared_dir, "RUN-20260821-001", 1)
    wk3 = _cycle("weekly", shared_dir, report_dir, state_path)
    assert wk3["total_resolved"] == 76
    assert wk3["new_resolved_since_last_cycle"] == 1     # 버그 시절엔 16
    assert wk3["action"] == "skip"                        # min=10 게이트가 다시 살아있다

    _write_resolved(shared_dir, "RUN-20260828-001", 1)
    wk4 = _cycle("weekly", shared_dir, report_dir, state_path)
    assert wk4["new_resolved_since_last_cycle"] == 2      # 버그 시절엔 17
    assert wk4["action"] == "skip"


def test_weekly_dataset_only_does_not_claim_a_model_was_trained(monkeypatch, tmp_path):
    """F-3의 반쪽: 기준선은 전진해도 '마지막 재학습 시각'은 전진하면 안 된다.

    두 사실(표본을 어디까지 소화했나 / 모델을 언제 학습했나)을 한 필드에 묶어둔 것이
    F-3의 원인이었다. 분리한 뒤에도 재학습 시각이 오염되지 않는지 못박는다.
    """
    monkeypatch.setattr(runner, "_run_command", _fake_ok_command)
    monkeypatch.delenv("AG_PHASE25_RETRAIN", raising=False)
    shared_dir, report_dir = tmp_path / "shared", tmp_path / "reports"
    state_path = tmp_path / "state.json"
    _write_resolved(shared_dir, "RUN-20260807-001", 60)
    _cycle("weekly", shared_dir, report_dir, state_path)
    _write_resolved(shared_dir, "RUN-20260814-001", 15)
    report = _cycle("weekly", shared_dir, report_dir, state_path)

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert report["action"] == "weekly_dataset_only"
    assert state["last_weekly_resolved_total"] == 75      # 표본 기준선은 전진
    assert state.get("last_weekly_train_at") is None      # 재학습 시각은 그대로


def _live_shaped_state(key_count: int = 200) -> dict:
    """라이브와 같은 모양(키집합 2개를 든 큰 상태파일)."""
    keys = [f"RUN-2026081{i % 9}-001:{i:06d}:{i % 5}" for i in range(key_count)]
    return {
        "last_nightly_resolved_total": key_count,
        "last_nightly_resolved_keys": sorted(keys),
        "last_weekly_resolved_total": key_count,
        "last_weekly_resolved_keys": sorted(keys),
        "last_weekly_train_at": "2026-06-14T00:14:28.513171+00:00",
    }


def test_state_file_survives_a_write_that_dies_midway(monkeypatch, tmp_path):
    """반려사유 ① 회귀: 쓰기가 도중에 죽어도 기존 기준선이 남아 있어야 한다.

    `open("w")`는 **먼저 절단하고** 그 자리에 쓴다. 262B짜리 파일은 사실상 안 찢어지지만,
    23aff46이 키집합 2개를 넣으면서 상태파일이 262B → 251,920B(**962배**)가 된다.
    252KB는 여러 페이지에 걸쳐 launchd 타임아웃·절전·디스크풀·강제종료에서 얼마든지 찢어진다.
    찢어지면 `_load_json`이 예외를 삼켜 `{}`를 주고 전 기준선이 **조용히 0으로 리셋**된다 —
    로그도 필드도 없고, 게이트에는 "건강한 대량 신규 수확"으로 보인다(new=4156 >= min=1 통과).

    tmp + os.replace면 실패한 쓰기가 원본을 건드리지 못한다.
    리포에 이미 있는 패턴이다: train_kosdaq_1500_bundle.py:167, kis_openapi.py:431.
    """
    state_path = tmp_path / "state.json"
    original = _live_shaped_state()
    runner._write_json(state_path, original)
    assert json.loads(state_path.read_text(encoding="utf-8")) == original

    def _die_midway(*args, **kwargs):
        raise OSError("No space left on device")

    monkeypatch.setattr(runner.json, "dump", _die_midway)
    with pytest.raises(OSError):
        runner._write_json(state_path, {"last_nightly_resolved_total": 999})

    # 원본이 온전해야 한다. 비원자적 쓰기였다면 여기서 빈 파일이 된다.
    assert json.loads(state_path.read_text(encoding="utf-8")) == original
    # tmp 잔재를 남기지 않아야 한다 (다음 쓰기·디스크를 갉아먹지 않도록).
    assert sorted(p.name for p in tmp_path.iterdir()) == ["state.json"]


def test_corrupt_state_file_is_surfaced_instead_of_silently_resetting(monkeypatch, tmp_path):
    """반려사유 ① 회귀: 손상된 상태파일이 '정상 대량 수확'으로 보이면 안 된다.

    수정 전 실측(50% 절단): 전 기준선 0 · 키집합 소실 · 예외 없음 · 로그 없음 →
    다음 사이클이 action=dataset_refresh, new=4156으로 게이트를 **통과**한다.
    23aff46이 새로 넣은 관측장치(consecutive_skip_cycles / counter_rebaselined_from /
    dropped_resolved / basis)는 전부 0·None·fallback으로 정상처럼 찍혀 사고를 못 가리킨다.
    """
    monkeypatch.setattr(runner, "_run_command", _fake_ok_command)
    shared_dir, report_dir = tmp_path / "shared", tmp_path / "reports"
    state_path = tmp_path / "state.json"
    _write_resolved(shared_dir, "RUN-20260814-001", 5)

    # 부분쓰기 재현 — 유효한 JSON의 앞 절반만 남은 상태
    full = json.dumps(_live_shaped_state(), indent=2)
    state_path.write_text(full[: len(full) // 2], encoding="utf-8")

    report = _cycle("nightly", shared_dir, report_dir, state_path)

    assert report["state_load_error"] is not None
    assert "state.json" in report["state_load_error"]
    # md 리포트 표면에도 떠야 운영자가 본다.
    md = (report_dir / "learning_cycle_nightly.md").read_text(encoding="utf-8")
    assert "state_load_error" in md
    # 손상본은 덮어쓰지 말고 보존해야 복구가 가능하다.
    assert state_path.with_suffix(".json.corrupt").exists()


def test_missing_state_file_is_not_reported_as_corruption(monkeypatch, tmp_path):
    """첫 실행(파일 없음)과 손상(파싱 실패)은 서로 다른 사건이다.

    지금은 둘 다 조용히 `{}`로 뭉개진다. 구분하지 않으면 손상 경보가 매 신규 설치마다
    울려 곧 무시당한다 — 경보를 살리려면 정상 초기화는 조용해야 한다.
    """
    monkeypatch.setattr(runner, "_run_command", _fake_ok_command)
    shared_dir, report_dir = tmp_path / "shared", tmp_path / "reports"
    state_path = tmp_path / "state.json"
    _write_resolved(shared_dir, "RUN-20260814-001", 5)

    report = _cycle("nightly", shared_dir, report_dir, state_path)

    assert report["state_load_error"] is None
    assert report["action"] == "dataset_refresh"
    assert not state_path.with_suffix(".json.corrupt").exists()


def test_atomic_write_round_trips_a_live_sized_state(tmp_path):
    """원자화가 라이브 크기(키집합 2개, 실측 251,920B)에서도 정확히 왕복해야 한다."""
    state_path = tmp_path / "state.json"
    payload = _live_shaped_state(4156)
    runner._write_json(state_path, payload)

    assert json.loads(state_path.read_text(encoding="utf-8")) == payload
    assert state_path.stat().st_size > 100_000
    assert sorted(p.name for p in tmp_path.iterdir()) == ["state.json"]


def test_legacy_state_without_key_set_still_rebaselines_on_shrink(monkeypatch, tmp_path):
    """구 상태파일(키 집합 없음)에서도 기존 축소-재기준선이 그대로 동작해야 한다."""
    monkeypatch.setattr(runner, "_run_command", _fake_ok_command)
    shared_dir, report_dir = tmp_path / "shared", tmp_path / "reports"
    state_path = tmp_path / "state.json"
    _write_json(state_path, {"last_nightly_resolved_total": 8180})
    _write_resolved(shared_dir, "RUN-20260814-001", 2)

    report = _cycle("nightly", shared_dir, report_dir, state_path)

    assert report["new_resolved_measurement_basis"] == "total_delta_fallback"
    assert report["counter_rebaselined_from"] == 8180
    assert report["action"] == "skip"
    # 재기준선 시점에 키 집합을 채워 넣어야 다음 주기부터 집합 기반으로 넘어간다.
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert len(state["last_nightly_resolved_keys"]) == 2
