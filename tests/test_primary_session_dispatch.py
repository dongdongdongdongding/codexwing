from datetime import datetime, timezone
import json
import threading

from multi_agent.tools import primary_session_dispatch as d

NOW = datetime(2026, 10, 7, 1, tzinfo=timezone.utc)


def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(d, "legacy_pids", lambda role: [])
    return {"queue": tmp_path / "queue", "state_path": tmp_path / "state.json",
            "report_dir": tmp_path / "reports"}


def enqueue(name, args, now=NOW):
    return d.enqueue(d.ops._session_map()[name], now, args["queue"])


def success(command, **kwargs):
    return {"name": command["name"], "returncode": 0, "started_at": d.stamp(),
            "finished_at": d.stamp()}


def test_polling_is_durable_idempotent_and_does_not_run_commands(tmp_path, monkeypatch):
    args = setup(tmp_path, monkeypatch)
    def forbidden(*a, **kw):
        raise AssertionError("poller must not execute a scan or batch")
    monkeypatch.setattr(d.ops, "_run_command", forbidden)
    first = d.dispatch(NOW, **args)
    assert set(first["sessions"]) == {"kr_premarket_refresh", "nasdaq_afterhours_early"}
    assert d.dispatch(NOW, **args)["queued_count"] == 0
    # The old, already-running synchronous poller can overwrite aggregate state.
    args["state_path"].write_text('{"runs":{}}')
    assert d.dispatch(NOW, **args)["queued_count"] == 0
    assert len(d.requests(args["queue"])) == 2
    state = json.loads(args["state_path"].read_text())
    assert all(r["status"] == "running" for r in state["runs"].values())


def test_live_global_batch_does_not_block_kr_scan(tmp_path, monkeypatch):
    args = setup(tmp_path, monkeypatch)
    req = enqueue("kr_premarket_refresh", args)
    monkeypatch.setattr(d, "legacy_pids", lambda role: [75970] if role == "daily_ops" else [])
    monkeypatch.setattr(d.ops, "_run_command", success)
    assert d.worker("daily_ops", now=NOW, **args)["status"] == "busy"
    assert d.worker("kr_scan", now=NOW, **args)["status"] == "finished"
    assert not d.result_path(args["queue"], req, "daily_ops").exists()
    report = d.materialize(req, **args)
    assert report["status"] == "running" and report["pending_command_count"] == 1


def test_resource_lock_and_independent_worker_completion(tmp_path, monkeypatch):
    args = setup(tmp_path, monkeypatch)
    req = enqueue("kr_premarket_refresh", args)
    entered, release = threading.Event(), threading.Event()
    def run(command, **kwargs):
        if command["name"] == "primary_daily_ops":
            entered.set()
            assert release.wait(5)
        return success(command)
    monkeypatch.setattr(d.ops, "_run_command", run)
    outcome = []
    t = threading.Thread(target=lambda: outcome.append(d.worker("daily_ops", now=NOW, **args)))
    t.start()
    try:
        assert entered.wait(5)
        assert d.worker("daily_ops", now=NOW, **args)["reason"] == "worker_lock"
        assert d.worker("kr_scan", now=NOW, **args)["status"] == "finished"
    finally:
        release.set()
        t.join(5)
    assert not t.is_alive() and outcome[0]["status"] == "finished"
    assert d.materialize(req, **args)["status"] == "ok"


def test_one_batch_serves_requests_present_before_start(tmp_path, monkeypatch):
    args = setup(tmp_path, monkeypatch)
    kr = enqueue("kr_premarket_refresh", args)
    us = enqueue("nasdaq_afterhours_early", args)
    called = []
    def run(command, **kwargs):
        called.append(command["name"])
        enqueue("kr_regular_close", args, datetime(2026, 10, 7, 7, tzinfo=timezone.utc))
        return success(command)
    monkeypatch.setattr(d.ops, "_run_command", run)
    out = d.worker("daily_ops", now=NOW, **args)
    assert len(out["served"]) == 2 and called == ["primary_daily_ops"]
    for r in (kr, us):
        assert json.loads(d.result_path(args["queue"], r, "daily_ops").read_text())["shared_batch"]
    future = next(r for r in d.requests(args["queue"]) if r["session_id"] == "kr_regular_close")
    assert not d.result_path(args["queue"], future, "daily_ops").exists()


def test_expired_and_superseded_scans_are_not_backdated(tmp_path, monkeypatch):
    args = setup(tmp_path, monkeypatch)
    old = enqueue("kr_premarket_refresh", args)
    late = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
    new = enqueue("kr_nxt_close", args, late)
    calls = []
    monkeypatch.setattr(d.ops, "_run_command", lambda c, **kw: calls.append(c) or success(c))
    assert d.worker("kr_scan", now=late, **args)["served"] == [new["id"]]
    result = json.loads(d.result_path(args["queue"], old, "kr_scan").read_text())
    assert result["dispatch_status"] == "superseded" and len(calls) == 1
    tomorrow = datetime(2026, 10, 8, 1, tzinfo=timezone.utc)
    stale = enqueue("kr_regular_close", args, late)
    assert d.worker("kr_scan", now=tomorrow, **args)["status"] == "idle"
    assert json.loads(d.result_path(args["queue"], stale, "kr_scan").read_text())["reason"] == "market_local_day_expired"


def test_interrupted_worker_does_not_repeat_unknown_outcome(tmp_path, monkeypatch):
    args = setup(tmp_path, monkeypatch)
    req = enqueue("kr_premarket_refresh", args)
    d.write_json(d.result_path(args["queue"], req, "kr_scan"), {"dispatch_status": "running"})
    monkeypatch.setattr(d.ops, "_run_command", lambda *a, **kw: (_ for _ in ()).throw(AssertionError()))
    assert d.worker("kr_scan", now=NOW, **args)["status"] == "idle"
    assert json.loads(d.result_path(args["queue"], req, "kr_scan").read_text())["dispatch_status"] == "interrupted"


def test_failed_batch_is_not_reported_success(tmp_path, monkeypatch):
    args = setup(tmp_path, monkeypatch)
    req = enqueue("kr_premarket_refresh", args)
    monkeypatch.setattr(d.ops, "_run_command", lambda c, **kw: {"returncode": 9 if c["required"] else 0})
    d.worker("kr_scan", now=NOW, **args)
    d.worker("daily_ops", now=NOW, **args)
    report = d.materialize(req, **args)
    assert report["status"] == "failed" and report["required_failure_count"] == 1


def test_unchanged_poll_does_not_retimestamp_old_results(tmp_path, monkeypatch):
    args = setup(tmp_path, monkeypatch)
    req = enqueue("kr_premarket_refresh", args)
    a = d.materialize(req, **args)
    monkeypatch.setattr(d, "stamp", lambda: "2099-01-01T00:00:00+00:00")
    b = d.materialize(req, **args)
    assert a == b


def test_legacy_probe_detects_actual_program_not_search_arguments(monkeypatch):
    from types import SimpleNamespace
    sample = ('123 /usr/bin/python3 multi_agent/tools/run_us_full_universe_research.py --market NASDAQ\n'
              '456 /bin/bash multi_agent/tools/run_daily_ops.sh\n'
              '789 rg run_daily_ops.sh\n')
    monkeypatch.setattr(d.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout=sample))
    assert d.legacy_pids("daily_ops") == [456]
    assert d.legacy_pids("us_scan") == [123]
    assert d.legacy_pids("kr_scan") == []
