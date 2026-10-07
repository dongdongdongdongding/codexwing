import json
from types import SimpleNamespace

from multi_agent.tools import research_reopen_queue as queue


def setup_queue(tmp_path, monkeypatch, rows):
    monkeypatch.setattr(queue, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(queue, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(queue, "OUT", tmp_path / "report.json")
    monkeypatch.setattr(queue, "QUEUE", {k: v for k, v in queue.QUEUE.items()
                                       if k.startswith("live_meta")})
    path = tmp_path / "runtime_state/reports/experimental" / queue.META_LEDGERS[0][0]
    path.parent.mkdir(parents=True)
    path.write_text("\n".join(json.dumps(r) for r in rows))
    queue.STATE.write_text(json.dumps({"live_meta_calibration": "2026-07-30"}))
    calls = []
    monkeypatch.setattr(queue.subprocess, "run", lambda *a, **kw:
                        calls.append(a[0]) or SimpleNamespace(returncode=0))
    return path, calls


def test_independent_second_stage_preserves_history_and_deduplicates(tmp_path, monkeypatch):
    _, calls = setup_queue(tmp_path, monkeypatch,
        [{"exit_t5_h5": 0, "mkt_state": "NORMAL", "hold_days": 5}] * 200)
    report = queue.run_queue()
    full = report["items"][1]
    assert full["ready"] and full["ticketed"]
    assert len(calls) == 1 and "2차" in calls[0][2]
    state = json.loads(queue.STATE.read_text())
    assert state["live_meta_calibration"] == "2026-07-30"
    assert state["live_meta_calibration_full"]
    assert full["evidence"]["promotion_allowed"] is False
    assert full["evidence"]["h10_tp5_probability_verified"] is False
    assert full["evidence"]["ledgers"][0]["contracts"]
    queue.run_queue()
    assert len(calls) == 1


def test_unknown_regime_is_not_non_risk_off(tmp_path, monkeypatch):
    _, calls = setup_queue(tmp_path, monkeypatch,
        [{"exit_t5_h5": 2, "mkt_state": "RISK_OFF"}] * 200 +
        [{"exit_t5_h5": 2}, {"exit_t5_h5": 2, "mkt_state": "INVALID"}])
    full = queue.run_queue()["items"][1]
    assert full["have"] == 202 and not full["ready"]
    assert not calls


def test_finite_outcomes_and_contracts_are_reported(tmp_path, monkeypatch):
    path, calls = setup_queue(tmp_path, monkeypatch,
        [{"exit_t5_h5": n, "mkt_state": "NORMAL"} for n in
         [None, True, False, float("nan"), float("inf"), -float("inf"), "5", 0, -2]])
    with path.open("a") as f:
        f.write('\n[1,2]\ninvalid\n')
    out = queue.run_queue()["items"][1]
    assert out["have"] == 2 and not out["ready"]
    evidence = out["evidence"]
    assert evidence["known_non_risk_off"] == 2
    assert evidence["ledgers"][0]["malformed_rows"] == 2
    assert len(evidence["ledgers"][0]["sha256"]) == 64
    assert not calls


def test_no_tickets_does_not_consume_stage(tmp_path, monkeypatch):
    _, calls = setup_queue(tmp_path, monkeypatch,
        [{"exit_t5_h5": 1, "mkt_state": "RISK_ON"}] * 200)
    full = queue.run_queue(no_tickets=True)["items"][1]
    assert full["ready"] and not full["ticketed"] and not calls
    queue.run_queue()
    assert len(calls) == 1


def test_failed_creation_is_retryable(tmp_path, monkeypatch):
    _, calls = setup_queue(tmp_path, monkeypatch,
        [{"exit_t5_h5": 1, "mkt_state": "NORMAL"}] * 200)
    monkeypatch.setattr(queue.subprocess, "run", lambda *a, **kw:
                        SimpleNamespace(returncode=1))
    full = queue.run_queue()["items"][1]
    assert full["ready"] and not full["ticketed"]
    assert "live_meta_calibration_full" not in json.loads(queue.STATE.read_text())


def test_199_with_regime_is_not_ready(tmp_path, monkeypatch):
    _, calls = setup_queue(tmp_path, monkeypatch,
        [{"exit_t5_h5": 1, "mkt_state": "NORMAL"}] * 199)
    assert not queue.run_queue()["items"][1]["ready"]
    assert not calls
